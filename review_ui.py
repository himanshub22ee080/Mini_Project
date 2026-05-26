import streamlit as st
import json
import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from src.core.schema import EnDataExtractionSchema

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "ExchangeSystem"
NOTIFICATIONS_COLLECTION = "notifications"

# Define which fields require human RDU input
RDU_EDITABLE_FIELDS = [
    "exchangeNotificationId", "exchangeCode", "newExchangeCode", 
    "exchangeSourceName", "eventType", "instrumentTypeCode", 
    "subscriptionPriceCurrencyCode"
]

@st.cache_resource
def init_connection():
    return MongoClient(MONGO_URI)

client = init_connection()
db = client[DB_NAME]
collection = db[NOTIFICATIONS_COLLECTION]

st.set_page_config(page_title="Exchange System | HITL Review", layout="wide")
st.title("🧑‍💻 EnData Human-in-the-Loop Review Queue")

def get_pending_reviews():
    return list(collection.find({"status": "pending_review"}))

def unwrap_endata_dual(endata_doc):
    """Safely extracts both FEED and RDU values for the UI."""
    unwrapped = {}
    for k, v in endata_doc.items():
        if k in ["_class", "_id", "audit", "version", "insDate", "insUser", "updDate", "updUser", "eventStatus"]: 
            continue
            
        # Map back the alias for UI purposes
        display_key = "exchangeNotificationId" if k == "_exchangeNotificationId" else k
            
        if isinstance(v, list):
            unwrapped[display_key] = {"FEED": v, "RDU": None}
        elif isinstance(v, dict):
            feed_val, rdu_val = None, None
            
            if "FEED" in v:
                val = v["FEED"].get("value", "")
                feed_val = val["val"] if isinstance(val, dict) and "val" in val else val
                
            if "RDU" in v:
                val = v["RDU"].get("value", "")
                rdu_val = val["normalizedValue"] if isinstance(val, dict) and "normalizedValue" in val else val
                    
            unwrapped[display_key] = {"FEED": feed_val, "RDU": rdu_val}
        else:
            unwrapped[display_key] = {"FEED": v, "RDU": None}
    return unwrapped

pending_docs = get_pending_reviews()

if not pending_docs:
    st.success("🎉 Great job! The review queue is empty. All EnData notifications are processed.")
else:
    st.warning(f"You have {len(pending_docs)} document(s) waiting for review.")
    
    doc_options = {str(doc["_id"]): doc["metadata"]["file_name"] for doc in pending_docs}
    selected_id = st.sidebar.selectbox("Select a file to review:", options=list(doc_options.keys()), format_func=lambda x: doc_options[x])
    selected_doc = next(doc for doc in pending_docs if str(doc["_id"]) == selected_id)
    
    st.subheader(f"📄 Reviewing: {selected_doc['metadata']['file_name']}")
    st.caption(f"AI Confidence Score: **{selected_doc['metadata']['confidence']:.2f}**")
    
    with st.form("review_form"):
        st.write("### Edit Extracted EnData Attributes")
        st.info("💡 For Fields marked with '(RDU - Normalized)', review the raw FEED data on the left and input the system-normalized code on the right.")
        
        unwrapped_data = unwrap_endata_dual(selected_doc.get("enData", {}))
        edited_data = {}
        
        col1, col2 = st.columns(2)
        all_possible_fields = EnDataExtractionSchema.model_fields.keys()
        
        for i, key in enumerate(all_possible_fields):
            data = unwrapped_data.get(key, {"FEED": None, "RDU": None})
            feed_val = data["FEED"]
            rdu_val = data["RDU"]
            
            if key in ["underlyings", "newUnderlyings", "dividends", "eventPreviousReferenceIds", "enWorkItemReference"]:
                st.write(f"#### {key}")
                display_val = feed_val if feed_val is not None else []
                edited_data[key] = {"FEED": st.text_area(f"{key} (Edit as JSON Array)", value=json.dumps(display_val, indent=2), height=200)}
                
            elif key in RDU_EDITABLE_FIELDS:
                st.write(f"**{key}**")
                c1, c2 = st.columns(2)
                feed_input = c1.text_input(f"FEED (Raw)", value=str(feed_val) if feed_val is not None else "", key=f"{key}_feed")
                rdu_input = c2.text_input(f"RDU (Normalized)", value=str(rdu_val) if rdu_val is not None else "", key=f"{key}_rdu")
                edited_data[key] = {"FEED": feed_input, "RDU": rdu_input}
                
            else:
                with col1 if i % 2 == 0 else col2:
                    current_val = ", ".join(map(str, feed_val)) if isinstance(feed_val, list) else (str(feed_val) if feed_val is not None else "")
                    edited_data[key] = {"FEED": st.text_input(label=key, value=current_val)}
        
        submitted = st.form_submit_button("✅ Approve and Save EnData", type="primary")
        
        if submitted:
            updated_enData = selected_doc.get("enData", {})
            
            for k, vals in edited_data.items():
                feed_str = vals.get("FEED", "")
                rdu_str = vals.get("RDU", "")
                db_key = "_exchangeNotificationId" if k == "exchangeNotificationId" else k
                
                # CRITICAL FIX: If both inputs are empty, remove from MongoDB document!
                if not feed_str and not rdu_str and feed_str != "[]":
                    if db_key in updated_enData:
                        del updated_enData[db_key]
                    continue
                
                # Save JSON Arrays
                if k in ["underlyings", "newUnderlyings", "dividends", "eventPreviousReferenceIds", "enWorkItemReference"]:
                    if feed_str and feed_str != "[]":
                        try:
                            updated_enData[db_key] = json.loads(feed_str)
                        except Exception as e:
                            st.error(f"Invalid JSON format in '{k}': {e}")
                            st.stop()
                else:
                    if db_key not in updated_enData:
                        updated_enData[db_key] = {}
                        
                    # Save FEED
                    if feed_str:
                        if k in ["events", "exchangeTickers", "series"]:
                            val_list = [v.strip() for v in feed_str.split(",") if v.strip()]
                            updated_enData[db_key]["FEED"] = {"value": val_list}
                        else:
                            try:
                                if k in ["productIsin", "newProductIsin", "exchangePrefix"]: final_val = feed_str
                                else: final_val = float(feed_str) if '.' in feed_str else int(feed_str)
                            except ValueError:
                                final_val = feed_str
                            updated_enData[db_key]["FEED"] = {"value": final_val}
                            
                    # Save Human RDU Input
                    if rdu_str:
                        # Ensure RDU uses generic "value" for exchangeNotificationId, but "normalizedValue" for domains
                        if k == "exchangeNotificationId":
                            updated_enData[db_key]["RDU"] = {"value": rdu_str.strip()}
                        else:
                            updated_enData[db_key]["RDU"] = {"value": {"normalizedValue": rdu_str.strip()}}
            
            # Update System/Audit Fields
            current_time = datetime.datetime.now(datetime.timezone.utc).strftime("ISODate(\"%Y-%m-%dT%H:%M:%S.000Z\")")
            updated_enData["updDate"] = {"RDU": {"value": current_time}}
            updated_enData["updUser"] = {"RDU": {"value": "Human_Reviewer"}}
            
            if "audit" in updated_enData:
                updated_enData["audit"].append({
                    "auditIndex": len(updated_enData["audit"]),
                    "user": "Human_Reviewer",
                    "program": "Review_UI",
                    "updateDate": current_time,
                    "comment": "Manual FEED correction and RDU normalization via Review UI"
                })
            
            collection.update_one(
                {"_id": selected_doc["_id"]},
                {
                    "$set": {
                        "enData": updated_enData,
                        "status": "completed",
                        "review_notes": "Manually verified and normalized by human operator"
                    }
                }
            )
            st.success("✅ Document EnData updated successfully! Extraneous empty dicts have been removed.")
            st.rerun()