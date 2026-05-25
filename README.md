# Intelligent Exchange Notification System

An automated pipeline using **LangGraph** and **Gemini 1.5 Flash** to extract complex financial data from PDFs and store it in **MongoDB**.

## Features
- **Watcher Ingestion**: Automatically detects new PDFs in the `data/incoming` folder.
- **Structured Extraction**: Maps unstructured PDF text to a 20-field Pydantic schema.
- **Verification Scoring**: Automatically flags low-confidence extractions for Human-in-the-Loop review.
- **Deduplication**: Uses SHA-256 file hashing in MongoDB to prevent re-processing files.

## Setup
1. **Environment**:
   - Install MongoDB locally.
   - Create a `.env` file with `GOOGLE_API_KEY` and `MONGO_URI`.

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt