import os
import datetime
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

from src.core.schema import ExchangeSchema
from src.database.mongodb import MongoHandler
from src.core.config import CONFIDENCE_THRESHOLD  

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
        """Node 1: Structured Extraction"""
        structured_llm = self.llm.with_structured_output(ExchangeSchema)
        result = structured_llm.invoke(f"Extract data from this notification: {state['raw_text']}")
        
        # Pydantic V1 / V2 compatibility check
        # .dict() is deprecated in newer Pydantic versions in favor of .model_dump()
        extracted_dict = result.model_dump() if hasattr(result, "model_dump") else result.dict()
        
        return {"extracted_json": extracted_dict}

    def verification_node(self, state: AgentState):
        """Node 2: Score calculation & Data Validation"""
        data = state["extracted_json"]
        # Logic: -0.25 for every missing core field
        core_fields = ["isin", "quantity", "price", "trade_date"]
        missing = sum(1 for f in core_fields if not data.get(f))
        
        score = 1.0 - (missing * 0.25)
        return {"score": max(0, score)}

    def store_node(self, state: AgentState):
        """Node 3: Final Storage"""
        # Adding 'processed_at' timestamp for better auditing
        metadata = {
            "file_name": state["file_name"],
            "file_hash": self.db.generate_hash(state["file_bytes"]),
            "confidence": state["score"],
            "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        # Dynamically using the threshold from config.py
        status = "completed" if state["score"] >= CONFIDENCE_THRESHOLD else "pending_review"
        
        # ⚠️ CRITICAL FIX: Calling store_notification (matches mongodb.py) 
        self.db.store_notification(state["extracted_json"], metadata, status)
        
        print(f"--- Processed {state['file_name']} | Score: {state['score']} | Status: {status} ---")
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