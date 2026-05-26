import hashlib
import json
import datetime
import pdfplumber

def calculate_sha256(file_bytes: bytes) -> str:
    """Generates a unique hash for a file to prevent duplicates."""
    return hashlib.sha256(file_bytes).hexdigest()

def extract_text_from_pdf(file_path: str) -> str:
    """
    Creates a JSON DOM from a PDF. 
    Filters table text out of raw text, extracts tables structurally,
    and merges tables that span across multiple pages.
    """
    dom_pages = []
    global_tables = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                page_data = {"page": page_num, "text": "", "table_refs": []}
                
                tables = page.find_tables()
                bboxes = [table.bbox for table in tables]
                
                def not_in_table(obj):
                    for (x0, y0, x1, y1) in bboxes:
                        if (obj.get("x0", 0) < x1 and obj.get("x1", 0) > x0 and 
                            obj.get("top", 0) < y1 and obj.get("bottom", 0) > y0):
                            return False
                    return True

                filtered_page = page.filter(not_in_table)
                text = filtered_page.extract_text()
                if text:
                    page_data["text"] = text.strip()
                    
                extracted_tables = page.extract_tables()
                for table in extracted_tables:
                    cleaned_table = [[str(cell).strip() if cell else "" for cell in row] for row in table]
                    if not cleaned_table or not cleaned_table[0]:
                        continue 

                    merged = False
                    if global_tables:
                        last_table_data = global_tables[-1]
                        last_table = last_table_data["content"]
                        
                        if len(cleaned_table[0]) == len(last_table[0]):
                            start_idx = 1 if cleaned_table[0] == last_table[0] else 0
                            last_table.extend(cleaned_table[start_idx:])
                            if page_num not in last_table_data["pages"]:
                                last_table_data["pages"].append(page_num)
                            page_data["table_refs"].append(last_table_data["id"])
                            merged = True
                            
                    if not merged:
                        table_id = f"table_{len(global_tables) + 1}"
                        global_tables.append({
                            "id": table_id,
                            "pages": [page_num],
                            "content": cleaned_table
                        })
                        page_data["table_refs"].append(table_id)

                dom_pages.append(page_data)
                
        final_dom = {
            "document_pages": dom_pages,
            "extracted_tables": global_tables
        }
        return json.dumps(final_dom, indent=2)
        
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""

def clean_extracted_json(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}

def convert_to_endata_format(data: dict) -> dict:
    """Converts a flat LLM extraction to the strict EnData Format."""
    result = {}
    
    for key, val in data.items():
        # STRICT CLEANUP: Ignore None, empty strings, and empty arrays
        if val is None or val == "" or val == []:
            continue
            
        # Map specific internal ID fields
        if key == "exchangeNotificationId":
            result["_exchangeNotificationId"] = {"RDU": {"value": val}}
            continue
        if key == "enRawDataId":
            result["enRawDataId"] = {"FEED": {"value": val}}
            continue
            
        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
            array_result = []
            for item in val:
                item_dict = {}
                for k, v in item.items():
                    if v is not None and v != "":
                        item_dict[k] = {"FEED": {"value": v}}
                if item_dict:
                    array_result.append(item_dict)
            if array_result:
                result[key] = array_result
        else:
            result[key] = {"FEED": {"value": val}}

    # Add System/Tracking Fields 
    current_time = datetime.datetime.now(datetime.timezone.utc).strftime("ISODate(\"%Y-%m-%dT%H:%M:%S.000Z\")")
    
    if "eventStatus" not in result:
        result["eventStatus"] = {"RDU": {"value": {"normalizedValue": "A"}}}
        
    result["insDate"] = {"RDU": {"value": current_time}}
    result["insUser"] = {"RDU": {"value": "AI_Extraction_Agent"}}
    result["updDate"] = {"RDU": {"value": current_time}}
    result["updUser"] = {"RDU": {"value": "AI_Extraction_Agent"}}
    result["version"] = "NumberLong(1)"
    
    result["audit"] = [
        {
            "auditIndex": 0,
            "program": "AI-Data-Ingestion",
            "updateDate": current_time,
            "comment": "Initial load from PDF feed extraction"
        }
    ]

    result["_class"] = "com.smartstreamrdu.persistence.domain.EnData"
    return result