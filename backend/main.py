from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
import base64
import json
import os
from dotenv import load_dotenv
import logging
import re
import pandas as pd
from openai import OpenAI
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Load OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("⚠️ OPENAI_API_KEY environment variable not set")
    raise RuntimeError("OPENAI_API_KEY environment variable not set. Please create a .env file with OPENAI_API_KEY=your-key")

# Initialize OpenAI client
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("✅ OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize OpenAI client: {str(e)}")
    raise RuntimeError(f"Failed to initialize OpenAI client: {str(e)}")

app = FastAPI(title="Insurance Policy Processing System")

# Add CORS middleware for frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tata-reports.vercel.app"],  # Adjust to specific origins in production, e.g., ["https://your-frontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Embedded Formula Data
FORMULA_DATA = [
    {"LOB": "TW", "SEGMENT": "1+5", "INSURER": "All Companies", "PO": "90% of Payin", "REMARKS": "NIL"},
    {"LOB": "TW", "SEGMENT": "TW SAOD + COMP", "INSURER": "All Companies", "PO": "90% of Payin", "REMARKS": "NIL"},
    {"LOB": "TW", "SEGMENT": "TW SAOD + COMP", "INSURER": "DIGIT", "PO": "-2%", "REMARKS": "Payin Below 20%"},
    {"LOB": "TW", "SEGMENT": "TW SAOD + COMP", "INSURER": "DIGIT", "PO": "-3%", "REMARKS": "Payin 21% to 30%"},
    {"LOB": "TW", "SEGMENT": "TW SAOD + COMP", "INSURER": "DIGIT", "PO": "-4%", "REMARKS": "Payin 31% to 50%"},
    {"LOB": "TW", "SEGMENT": "TW SAOD + COMP", "INSURER": "DIGIT", "PO": "-5%", "REMARKS": "Payin Above 50%"},
    {"LOB": "TW", "SEGMENT": "TW TP", "INSURER": "Bajaj, Digit, ICICI", "PO": "-3%", "REMARKS": "Payin Above 20%"},
    {"LOB": "TW", "SEGMENT": "TW TP", "INSURER": "Rest of Companies", "PO": "-2%", "REMARKS": "Payin Below 20%"},
    {"LOB": "TW", "SEGMENT": "TW TP", "INSURER": "Rest of Companies", "PO": "-3%", "REMARKS": "Payin 21% to 30%"},
    {"LOB": "TW", "SEGMENT": "TW TP", "INSURER": "Rest of Companies", "PO": "-4%", "REMARKS": "Payin 31% to 50%"},
    {"LOB": "TW", "SEGMENT": "TW TP", "INSURER": "Rest of Companies", "PO": "-5%", "REMARKS": "Payin Above 50%"},
    {"LOB": "PVT CAR", "SEGMENT": "PVT CAR COMP + SAOD", "INSURER": "All Companies", "PO": "90% of Payin", "REMARKS": "All Fuel"},
    {"LOB": "PVT CAR", "SEGMENT": "PVT CAR TP", "INSURER": "Bajaj, Digit, SBI", "PO": "-2%", "REMARKS": "Payin Below 20%"},
    {"LOB": "PVT CAR", "SEGMENT": "PVT CAR TP", "INSURER": "Bajaj, Digit, SBI", "PO": "-3%", "REMARKS": "Payin Above 20%"},
    {"LOB": "PVT CAR", "SEGMENT": "PVT CAR TP", "INSURER": "Rest of Companies", "PO": "90% of Payin", "REMARKS": "Zuno - 21"},
    {"LOB": "CV", "SEGMENT": "Upto 2.5 GVW", "INSURER": "Reliance, SBI", "PO": "-2%", "REMARKS": "NIL"},
    {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "INSURER": "Rest of Companies", "PO": "-2%", "REMARKS": "Payin Below 20%"},
    {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "INSURER": "Rest of Companies", "PO": "-3%", "REMARKS": "Payin 21% to 30%"},
    {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "INSURER": "Rest of Companies", "PO": "-4%", "REMARKS": "Payin 31% to 50%"},
    {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "INSURER": "Rest of Companies", "PO": "-5%", "REMARKS": "Payin Above 50%"},
    {"LOB": "BUS", "SEGMENT": "SCHOOL BUS", "INSURER": "TATA, Reliance, Digit, ICICI", "PO": "Less 2% of Payin", "REMARKS": "NIL"},
    {"LOB": "BUS", "SEGMENT": "SCHOOL BUS", "INSURER": "Rest of Companies", "PO": "88% of Payin", "REMARKS": "NIL"},
    {"LOB": "BUS", "SEGMENT": "STAFF BUS", "INSURER": "All Companies", "PO": "88% of Payin", "REMARKS": "NIL"},
    {"LOB": "TAXI", "SEGMENT": "TAXI", "INSURER": "All Companies", "PO": "-2%", "REMARKS": "Payin Below 20%"},
    {"LOB": "TAXI", "SEGMENT": "TAXI", "INSURER": "All Companies", "PO": "-3%", "REMARKS": "Payin 21% to 30%"},
    {"LOB": "TAXI", "SEGMENT": "TAXI", "INSURER": "All Companies", "PO": "-4%", "REMARKS": "Payin 31% to 50%"},
    {"LOB": "TAXI", "SEGMENT": "TAXI", "INSURER": "All Companies", "PO": "-5%", "REMARKS": "Payin Above 50%"},
    {"LOB": "MISD", "SEGMENT": "Misd, Tractor", "INSURER": "All Companies", "PO": "88% of Payin", "REMARKS": "NIL"}
]

def extract_text_from_file(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Extract text from uploaded image file using OCR with enhanced prompting"""
    file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
    file_type = content_type if content_type else file_extension

    # Image-based extraction with enhanced OCR
    image_extensions = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff']
    if file_extension in image_extensions or file_type.startswith('image/'):
        try:
            image_base64 = base64.b64encode(file_bytes).decode('utf-8')
            
            prompt = """Extract ALL text from this insurance policy image with extreme accuracy.

CRITICAL INSTRUCTIONS:
1. Read EVERY piece of text visible in the image, including:
   - Headers, titles, and section names
   - All table data (columns and rows)
   - Segment/LOB information (TW, PVT CAR, CV, BUS, TAXI, MISD)
   - Company names
   - Policy types (TP, COMP, SAOD, etc.)
   - Payin/Payout percentages or decimals
   - Weight/tonnage (e.g., "upto 2.5 Tn", "2.5 GVW")
   - Vehicle makes (Tata, Maruti, etc.)
   - Age information (>5 years, etc.)
   - Transaction types (New, Old, Renewal)
   - Location/district information
   - Validity dates
   - ALL numerical values
   - Any remarks, notes, or conditions

2. Preserve the EXACT format and structure of tables if present
3. If there's a table, clearly indicate column headers and separate rows
4. For numbers that look like decimals (0.625, 0.34), preserve them exactly
5. For percentages (34%, 62.5%), preserve them exactly
6. Extract text in a structured, organized manner

Return the complete text extraction - do not summarize or skip anything."""
                
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/{file_extension};base64,{image_base64}"}}
                    ]
                }],
                temperature=0.0,
                max_tokens=4000
            )
            
            extracted_text = response.choices[0].message.content.strip()
            
            if not extracted_text or len(extracted_text) < 10:
                logger.error("OCR returned very short or empty text")
                return ""
            
            return extracted_text
            
        except Exception as e:
            logger.error(f"Error in OCR extraction: {str(e)}")
            raise ValueError(f"Failed to extract text from image: {str(e)}")

    raise ValueError(f"Unsupported file type for {filename}. Only images are supported.")

def clean_json_response(response_text: str) -> str:
    """Clean and extract valid JSON array from OpenAI response"""
    cleaned = re.sub(r'```json\s*|\s*```', '', response_text).strip()
    
    start_idx = cleaned.find('[')
    end_idx = cleaned.rfind(']') + 1 if cleaned.rfind(']') != -1 else len(cleaned)
    
    if start_idx != -1 and end_idx > start_idx:
        cleaned = cleaned[start_idx:end_idx]
    else:
        logger.warning("No valid JSON array found in response, returning empty array")
        return "[]"
    
    if not cleaned.startswith('['):
        cleaned = '[' + cleaned
    if not cleaned.endswith(']'):
        cleaned += ']'
    
    return cleaned

def ensure_list_format(data) -> list:
    """Ensure data is in list format"""
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        raise ValueError(f"Expected list or dict, got {type(data)}")

def classify_payin(payin_str):
    """Converts Payin string to float and classifies its range"""
    try:
        payin_clean = str(payin_str).replace('%', '').replace(' ', '').strip()
        
        if not payin_clean or payin_clean.upper() == 'N/A':
            return 0.0, "Payin Below 20%"
        
        payin_value = float(payin_clean)
        
        if payin_value <= 20:
            category = "Payin Below 20%"
        elif 21 <= payin_value <= 30:
            category = "Payin 21% to 30%"
        elif 31 <= payin_value <= 50:
            category = "Payin 31% to 50%"
        else:
            category = "Payin Above 50%"
        return payin_value, category
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse payin value: {payin_str}, error: {e}")
        return 0.0, "Payin Below 20%"

def apply_formula_directly(policy_data, company_name):
    """Apply formula rules directly using Python logic with default STAFF BUS for unspecified BUS"""
    if not policy_data:
        logger.warning("No policy data to process")
        return []
    
    calculated_data = []
    
    for record in policy_data:
        try:
            segment = str(record.get('Segment', '')).upper()
            payin_value = record.get('Payin_Value', 0)
            payin_category = record.get('Payin_Category', '')
            
            lob = ""
            segment_upper = segment.upper()
            
            if any(tw_keyword in segment_upper for tw_keyword in ['TW', '2W', 'TWO WHEELER', 'TWO-WHEELER']):
                lob = "TW"
            elif any(car_keyword in segment_upper for car_keyword in ['PVT CAR', 'PRIVATE CAR', 'CAR', 'PCI']):
                lob = "PVT CAR"
            elif any(cv_keyword in segment_upper for cv_keyword in ['CV', 'COMMERCIAL', 'LCV', 'GVW', 'TN', 'UPTO', 'ALL GVW', 'PCV', 'GCV']):
                lob = "CV"
            elif 'BUS' in segment_upper:
                lob = "BUS"
            elif 'TAXI' in segment_upper:
                lob = "TAXI"
            elif any(misd_keyword in segment_upper for misd_keyword in ['MISD', 'TRACTOR', 'MISC', 'AMBULANCE', 'POLICE VAN', 'GARBAGE VAN']):
                lob = "MISD"
            else:
                remarks_upper = str(record.get('Remarks', '')).upper()
                if any(cv_keyword in remarks_upper for cv_keyword in ['TATA', 'MARUTI', 'GVW', 'TN']):
                    lob = "CV"
                else:
                    lob = "UNKNOWN"
            
            matched_segment = segment_upper
            if lob == "BUS":
                if "SCHOOL" not in segment_upper and "STAFF" not in segment_upper:
                    matched_segment = "STAFF BUS"
                elif "SCHOOL" in segment_upper:
                    matched_segment = "SCHOOL BUS"
                elif "STAFF" in segment_upper:
                    matched_segment = "STAFF BUS"
            
            matched_rule = None
            rule_explanation = ""
            company_normalized = company_name.upper().replace('GENERAL', '').replace('INSURANCE', '').strip()
            
            for rule in FORMULA_DATA:
                if rule["LOB"] != lob:
                    continue
                    
                rule_segment = rule["SEGMENT"].upper()
                segment_match = False
                
                if lob == "CV":
                    if "UPTO 2.5" in rule_segment:
                        if any(keyword in segment_upper for keyword in ["UPTO 2.5", "2.5 TN", "2.5 GVW", "2.5TN", "2.5GVW", "UPTO2.5"]):
                            segment_match = True
                    elif "ALL GVW" in rule_segment:
                        segment_match = True
                elif lob == "BUS":
                    if matched_segment == rule_segment:
                        segment_match = True
                elif lob == "PVT CAR":
                    if "COMP" in rule_segment and any(keyword in segment for keyword in ["COMP", "COMPREHENSIVE", "PACKAGE", "1ST PARTY", "1+1"]):
                        segment_match = True
                    elif "TP" in rule_segment and "TP" in segment and "COMP" not in segment:
                        segment_match = True
                elif lob == "TW":
                    if "1+5" in rule_segment and any(keyword in segment for keyword in ["1+5", "NEW", "FRESH"]):
                        segment_match = True
                    elif "SAOD + COMP" in rule_segment and any(keyword in segment for keyword in ["SAOD", "COMP", "PACKAGE", "1ST PARTY", "1+1"]):
                        segment_match = True
                    elif "TP" in rule_segment and "TP" in segment:
                        segment_match = True
                else:
                    segment_match = True
                
                if not segment_match:
                    continue
                
                insurers = [ins.strip().upper() for ins in rule["INSURER"].split(',')]
                company_match = False
                
                if "ALL COMPANIES" in insurers:
                    company_match = True
                elif "REST OF COMPANIES" in insurers:
                    is_in_specific_list = False
                    for other_rule in FORMULA_DATA:
                        if (other_rule["LOB"] == rule["LOB"] and 
                            other_rule["SEGMENT"] == rule["SEGMENT"] and
                            "REST OF COMPANIES" not in other_rule["INSURER"] and
                            "ALL COMPANIES" not in other_rule["INSURER"]):
                            other_insurers = [ins.strip().upper() for ins in other_rule["INSURER"].split(',')]
                            if any(company_key in company_normalized for company_key in other_insurers):
                                is_in_specific_list = True
                                break
                    if not is_in_specific_list:
                        company_match = True
                else:
                    for insurer in insurers:
                        if insurer in company_normalized or company_normalized in insurer:
                            company_match = True
                            break
                
                if not company_match:
                    continue
                
                remarks = rule.get("REMARKS", "")
                
                if remarks == "NIL" or "NIL" in remarks.upper():
                    matched_rule = rule
                    rule_explanation = f"Direct match: LOB={lob}, Segment={rule_segment}, Company={rule['INSURER']}"
                    break
                elif any(payin_keyword in remarks for payin_keyword in ["Payin Below", "Payin 21%", "Payin 31%", "Payin Above"]):
                    if payin_category in remarks:
                        matched_rule = rule
                        rule_explanation = f"Payin category match: LOB={lob}, Segment={rule_segment}, Payin={payin_category}"
                        break
                else:
                    matched_rule = rule
                    rule_explanation = f"Other remarks match: LOB={lob}, Segment={rule_segment}, Remarks={remarks}"
                    break
            
            if matched_rule:
                po_formula = matched_rule["PO"]
                calculated_payout = payin_value
                
                if "90% of Payin" in po_formula:
                    calculated_payout *= 0.9
                elif "88% of Payin" in po_formula:
                    calculated_payout *= 0.88
                elif "Less 2% of Payin" in po_formula:
                    calculated_payout -= 2
                elif "-2%" in po_formula:
                    calculated_payout -= 2
                elif "-3%" in po_formula:
                    calculated_payout -= 3
                elif "-4%" in po_formula:
                    calculated_payout -= 4
                elif "-5%" in po_formula:
                    calculated_payout -= 5
                
                calculated_payout = max(0, calculated_payout)
                formula_used = po_formula
            else:
                calculated_payout = payin_value
                formula_used = "No matching rule found"
            
            result_record = record.copy()
            result_record['Calculated Payout'] = f"{calculated_payout:.2f}%"
            result_record['Formula Used'] = formula_used
            result_record['Rule Explanation'] = rule_explanation
            
            calculated_data.append(result_record)
            
        except Exception as e:
            logger.error(f"Error processing record: {record}, error: {str(e)}")
            result_record = record.copy()
            result_record['Calculated Payout'] = "Error"
            result_record['Formula Used'] = "Error in calculation"
            result_record['Rule Explanation'] = f"Error: {str(e)}"
            calculated_data.append(result_record)
    
    return calculated_data

def process_files(policy_file_bytes: bytes, policy_filename: str, policy_content_type: str, company_name: str):
    """Main processing function with enhanced error handling"""
    try:
        logger.info("=" * 50)
        logger.info(f"🚀 Starting file processing for {policy_filename}...")
        logger.info(f"📁 File size: {len(policy_file_bytes)} bytes")
        
        # Extract text
        logger.info("🔍 Extracting text from policy image...")
        extracted_text = extract_text_from_file(policy_file_bytes, policy_filename, policy_content_type)
        logger.info(f"✅ Extracted text length: {len(extracted_text)} chars")

        if not extracted_text.strip():
            logger.error("No text extracted from the image")
            raise ValueError("No text could be extracted. Please ensure the image is clear and contains readable text.")

        # Parse with AI
        logger.info("🧠 Parsing policy data with AI...")
        
        parse_prompt="""Analyze this insurance policy text and extract structured data.

Company Name: {company_name}

CRITICAL INSTRUCTIONS:
1. ALWAYS return a valid JSON ARRAY (list) of objects, even if there's only one record
2. Each object must have these EXACT field names:
   - "Segment": LOB + policy type (e.g., "TW TP", "PVT CAR COMP", "CV upto 2.5 Tn")
   - "Location": location/region information (use "N/A" if not found)
   - "Policy Type": policy type details (use "COMP/TP" if not specified)
   - "Payin": percentage value (convert decimals: 0.625 → 62.5%, or keep as is: 34%)
   - "Doable District": district info (use "N/A" if not found)
   - "Remarks": additional info including vehicle makes, age, transaction type, validity

3. For Segment field:
   - Identify LOB: TW, PVT CAR, CV, BUS, TAXI, MISD
   - Add policy type: TP, COMP, SAOD, etc.
   - For CV: preserve tonnage (e.g., "CV upto 2.5 Tn")

4. For Payin field:
   - If you see decimals like 0.625, convert to 62.5%
   - If you see whole numbers like 34, add % to make 34%
   - If you see percentages, keep them as is
   - Use the value from the "PO" column or any column that indicates payout/payin
   - Do not use values from "Discount" column for Payin

5. For Remarks field - extract ALL additional info:
   - Vehicle makes (Tata, Maruti, etc.) → "Vehicle Makes: Tata, Maruti"
   - Age info (>5 years, etc.) → "Age: >5 years"
   - Transaction type (New/Old/Renewal) → "Transaction: New"
   - Validity dates → "Validity till: [date]"
   - Decline RTO information (e.g., "Decline RTO: Dhar, Jhabua")
   - Combine with semicolons: "Vehicle Makes: Tata; Age: >5 years; Transaction: New"

IMPORTANT: 
- If a field is not found, use "N/A"
- Return ONLY the JSON array, no other text
- Ensure the JSON is valid and parseable
- Do not extract or include the "Discount" column or its values in any field. Ignore it completely.
- The "PO" column contains the Payin values - use that for the "Payin" field.
- The table may have a "Discount" column - IGNORE it completely. Do not include its values anywhere, not even in remarks.
IGNORE these columns completely - DO NOT extract them:
   - Discount
   - CD1
   - Any column containing "discount" or "cd1" 
   - These are not needed for our analysis

NOTE:
- Taxi PCV comes under the category of Taxi
- Multiple columns are there which has payouts based on either policy type or fuel type , so consider that as payin
- PCV < 6 STR comes under Taxi
-PC means Private Car and STP = TP
- Kali Pilli or Kaali Pilli means Taxi and it comes under Taxi

Here is the training Data:
I am training you

### Overview of How the Data is Given

The data in the provided images consists of screenshots from emails (mostly from Gmail or similar interfaces) and a few from spreadsheets (likely Excel) or chat apps (like WhatsApp or Teams). These appear to be internal communications from InduSind Insurance (previously Reliance General Insurance, as noted in the domain change from relianceada.com to indusindinsurance.com). The emails discuss revisions, extensions, or approvals of "PO" (Payout) rates for various motor insurance segments. Key themes:

- **Format and Structure**: 
  - Emails typically start with a "NOTE" about the email domain change.
  - They include greetings, brief explanations (e.g., "revised PO rate," "grid extended"), and then list data in bullet points, simple tables, or inline text.
  - Data is organized by **RTO (Regional Transport Office)/Region/Zone**, **Segment (vehicle type, e.g., PCV Taxi, TW SAOD, PVT Car)**, **Policy Type (e.g., STP/TP for Third Party, SAOD for Stand Alone Own Damage, Comp for Comprehensive)**, **Fuel Type (e.g., Diesel, Non-Diesel, Petrol)**, and **Payout Percentage**.
  - Additional details include applicability (e.g., for NCB - No Claim Bonus - policies only, specific months like June/July/Aug 2025, vehicle CC/GVW limits, or bonuses like "Jul Bonanza").
  - Spreadsheets show tabular data with columns like RTO, Payout, Product, focusing on specific segments like PCV 3W (Passenger Carrying Vehicle 3-Wheeler).
  - Dates: Emails range from June to August 2025, but the current date is October 15, 2025, suggesting these are historical updates being referenced.

- **Key Concepts in the Data**:
  - **PO/Payout**: This refers to the commission or payout percentage to agents/brokers based on premium "Payin" (not always explicitly mentioned, but implied as the base for calculations).
  - **Segments**: Categorized by vehicle LOB (Line of Business) like TW (Two-Wheeler), PVT Car (Private Car), PCV (Passenger Carrying Vehicle), CV (Commercial Vehicle), Bus, Taxi, etc.
  - **Conditions**: Often include exclusions (e.g., excl MH46 & MH47 RTOs), fuel specifics, NCB requirements, or bonuses for performance targets (e.g., achieving 1.0 Cr in Pvt Car sales).
  - **Patterns**: Rates vary by region (higher in urban areas like Mumbai/Pune), segment (lower for high-risk like Diesel STP), and time (revisions/extensions for specific months). Rates are generally between 20-70%, with adjustments like +2.5% bonuses.
  - **Purpose**: These seem to be strategy updates from teams like "Strategy Group" or individuals (e.g., Ankit Jain, Gaurav Jauhari) to sales/ops teams (e.g., Krunal, Nitin) to inform payout structures for selling policies.

- **Relation to the Provided Code**:
  - The Streamlit code is an app for processing similar insurance policy images: It uses OCR (via OpenAI GPT-4o) to extract text, parses it into structured JSON (fields like Segment, Location, Payin, Remarks), classifies Payin into categories (e.g., Below 20%, 21-30%), applies embedded formula rules (e.g., 90% of Payin, -2% adjustments based on LOB/Segment/Insurer/Payin category), and outputs calculated payouts in tables/Excel.
  - The code's FORMULA_DATA array embeds similar rules (e.g., for TW SAOD + COMP: -2% to -5% based on Payin category; for PVT CAR COMP + SAOD: 90% of Payin).
  - This data in images could be input to such an app: Extracted Payin % would be classified and adjusted per rules. For example, a 55% Payin in "Payin 31% to 50%" category might get -4% adjustment for certain segments.
  - Analysis Depth: The code assumes Payin is from "PO" columns, ignores "Discount," and enhances remarks with details like vehicle makes, age, validity – which align with image data (e.g., fuel types, RTO exclusions).

Now, I'll analyze **each and every image** in depth, numbering them based on their order in your query. For each, I'll:
- **Describe the Presentation**: How data is shown (e.g., list, table).
- **Key Data Points**: Extract and tabulate main info.
- **In-Depth Analysis**: Trends, implications, comparisons to other images, potential calculations per code's formulas, any anomalies.

---

#### Image 1: Email to Krunal, Pankaj, Nitin, me, Rakesh about PC STP (Non-Diesel)
**Presentation**: Simple bulleted list in email body. Starts with NOTE on domain change, greeting, then region/payout details, ending with applicability note and regards.

**Key Data Points**:
| Region | Segment/Policy Type | Payout | Applicability/Remarks |
|--------|---------------------|--------|-----------------------|
| Mumbai all RTO's excl MH46 & MH47 | PC STP (Non-Diesel) | 60% | >1000 CC vehicle |
| Goa | PC STP (Non-Diesel) | 56% | >1000 CC vehicle |

**In-Depth Analysis**:
- Focus on Private Car (PC) Third Party (STP/TP) for Non-Diesel (likely Petrol/CNG). Lower payout in Goa (56%) vs. Mumbai (60%) suggests regional risk variation (e.g., higher claims in Goa?).
- Exclusions: MH46 (possibly Navi Mumbai) & MH47 (Thane) – these might be high-risk RTOs with separate rates.
- Per code: This fits "PVT CAR" LOB, "PVT CAR TP" segment. For "Rest of Companies" (assuming InduSind), if Payin=60% ("Payin Above 50%"), formula could be -5% (payout=55%). But code has special note for Zuno at 21 – not applicable here.
- Trend: Base rates for urban vs. coastal; no bonuses mentioned. Compared to later images, this seems like a baseline for Non-Diesel, potentially revised upward in extensions.

---

#### Image 2: Email from Krunal Vora forwarding about PCV<6STR "Kolkata" for June 2025
**Presentation**: Forwarded email with subject, cc list, NOTE on domain, then numbered list of rates.

**Key Data Points**:
| Segment | Fuel Type | Payout | Applicability/Remarks |
|---------|-----------|--------|-----------------------|
| PCV<6STR "Kolkata" | Diesel | 50% | Revised for June 2025 |
| PCV<6STR "Kolkata" | Other Diesel | 52.5% | Revised for June 2025 |

**In-Depth Analysis**:
- PCV<6STR likely Passenger Carrying Vehicle <6 Seater (e.g., small taxis). "Other Diesel" might mean non-standard or specific variants.
- Revision implies previous rates were different (possibly lower/higher – not specified). Kolkata-specific, indicating location-based adjustments.
- Per code: Fits "TAXI" LOB (since PCV<6STR is noted as Taxi). For "All Companies," if Payin=50% ("Payin 31% to 50%"), formula -4% (payout=46%). For 52.5% ("Above 50%"), -5% (47.5%).
- Trend: Lower rates for Diesel (higher risk/fuel costs?). Compared to Image 3, this seems pre-revision (50% vs. later 55%).

---

#### Image 3: Email from Ankit Jain about revision for PCV Taxi <6STR (Diesel - STP), Kolkata
**Presentation**: Bullet points for segment, RTO, revised rate. Short and direct.

**Key Data Points**:
| Segment | Policy Type | RTO | Revised Payout | Remarks |
|---------|-------------|-----|----------------|---------|
| PCV Taxi <6STR | Diesel - STP | Kolkata | 55% | Revision from previous grid |

**In-Depth Analysis**:
- Specific to Diesel Third Party (STP) for small taxis. Increase to 55% suggests incentive to sell more in Kolkata.
- Per code: "TAXI" LOB, "Payin Above 50%" → -5% adjustment (payout=50%).
- Trend: Builds on Image 2 (from 50% to 55%), showing progressive revisions. No fuel variants here, focused on one sub-segment.

---

#### Image 4: Forwarded email from Gaurav Jauhari about extended grid for Aug25 & Sep25
**Presentation**: List of RTO/Segment/Payout bullets, with NOTE on domain.

**Key Data Points**:
| RTO | Segment | Payout | Remarks |
|-----|---------|--------|---------|
| Mumbai | PCV Taxi NND <6str (non-Diesel) | 55% | Extended for Aug/Sep 2025 |
| Mumbai | Kali Pilli | 67.5% | Extended (Kali Pilli = Taxi, per code note) |
| Mumbai | PCV 3W | 68.5% | Extended |
| Pune | PCV 3W | 70.0% | Extended |

**In-Depth Analysis**:
- Extension from previous months, focusing on Mumbai/Pune. Higher rates for 3W (68.5-70%) vs. Taxi (55-67.5%), possibly lower risk in 3-wheelers.
- "NND" likely Non-Diesel. Kali Pilli (Yellow-Black taxis) treated as Taxi.
- Per code: For "TAXI" (Kali Pilli/PCV Taxi), Payin 55-70% ("Above 50%") → -5% (payout 50-65%). For PCV 3W, might fall under "CV" LOB ("PCV 3W" in rules), -5% if >50%.
- Trend: Urban focus (Mumbai/Pune higher than others in later images). Compared to Image 9/10 spreadsheets, matches PCV 3W rates but extends timeline.

---

#### Image 5: Email from Gaurav Jauhari about extended grid for Jul, with NCB table
**Presentation**: Table with zones, SAOD/Comp rates for Petrol/Diesel. Plus bonanza note.

**Key Data Points**:
| Zone | SAOD Petrol | SAOD Diesel | Comp Petrol | Remarks |
|------|-------------|-------------|-------------|---------|
| East | 30% | 30% | 30% | With NCB only; Non-NCB/Comp Diesel use strategy grid |
| North | 30% | 30% | 30% | Same |
| West | 30% | 30% | 30% | Same |
| South | 30% | 30% | 20% | Same |

- Jul Bonanza: +2.5% on above if achieving 1.0 Cr in Pvt Car (Ex STP) for Jul.

**In-Depth Analysis**:
- Zonal uniformity except South Comp Petrol (20% lower – higher risk?). NCB requirement incentivizes low-claim policies.
- Per code: "PVT CAR" LOB, "PVT CAR COMP + SAOD". All Payin 20-30% ("21-30%" or "Below 20%") → -3% or -2% (payout 17-27%).
- Trend: Lower rates than regional ones in other images; bonanza adds performance incentive. Similar to Image 7 but for Jul extension.

---

#### Image 6: Email about TW SAOD - MP / CG - Bike
**Presentation**: Simple bullets for payout, RTO.

**Key Data Points**:
| Segment | Payout | RTO | Remarks |
|---------|--------|-----|---------|
| TW SAOD - Bike | 25% | MP & CG | Approved rates |

**In-Depth Analysis**:
- Two-Wheeler Stand Alone Own Damage, Madhya Pradesh/Chhattisgarh only. 25% is moderate.
- Per code: "TW" LOB, "TW SAOD + COMP". Payin 25% ("21-30%") → -3% (payout 22%).
- Trend: Regional (central India), lower than urban taxi rates. Standalone, no bonuses.

---

#### Image 7: Private Car Grid for Jun25, similar to Image 5
**Presentation**: Table like Image 5, with additional notes.

**Key Data Points**: Identical table to Image 5, but for Jun. Jun Bonanza +2.5%. Additional: "Additional enabler on Pvt Car will Not be applicable."

**In-Depth Analysis**:
- Mirrors Image 5 but for June, with no extra enablers (e.g., no bonuses beyond bonanza).
- Per code: Same as Image 5 calculations.
- Trend: Consistent zonal structure; "Not applicable" note suggests restrictions vs. Jul extension.

---

#### Image 8: Email from Krunal Vora forwarding about Motor PO Grid - Aug25 revision
**Presentation**: Bullets identical to Image 3 (PCV Taxi <6STR Diesel - STP, Kolkata, 55%).

**Key Data Points**: Same as Image 3.

**In-Depth Analysis**: Duplicate of Image 3, but forwarded in Aug context. Indicates ongoing revisions. Per code: Same as Image 3.

---

#### Image 9: Spreadsheet screenshot for PCV 3W
**Presentation**: Excel table snippet (columns D-F: RTO, Payout, Product).

**Key Data Points**:
| RTO | Payout | Product |
|-----|--------|---------|
| Mumbai | 67.50% | PCV 3W |
| Pune | 67.50% | PCV 3W |
| ROM | 60.00% | PCV 3W |
| Surat | 62.50% | PCV 3W |
| Ahmedabad, Vadodara, Gandhinagar | 60.00% | PCV 3W |

**In-Depth Analysis**:
- PCV 3W (3-Wheeler Passenger). Highest in Mumbai/Pune (67.5%), lower in Gujarat (60-62.5%). "ROM" likely Rest of Maharashtra.
- Per code: "CV" LOB ("PCV 3W" rule), Payin >50% → -5% (payout 55-62.5%).
- Trend: Gujarat lower, urban Maharashtra higher. Matches Image 4 extensions.

---

#### Image 10: Chat from Nitin Deshmukh with spreadsheet
**Presentation**: Similar Excel snippet as Image 9, plus text notes.

**Key Data Points**: Table identical to Image 9. Notes: "PCV 3W (Non Diesel) is continued for Jun'35. No additional enabler except VLI 10:32 Pl note this grid is applicable for mentioned RTO 10:32"

**In-Depth Analysis**:
- Continuation for Non-Diesel PCV 3W into "Jun'35" (typo for 2025?). "VLI" possibly Vehicle Loan Insurance or enabler.
- Per code: Same as Image 9.
- Trend: Emphasizes limitations (no extra enablers, RTO-specific). Duplicate table reinforces consistency.

### Overview of How the Data is Given (Continued)

This set of images continues the theme from the previous ones: internal emails from IndusInd Insurance (noting the domain change from relianceada.com to indusindinsurance.com) discussing payout (PO) rate extensions, revisions, and bonuses for motor insurance segments. The focus is on zonal, regional, and segment-specific rates, often with conditions like NCB (No Claim Bonus) applicability or performance bonuses (e.g., Jul Bonanza). Dates reference July to September 2025, but viewed in October 2025 context, suggesting archival or ongoing policy updates.

- **Format and Structure**: Emails feature NOTES on domain changes, greetings, explanatory text, tables or bullets for rates, and sign-offs. Data covers **Zones/Regions/RTOs**, **Segments (e.g., SAOD, Comp, PCV Taxi)**, **Fuel Types (Petrol, Diesel, Non-Diesel/NND)**, **Policy Types (e.g., STP/TP)**, and **Payout Percentages**. Bonuses and restrictions (e.g., NCB-only, non-NCB rates from separate grids) are common.
- **Key Concepts**: PO rates are commissions; higher in certain zones/segments to incentivize sales. Revisions show adjustments (e.g., 50% to 55%). Segments align with LOBs like PVT CAR, TAXI, CV.
- **Patterns**: Uniform zonal rates (30% common), urban premiums (Mumbai/Pune higher), Diesel often lower-risk adjusted. Bonanzas add 2.5% for targets.
- **Relation to Code**: These could be inputs for the Streamlit app's OCR/parsing. Payin % (from PO) classified (e.g., 30% as "21-30%"), adjusted per FORMULA_DATA (e.g., PVT CAR COMP + SAOD: 90% of Payin; TAXI: -3% for 21-30%). Remarks capture bonuses, validity, fuel.

Below, in-depth analysis for **each and every image** (numbered 1-6 based on order). Each includes presentation, key data (tabulated), and analysis (trends, implications, code links, comparisons).

---

#### Image 1: Email from Gaurav Jauhari about Extended Grid for Jul, with NCB Table
**Presentation**: Table for SAOD/Comp rates by zone/fuel, under "With NCB" header. Text notes applicability for NCB policies only; non-NCB/Comp Diesel use strategy team grid. Ends with Jul Bonanza details.

**Key Data Points**:
| Zone | SAOD Petrol | SAOD Diesel | Comp Petrol | Remarks |
|------|-------------|-------------|-------------|---------|
| East | 30% | 30% | 30% | Extended for Jul; NCB only |
| North | 30% | 30% | 30% | Same |
| West | 30% | 30% | 30% | Same |
| South | 30% | 30% | 20% | Same |

- Jul Bonanza: +2.5% additional on above segment upon achieving 1.0 Cr in Pvt Car (Ex STP) for July.

**In-Depth Analysis**:
- Zonal structure with uniformity (30% most places), but South Comp Petrol at 20% indicates higher risk/lower incentives there (possibly due to claims data or market saturation).
- NCB emphasis rewards claim-free policies; separate grid for non-NCB suggests lower rates elsewhere. Bonanza ties to sales targets (1 Cr = 10 million INR), promoting volume in Private Cars excluding Third Party.
- Per code: "PVT CAR" LOB, "PVT CAR COMP + SAOD" segment. Payin 20-30% ("Below 20%" or "21-30%") → -2% or -3% adjustment (payout 18-27%). Bonanza could be added in remarks; code's classify_payin would categorize base before bonus.
- Trend: Incentive-focused for July; compared to previous set's June grid (Image 7), identical rates but extended timeline. Lower South rates consistent across sets, hinting at regional strategy. Anomalies: No Diesel Comp column – explicitly deferred to another grid.

---

#### Image 2: Duplicate Email from Gaurav Jauhari about Extended Grid for Jul
**Presentation**: Identical to Image 1, including table, notes, and bonanza.

**Key Data Points**: Same as Image 1.

**In-Depth Analysis**: This appears as a repeat (possibly screenshot artifact or emphasis). No new data, but reinforces July extension. In context, it might indicate forwarding or multiple views.
- Per code: Identical processing.
- Trend: Duplication suggests importance of NCB rates; compared to revisions in other images (e.g., Kolkata-specific), this is broad zonal vs. localized.

---

#### Image 3: Email from Ankit Jain about Revision for PCV Taxi <6STR (Diesel - STP), Kolkata
**Presentation**: Bullets for segment, RTO, revised rate. Concise, with thanks and contact.

**Key Data Points**:
| Segment | Policy Type | RTO | Revised Payout | Remarks |
|---------|-------------|-----|----------------|---------|
| PCV Taxi <6STR | Diesel - STP | Kolkata | 55% | Revision from previous grid |

**In-Depth Analysis**:
- Targeted at small passenger vehicles (<6 seater taxis), Diesel Third Party only. 55% revision up from potential prior (e.g., 50% in previous set's Image 2), to boost sales in Kolkata amid competition or low uptake.
- "STP" = Stand-alone Third Party, high-risk coverage (liability only), hence moderate rate.
- Per code: "TAXI" LOB (PCV <6STR noted as Taxi). Payin 55% ("Above 50%") → -5% (payout 50%). Remarks would capture "Diesel; STP; Revision".
- Trend: Location-specific upward adjustment; compared to zonal grids (Images 1/2), this is granular. In series, shows evolution (50% → 55%). Anomalies: No non-Diesel mention – perhaps covered elsewhere.

---

#### Image 4: Duplicate Email from Gaurav Jauhari about Extended Grid for Jul
**Presentation**: Same as Images 1/2.

**Key Data Points**: Same as Image 1.

**In-Depth Analysis**: Repeat, possibly for emphasis in conversation thread. No additions.
- Per code: Same.
- Trend: Highlights consistency in zonal NCB rates across communications.

---

#### Image 5: Email from Nitin Deshmukh about PCV <6 STR NND Update for Kolkata, Aug 2025
**Presentation**: Bullets for product/region/period/types with payouts. Differentiates Comp vs. STP, Diesel vs. Non-Diesel.

**Key Data Points**:
| Segment | Type | Fuel | Payout | Remarks |
|---------|------|------|--------|---------|
| PCV <6 STR NND | Comp | Non-Diesel | 55% | Kolkata RTO; 01st-31st Aug 2025 |
| PCV <6 STR NND | Comp | Diesel | 52.5% | Same |
| PCV <6 STR NND | STP | Non-Diesel | 57.5% | Same |
| PCV <6 STR NND | STP | Diesel | 57% | Same |

**In-Depth Analysis**:
- "NND" = Non-Named Driver? But context suggests Non-Diesel (Petrol/CNG). Higher STP rates (57-57.5%) vs. Comp (52.5-55%) – unusual, as TP often riskier; perhaps Kolkata-specific incentives for liability coverage.
- August focus, post-July bonanza, indicating monthly rollouts. Diesel slightly lower (risk premium).
- Per code: "TAXI" LOB. Payin 52.5-57.5% ("Above 50%") → -5% (payout 47.5-52.5%). Remarks: "Validity: Aug 2025; Kolkata RTO; Fuel specifics".
- Trend: Builds on Image 3's revision (55% Diesel STP aligns closely). Compared to previous set's 50-52.5%, shows increase. Anomalies: "NND" ambiguity – if Non-Diesel, fits patterns; higher STP could target renewals.

---

#### Image 6: Forwarded Email from Krunal Vora about Extended Grid for Aug25 & Sep25
**Presentation**: Bulleted list of RTO/Segment/Payout, with extension note.

**Key Data Points**:
| RTO | Segment | Payout | Remarks |
|-----|---------|--------|---------|
| Mumbai | PCV Taxi NND <6str (Non-Diesel) | 55% | Extended for Aug/Sep 2025 |
| Mumbai | Kali Pilli | 67.5% | Same (Kali Pilli = Taxi) |
| Mumbai | PCV 3W | 68.5% | Same |
| Pune | PCV 3W | 70.0% | Same |

**In-Depth Analysis**:
- Extension into fall 2025, focusing Maharashtra urban areas. Higher rates for 3W (68.5-70%) vs. Taxi (55-67.5%), possibly due to lower claims in auto-rickshaws. "NND" likely Non-Diesel; Kali Pilli (black-yellow taxis) premium at 67.5%.
- Per code: "TAXI" for PCV Taxi/Kali Pilli, "CV" for PCV 3W. Payin >50% ("Above 50%") → -5% (payout 50-65%). Remarks: "Extended validity; Non-Diesel".
- Trend: Urban bias (Mumbai/Pune high); matches previous set's Image 4. Compared to Kolkata-focused (Images 3/5), higher overall – regional disparity. Anomalies: No Diesel rates – perhaps in separate grids; ties to spreadsheets in prior set (e.g., 67.5% Mumbai PCV 3W).

Text to analyze:
{extracted_text}        
        
"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a data extraction expert. Extract policy data as a JSON array. Convert all Payin values to percentage format. Always return valid JSON array with complete field names. Extract all additional information for remarks."
                    },
                    {"role": "user", "content": parse_prompt}
                ],
                temperature=0.0,
                max_tokens=4000
            )
            
            parsed_json = response.choices[0].message.content.strip()
            logger.info(f"Raw parsing response length: {len(parsed_json)}")
            
            cleaned_json = clean_json_response(parsed_json)
            logger.info(f"Cleaned JSON length: {len(cleaned_json)}")
            
            try:
                policy_data = json.loads(cleaned_json)
                policy_data = ensure_list_format(policy_data)
                
                if not policy_data or len(policy_data) == 0:
                    raise ValueError("Parsed data is empty")
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)} with cleaned JSON: {cleaned_json[:500]}...")
                raise ValueError(f"JSON parsing failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error in AI parsing: {str(e)}")
            raise ValueError(f"AI parsing failed: {str(e)}")

        logger.info(f"✅ Successfully parsed {len(policy_data)} policy records")

        # Classify payin
        logger.info("🧮 Classifying payin values...")
        for record in policy_data:
            try:
                if 'Discount' in record:
                    del record['Discount']
                payin_val, payin_cat = classify_payin(record.get('Payin', '0%'))
                record['Payin_Value'] = payin_val
                record['Payin_Category'] = payin_cat
            except Exception as e:
                logger.warning(f"Error classifying payin: {e}")
                record['Payin_Value'] = 0.0
                record['Payin_Category'] = "Payin Below 20%"

        # Apply formulas
        logger.info("🧮 Applying formulas and calculating payouts...")
        calculated_data = apply_formula_directly(policy_data, company_name)
        
        if not calculated_data or len(calculated_data) == 0:
            logger.error("No data after formula application")
            raise ValueError("No data after formula application")

        logger.info(f"✅ Successfully calculated {len(calculated_data)} records")

        # Create Excel
        logger.info("📊 Creating Excel file...")
        df_calc = pd.DataFrame(calculated_data)
        
        if df_calc.empty:
            logger.error("DataFrame is empty")
            raise ValueError("DataFrame is empty")

        output = BytesIO()
        try:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_calc.to_excel(writer, sheet_name='Policy Data', startrow=2, index=False)
                worksheet = writer.sheets['Policy Data']
                headers = list(df_calc.columns)
                for col_num, value in enumerate(headers, 1):
                    cell = worksheet.cell(row=3, column=col_num, value=value)
                    cell.font = cell.font.copy(bold=True)
                if len(headers) > 1:
                    company_cell = worksheet.cell(row=1, column=1, value=company_name)
                    worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
                    company_cell.font = company_cell.font.copy(bold=True, size=14)
                    company_cell.alignment = company_cell.alignment.copy(horizontal='center')
                    title_cell = worksheet.cell(row=2, column=1, value='Policy Data with Payin and Calculated Payouts')
                    worksheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
                    title_cell.font = title_cell.font.copy(bold=True, size=12)
                    title_cell.alignment = title_cell.alignment.copy(horizontal='center')
                else:
                    worksheet.cell(row=1, column=1, value=company_name)
                    worksheet.cell(row=2, column=1, value='Policy Data with Payin and Calculated Payouts')

        except Exception as e:
            logger.error(f"Error creating Excel file: {str(e)}")
            raise ValueError(f"Error creating Excel: {str(e)}")

        output.seek(0)
        excel_data = output.read()
        excel_data_base64 = base64.b64encode(excel_data).decode('utf-8')

        # Calculate metrics
        avg_payin = sum([r.get('Payin_Value', 0) for r in calculated_data]) / len(calculated_data) if calculated_data else 0.0
        unique_segments = len(set([r.get('Segment', 'N/A') for r in calculated_data]))
        formula_summary = {}
        for record in calculated_data:
            formula = record.get('Formula Used', 'Unknown')
            formula_summary[formula] = formula_summary.get(formula, 0) + 1

        logger.info("✅ Processing completed successfully")
        logger.info("=" * 50)
        
        return {
            "extracted_text": extracted_text,
            "parsed_data": policy_data,
            "calculated_data": calculated_data,
            "excel_data": excel_data_base64,
            "csv_data": df_calc.to_csv(index=False),
            "json_data": json.dumps(calculated_data, indent=2),
            "formula_data": FORMULA_DATA,
            "metrics": {
                "total_records": len(calculated_data),
                "avg_payin": round(avg_payin, 1),
                "unique_segments": unique_segments,
                "company_name": company_name,
                "formula_summary": formula_summary
            }
        }

    except Exception as e:
        logger.error(f"Unexpected error in process_files: {str(e)}", exc_info=True)
        raise

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve a basic HTML frontend or instructions"""
    try:
        html_path = Path("index.html")
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        else:
            html_content = """
            <h1>Insurance Policy Processing System</h1>
            <p>Welcome to the Insurance Policy Processing API.</p>
            <h2>Usage Instructions:</h2>
            <ul>
                <li><b>Endpoint:</b> POST /process</li>
                <li><b>Parameters:</b>
                    <ul>
                        <li><b>company_name</b>: String (form-data, required)</li>
                        <li><b>policy_file</b>: Image file (PNG, JPG, JPEG, GIF, BMP, TIFF; file upload, required)</li>
                    </ul>
                </li>
                <li><b>Response:</b> JSON object containing extracted text, parsed data, calculated data, Excel/CSV/JSON files, and metrics.</li>
                <li><b>Health Check:</b> GET /health</li>
            </ul>
            <h2>Features:</h2>
            <ul>
                <li>AI-powered OCR using GPT-4o for text extraction</li>
                <li>Structured data parsing with detailed remarks</li>
                <li>Payout calculations based on embedded formula rules</li>
                <li>Downloadable Excel, CSV, and JSON outputs</li>
            </ul>
            """
            return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error serving HTML: {str(e)}")
        return HTMLResponse(content=f"<h1>Error loading page</h1><p>{str(e)}</p>", status_code=500)

@app.post("/process")
async def process_policy(company_name: str = Form(...), policy_file: UploadFile = File(...)):
    """Process policy image and return extracted and calculated data"""
    try:
        logger.info("=" * 50)
        logger.info(f"📨 Received request for company: {company_name}")
        logger.info(f"📄 File: {policy_file.filename}, Content-Type: {policy_file.content_type}")
        
        # Read file
        policy_file_bytes = await policy_file.read()
        if len(policy_file_bytes) == 0:
            logger.error("Uploaded file is empty")
            return JSONResponse(
                status_code=400,
                content={"error": "Uploaded file is empty"}
            )

        logger.info(f"📦 File size: {len(policy_file_bytes)} bytes")
        
        # Process
        results = process_files(
            policy_file_bytes, 
            policy_file.filename, 
            policy_file.content_type,
            company_name
        )
        
        logger.info("✅ Returning results to client")
        return JSONResponse(content=results)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Processing failed: {str(e)}"}
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(content={"status": "healthy", "message": "Server is running"})

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Insurance Policy Processing System...")
    logger.info("📡 Server will be available at: http://localhost:8000")
    logger.info("🔑 OpenAI API Key is configured: ✅")
    uvicorn.run(app, host="0.0.0.0", port=8000)
