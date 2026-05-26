import os
import datetime
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

from src.core.schema import EnDataExtractionSchema
from src.database.mongodb import MongoHandler
from src.core.config import CONFIDENCE_THRESHOLD  
from src.utils.helpers import convert_to_endata_format

class AgentState(TypedDict):
    raw_text: str
    file_bytes: bytes
    file_name: str
    extracted_json: Dict[str, Any]
    score: float

class ExchangeGraph:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        self.db = MongoHandler()
        self.workflow = self._build_graph()

    def extraction_node(self, state: AgentState):
        """Node 1: Structured Extraction against EnData Schema"""
        structured_llm = self.llm.with_structured_output(EnDataExtractionSchema)
        prompt = (
            "Extract exchange notification data into the provided EnData schema. "
            "The input is a structured JSON DOM. Map 'Before' and 'After' values accurately, "
            "and pay close attention to nested arrays like 'underlyings' and 'contract specifications'.\n\n"
            f"Document DOM:\n{state['raw_text']}"
        )
        
        result = structured_llm.invoke(prompt)
        extracted_dict = result.model_dump() if hasattr(result, "model_dump") else result.dict()
        return {"extracted_json": extracted_dict}

    def verification_node(self, state: AgentState):
        """Node 2: Score calculation & Data Validation"""
        data = state["extracted_json"]
        
        # New core fields based on EnData spec
        core_fields = ["eventType", "eventEffectiveDate", "exchangeCode"]
        missing = sum(1 for f in core_fields if not data.get(f))
        
        score = 1.0 - (missing * 0.33)
        return {"score": max(0, score)}

    def store_node(self, state: AgentState):
        """Node 3: Format to EnData and Storage"""
        metadata = {
            "file_name": state["file_name"],
            "file_hash": self.db.generate_hash(state["file_bytes"]),
            "confidence": state["score"],
            "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        status = "completed" if state["score"] >= CONFIDENCE_THRESHOLD else "pending_review"
        
        # Convert clean output into nested FEED format
        endata_document = convert_to_endata_format(state["extracted_json"])
        
        self.db.store_notification(endata_document, metadata, status)
        
        print(f"--- Processed {state['file_name']} | Score: {state['score']:.2f} | Status: {status} ---")
        return state

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("extract", self.extraction_node)
        builder.add_node("verify", self.verification_node)
        builder.add_node("store", self.store_node)
        builder.set_entry_point("extract")
        builder.add_edge("extract", "verify")
        builder.add_edge("verify", "store")
        builder.add_edge("store", END)
        return builder.compile()