import os
import time
import glob
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class IncomingFileHandler(FileSystemEventHandler):
    """
    Watches a folder and triggers a callback function 
    whenever a new PDF is added.
    """
    def __init__(self, callback_function):
        self.callback_function = callback_function

    def on_created(self, event):
        # We only care about files, not directories
        if not event.is_directory and (event.src_path.endswith(".pdf") or event.src_path.endswith(".txt")):
            # Wait a split second to ensure the file is fully written to disk
            time.sleep(0.5) 
            self.callback_function(event.src_path)

def process_backlog(path_to_watch, callback):
    """
    Scans the directory for existing PDFs and processes them.
    This prevents files from being ignored if the system was offline.
    """
    # Look for both PDFs and text files produced by the email watcher
    existing_files = glob.glob(os.path.join(path_to_watch, "*.pdf")) + glob.glob(os.path.join(path_to_watch, "*.txt"))
    
    if existing_files:
        print(f"🔎 Found {len(existing_files)} existing file(s) waiting to be processed.")
        for file_path in existing_files:
            callback(file_path)
    else:
        print("✨ No pending files found.")

def start_watcher(path_to_watch, callback):
    """Initializes and starts the file system observer."""
    event_handler = IncomingFileHandler(callback)
    observer = Observer()
    observer.schedule(event_handler, path_to_watch, recursive=False)
    observer.start()
    return observer