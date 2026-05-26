import json
from src.utils.helpers import extract_text_from_pdf

# 1. Place a tricky PDF with multi-page tables in your incoming folder
pdf_path = "../Smartstream Prototype - Copy/data/archive/58701.pdf" 

print(f"Extracting DOM from {pdf_path}...")
dom_output = extract_text_from_pdf(pdf_path)

if dom_output:
    # 2. Save it to a JSON file so you can inspect it visually
    output_path = "dom_test_output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(dom_output)
    
    print(f"✅ Success! Open '{output_path}' in your code editor to verify.")
    print("Check if 'extracted_tables' successfully merged your multi-page tables!")
else:
    print("❌ Extraction failed or returned empty.")