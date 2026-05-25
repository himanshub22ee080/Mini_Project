import streamlit as st
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "ExchangeSystem"
NOTIFICATIONS_COLLECTION = "notifications"

# Connect to Database
@st.cache_resource
def init_connection():
    return MongoClient(MONGO_URI)

client = init_connection()
db = client[DB_NAME]
collection = db[NOTIFICATIONS_COLLECTION]

# Page Config
st.set_page_config(page_title="Exchange System | HITL Review", layout="wide")
st.title("🧑‍💻 Human-in-the-Loop Review Queue")

# Fetch Pending Reviews
def get_pending_reviews():
    return list(collection.find({"status": "pending_review"}))

pending_docs = get_pending_reviews()

if not pending_docs:
    st.success("🎉 Great job! The review queue is empty. All notifications are processed.")
else:
    st.warning(f"You have {len(pending_docs)} document(s) waiting for review.")
    
    # Create a sidebar to select which document to review
    doc_options = {str(doc["_id"]): doc["metadata"]["file_name"] for doc in pending_docs}
    selected_id = st.sidebar.selectbox("Select a file to review:", options=list(doc_options.keys()), format_func=lambda x: doc_options[x])
    
    # Get the selected document data
    selected_doc = next(doc for doc in pending_docs if str(doc["_id"]) == selected_id)
    
    # Display Metadata
    st.subheader(f"📄 Reviewing: {selected_doc['metadata']['file_name']}")
    st.caption(f"AI Confidence Score: **{selected_doc['metadata']['confidence']}**")
    
    # Form to edit the data
    with st.form("review_form"):
        st.write("### Extracted Data")
        st.info("Fix any missing or incorrect fields below, then click 'Approve and Save'.")
        
        # Create a dictionary to hold user's edited values
        edited_data = {}
        
        col1, col2 = st.columns(2)
        
        # Loop through the extracted fields and create a text input for each
        fields = selected_doc.get("extracted_fields", {})
        for i, (key, value) in enumerate(fields.items()):
            # Alternate columns for layout
            with col1 if i % 2 == 0 else col2:
                # If value is None, show an empty string
                current_val = "" if value is None else str(value)
                edited_data[key] = st.text_input(label=key.replace("_", " ").title(), value=current_val)
        
        # Submit Button
        submitted = st.form_submit_button("✅ Approve and Save (Mark as Completed)", type="primary")
        
        if submitted:
            # Typecasting back to float for numeric fields where necessary (basic handling)
            for k, v in edited_data.items():
                if k in ["quantity", "price", "notional_amount", "fee_amount", "tax_amount"]:
                    try:
                        edited_data[k] = float(v) if v else None
                    except ValueError:
                        pass # Keep as string if it can't be cast
            
            # Update the database!
            collection.update_one(
                {"_id": selected_doc["_id"]},
                {
                    "$set": {
                        "extracted_fields": edited_data,
                        "status": "completed",
                        "review_notes": "Manually reviewed and approved"
                    }
                }
            )
            st.success("✅ Document updated successfully!")
            st.rerun() # Refresh the app to show the next pending document