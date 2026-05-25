import hashlib
import PyPDF2
import io

def calculate_sha256(file_bytes: bytes) -> str:
    """Generates a unique hash for a file to prevent duplicates."""
    return hashlib.sha256(file_bytes).hexdigest()

def extract_text_from_pdf(file_path: str) -> str:
    """Extracts raw text from a PDF file."""
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""

def clean_extracted_json(data: dict) -> dict:
    """Optional: Basic cleanup of dictionary data (removing nulls, etc.)"""
    return {k: v for k, v in data.items() if v is not None}