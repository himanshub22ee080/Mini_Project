import os
import json
import datetime
from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from src.core.schema import EnDataExtractionSchema
from src.database.mongodb import MongoHandler
from src.core.config import CONFIDENCE_THRESHOLD  
from src.utils.helpers import convert_to_endata_format

# ==========================================
# 1. SCHEMAS FOR NODE 1 (Extraction)
# ==========================================
class FieldEvidence(BaseModel):
    field_name: str = Field(description="The exact name of the schema attribute (e.g., 'eventType', 'quantityBefore')")
    extracted_value: str = Field(description="The value you extracted, converted to a string.")
    supporting_context: str = Field(description="The EXACT quote or specific context from the document that proves this value.")

class ExtractionWithEvidence(BaseModel):
    extracted_data: EnDataExtractionSchema = Field(description="The populated EnData schema.")
    evidence_list: List[FieldEvidence] = Field(description="A list providing the supporting context for EVERY field you populated in extracted_data.")

# ==========================================
# 2. SCHEMAS FOR NODE 2 (Verification)
# ==========================================
class FieldEvaluation(BaseModel):
    field_name: str
    is_supported: bool = Field(description="True if the context exists in the text AND logically supports the value. False if hallucinated or inconsistent.")
    reason: str = Field(description="Brief explanation of why it is supported or penalized.")

class VerificationReport(BaseModel):
    evaluations: List[FieldEvaluation]
    suggested_score: float = Field(description="Score from 0.0 to 1.0. Start at 1.0. Deduct 0.1 for every unsupported/hallucinated field.")

# ==========================================
# 3. STATE DEFINITION
# ==========================================
class AgentState(TypedDict):
    raw_text: str
    file_bytes: bytes
    file_name: str
    extracted_json: Dict[str, Any]
    evidence_list: List[Dict[str, Any]]
    score: float
    score_breakdown: Dict[str, Any]

# ==========================================
# 4. GRAPH ARCHITECTURE
# ==========================================
class ExchangeGraph:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash", 
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.0
        )
        self.db = MongoHandler()
        self.workflow = self._build_graph()

    def extraction_node(self, state: AgentState):
        """Node 1: Extract data AND provide supporting quotes"""
        structured_llm = self.llm.with_structured_output(ExtractionWithEvidence)
        prompt = (
            "Extract exchange notification data into the provided EnData schema. "
            "CRITICAL INSTRUCTIONS:\n"
            "1. Do not guess. If data is not explicitly present, leave the field empty.\n"
            "2. For EVERY field you populate, you MUST provide an entry in the 'evidence_list' containing the exact quote or context from the text.\n"
            "3. If you cannot find a direct quote to support a value, DO NOT extract it.\n\n"
            f"Document DOM:\n{state['raw_text']}"
        )
        
        result = structured_llm.invoke(prompt)
        
        # Clean up the EnData schema by removing nulls so we only pass actual data
        extracted_dict = result.extracted_data.model_dump()
        
        # Convert evidence list to standard dicts to pass in state
        evidence_dicts = [ev.model_dump() for ev in result.evidence_list]
        
        return {
            "extracted_json": extracted_dict, 
            "evidence_list": evidence_dicts
        }

    def verification_node(self, state: AgentState):
        """Node 2: Judge checks the Extracted Value against the Context and Document"""
        structured_llm = self.llm.with_structured_output(VerificationReport)
        
        evidence_str = json.dumps(state["evidence_list"], indent=2)
        
        prompt = f"""
        You are an expert financial data auditor. Your job is to verify an AI's data extraction.
        You must only penalize if there is an inconsistency or hallucination.
        
        Document DOM (Source of Truth):
        {state['raw_text']}
        
        AI's Evidence List (What it extracted and its supporting context):
        {evidence_str}
        
        INSTRUCTIONS:
        1. Evaluate EVERY item in the Evidence List.
        2. Ask yourself:
           - Does the "supporting_context" actually exist in the Document DOM?
           - Does that context logically prove the "extracted_value"?
        3. If BOTH are true, is_supported = True.
        4. If the context is missing from the DOM, or the context does not match the value, is_supported = False.
        5. Calculate the suggested_score: Start at 1.0. Deduct 0.1 ONLY for fields where is_supported is False. Do not go below 0.0.
        """
        
        report = structured_llm.invoke(prompt)
        
        # Format the breakdown for the debug file so you can see exactly what happened
        breakdown = {
            "initial_score": 1.0,
            "final_score": report.suggested_score,
            "evaluations": []
        }
        
        for ev in report.evaluations:
            # Find the context Node 1 provided so we can log it
            node1_context = next((e["supporting_context"] for e in state["evidence_list"] if e["field_name"] == ev.field_name), "N/A")
            node1_val = next((e["extracted_value"] for e in state["evidence_list"] if e["field_name"] == ev.field_name), "N/A")
            
            breakdown["evaluations"].append({
                "field": ev.field_name,
                "ai_extracted_value": node1_val,
                "ai_supporting_context": node1_context,
                "is_supported": ev.is_supported,
                "judge_reason": ev.reason
            })
        
        # Save debug log locally
        os.makedirs("debug_logs", exist_ok=True)
        safe_filename = state['file_name'].replace(".txt", "").replace(".pdf", "")
        debug_filepath = f"debug_logs/score_debug_{safe_filename}.json"
        
        with open(debug_filepath, "w", encoding="utf-8") as f:
            json.dump(breakdown, f, indent=4)
            
        return {"score": report.suggested_score, "score_breakdown": breakdown}

    def store_node(self, state: AgentState):
        """Node 3: Format and Store (Evidence list is discarded here, keeping schema clean)"""
        metadata = {
            "file_name": state["file_name"],
            "file_hash": self.db.generate_hash(state["file_bytes"]),
            "confidence": state["score"],
            "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        status = "completed" if state["score"] >= CONFIDENCE_THRESHOLD else "pending_review"
        
        # Notice we only pass the extracted_json to the DB, the evidence_list is safely ignored
        endata_document = convert_to_endata_format(state["extracted_json"])
        self.db.store_notification(endata_document, metadata, status)
        
        print(f"--- Processed {state['file_name']} | Score: {state['score']:.2f} | Status: {status} ---")
        return state

    def _build_graph(self):
        builder = StateGraph(AgentState)
        
        # Only 3 nodes: Extract -> Verify -> Store
        builder.add_node("extract", self.extraction_node)
        builder.add_node("verify", self.verification_node)
        builder.add_node("store", self.store_node)
        
        builder.set_entry_point("extract")
        builder.add_edge("extract", "verify")
        builder.add_edge("verify", "store")
        builder.add_edge("store", END)
        
        return builder.compile()