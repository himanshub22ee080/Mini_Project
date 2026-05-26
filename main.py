import os
import time
import threading
from src.core.config import INCOMING_DIR, ARCHIVE_DIR
from src.ingestion.watcher import start_watcher, process_backlog
from src.ingestion.email_watcher import start_email_polling
from src.utils.helpers import extract_text_from_pdf
from src.agents.graph import ExchangeGraph

# Initialize the AI Workflow
graph_app = ExchangeGraph().workflow

def process_new_file(file_path):
    """The orchestration logic for a single file."""
    file_name = os.path.basename(file_path) # extracting the basename of pdf from its path
    print(f"🔔 New file detected: {file_name}")

    # 1. Extract Text
    text = None
    if file_path.lower().endswith('.txt'):
        try:
            with open(file_path, 'r', encoding='utf-8') as fh:
                text = fh.read()
        except Exception as e:
            print(f"❌ Failed to read text file {file_name}: {e}")
            return
    else:
        text = extract_text_from_pdf(file_path)
        
    if not text:
        print(f"⚠️ Could not extract text from {file_name}. Skipping.")
        return

    # 2. Prepare File Bytes (for hashing)
    if file_path.lower().endswith('.txt'):
        file_bytes = text.encode('utf-8')
    else:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

    # 3. Run the LangGraph
    try:
        graph_app.invoke({
            "raw_text": text,
            "file_bytes": file_bytes,
            "file_name": file_name,
            "extracted_json": {},
            "score": 0.0
        })

        # 4. Archive the file
        dest_path = os.path.join(ARCHIVE_DIR, file_name)
        # Handle filename collisions in archive
        if os.path.exists(dest_path):
            dest_path = os.path.join(ARCHIVE_DIR, f"{int(time.time())}_{file_name}")
            
        os.rename(file_path, dest_path)
        print(f"✅ Successfully processed and archived: {file_name}")

    except Exception as e:
        print(f"❌ Failed to process {file_name}: {e}")

# if __name__ == "__main__":
#     # Ensure directories exist
#     os.makedirs(INCOMING_DIR, exist_ok=True)
#     os.makedirs(ARCHIVE_DIR, exist_ok=True)

#     print("AI Agent System Starting Up...")
    
#     process_backlog(INCOMING_DIR, process_new_file)

#     print(f"Now monitoring {INCOMING_DIR} for live updates...")
#     observer = start_watcher(INCOMING_DIR, process_new_file)


#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         observer.stop()
#         print("\nStopping system...")
    
#     observer.join()

if __name__ == "__main__":

    os.makedirs(INCOMING_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    print("🤖 AI Agent System Starting Up...")
    
    # 1. Process backlog folder files
    process_backlog(INCOMING_DIR, process_new_file)

    # 2. Start the Email Watcher in a background thread
    # It will check emails every 10 seconds (daemon=True means it stops when main.py stops)
    email_thread = threading.Thread(target=start_email_polling, args=(10,), daemon=True)
    email_thread.start()

    # 3. Start live folder monitoring
    print(f"👀 Now monitoring {INCOMING_DIR} for live updates...")
    observer = start_watcher(INCOMING_DIR, process_new_file)

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping system...")
    
    observer.join()