from fastapi import FastAPI, File, UploadFile, Form
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
    raise RuntimeError("OPENAI_API_KEY environment variable not set")

# Initialize OpenAI client
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("✅ OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize OpenAI client: {str(e)}")
    raise RuntimeError(f"Failed to initialize OpenAI client: {str(e)}")

app = FastAPI(title="Insurance Policy Processing System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://reliance-image-report.vercel.app"],  # Your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simplified Formula Data - Only for Digit
# FORMULA_DATA = [
#     {"LOB": "TW", "SEGMENT": "1+5", "PO": "90% of Payin", "REMARKS": "NIL"},
#     {"LOB": "TW", "SEGMENT": "TW SAOD + COMP", "PO": "-2%", "REMARKS": "Payin Below 20%"},
#     {"LOB": "TW", "SEGMENT": "TW SAOD + COMP", "PO": "-3%", "REMARKS": "Payin 21% to 30%"},
#     {"LOB": "TW", "SEGMENT": "TW SAOD + COMP", "PO": "-4%", "REMARKS": "Payin 31% to 50%"},
#     {"LOB": "TW", "SEGMENT": "TW SAOD + COMP", "PO": "-5%", "REMARKS": "Payin Above 50%"},
#     {"LOB": "TW", "SEGMENT": "TW TP", "PO": "-3%", "REMARKS": "Payin Above 20%"},
#     {"LOB": "TW", "SEGMENT": "TW TP", "PO": "-2%", "REMARKS": "Payin Below 20%"},
#     {"LOB": "PVT CAR", "SEGMENT": "PVT CAR COMP + SAOD", "PO": "90% of Payin", "REMARKS": "NIL"},
#     {"LOB": "PVT CAR", "SEGMENT": "PVT CAR TP", "PO": "-2%", "REMARKS": "Payin Below 20%"},
#     {"LOB": "PVT CAR", "SEGMENT": "PVT CAR TP", "PO": "-3%", "REMARKS": "Payin Above 20%"},
#     {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "PO": "-2%", "REMARKS": "Payin Below 20%"},
#     {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "PO": "-3%", "REMARKS": "Payin 21% to 30%"},
#     {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "PO": "-4%", "REMARKS": "Payin 31% to 50%"},
#     {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "PO": "-5%", "REMARKS": "Payin Above 50%"},
#     {"LOB": "BUS", "SEGMENT": "SCHOOL BUS", "PO": "Less 2% of Payin", "REMARKS": "NIL"},
#     {"LOB": "BUS", "SEGMENT": "STAFF BUS", "PO": "88% of Payin", "REMARKS": "NIL"},
#     {"LOB": "TAXI", "SEGMENT": "TAXI", "PO": "-2%", "REMARKS": "Payin Below 20%"},
#     {"LOB": "TAXI", "SEGMENT": "TAXI", "PO": "-3%", "REMARKS": "Payin 21% to 30%"},
#     {"LOB": "TAXI", "SEGMENT": "TAXI", "PO": "-4%", "REMARKS": "Payin 31% to 50%"},
#     {"LOB": "TAXI", "SEGMENT": "TAXI", "PO": "-5%", "REMARKS": "Payin Above 50%"},
#     {"LOB": "MISD", "SEGMENT": "Misd, Tractor", "PO": "88% of Payin", "REMARKS": "NIL"}
# ]

FORMULA_DATA = [
    {"LOB": "TW", "SEGMENT": "1+5","PO": "90% of Payin", "REMARKS": "NIL"},
    {"LOB": "TW", "SEGMENT": "TW SAOD + COMP",  "PO": "90% of Payin", "REMARKS": "NIL"},

    {"LOB": "TW", "SEGMENT": "TW TP", "PO": "-2%", "REMARKS": "Payin Below 20%"},
    {"LOB": "TW", "SEGMENT": "TW TP", "PO": "-3%", "REMARKS": "Payin 21% to 30%"},
    {"LOB": "TW", "SEGMENT": "TW TP", "PO": "-4%", "REMARKS": "Payin 31% to 50%"},
    {"LOB": "TW", "SEGMENT": "TW TP", "PO": "-5%", "REMARKS": "Payin Above 50%"},


    {"LOB": "PVT CAR", "SEGMENT": "PVT CAR COMP + SAOD", "PO": "90% of Payin", "REMARKS": "All Fuel"},

    
    
    {"LOB": "PVT CAR", "SEGMENT": "PVT CAR TP", "PO": "90% of Payin", "REMARKS": "Zuno - 21"},


    {"LOB": "CV", "SEGMENT": "Upto 2.5 GVW", "PO": "-2%", "REMARKS": "NIL"},
    {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "PO": "-2%", "REMARKS": "Payin Below 20%"},
    {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "PO": "-3%", "REMARKS": "Payin 21% to 30%"},
    {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "PO": "-4%", "REMARKS": "Payin 31% to 50%"},
    {"LOB": "CV", "SEGMENT": "All GVW & PCV 3W, GCV 3W", "PO": "-5%", "REMARKS": "Payin Above 50%"},


    {"LOB": "BUS", "SEGMENT": "SCHOOL BUS", "PO": "Less 2% of Payin", "REMARKS": "NIL"},

    {"LOB": "BUS", "SEGMENT": "STAFF BUS", "PO": "88% of Payin", "REMARKS": "NIL"},
    {"LOB": "TAXI", "SEGMENT": "TAXI", "PO": "-2%", "REMARKS": "Payin Below 20%"},
    {"LOB": "TAXI", "SEGMENT": "TAXI", "PO": "-3%", "REMARKS": "Payin 21% to 30%"},
    {"LOB": "TAXI", "SEGMENT": "TAXI", "PO": "-4%", "REMARKS": "Payin 31% to 50%"},
    {"LOB": "TAXI", "SEGMENT": "TAXI", "PO": "-5%", "REMARKS": "Payin Above 50%"},


    {"LOB": "MISD", "SEGMENT": "Misd, Tractor", "INSURER": "Reliance", "PO": "88% of Payin", "REMARKS": "NIL"}
]
def extract_text_from_file(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Extract text from uploaded image file using GPT-4o"""
    file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
    
    if file_extension not in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'] and not content_type.startswith('image/'):
        raise ValueError(f"Unsupported file type: {filename}")
    
    try:
        image_base64 = base64.b64encode(file_bytes).decode('utf-8')
        
        prompt = """
You are extracting insurance policy data from an image. Return a JSON array with these exact keys: segment, policy_type, location, payin, remark.

STEP-BY-STEP EXTRACTION:

STEP 1: Identify the vehicle/policy category
- 2W, MC, MCY, SC, Scooter, EV → TWO WHEELER
- PVT CAR, Car, PCI → PRIVATE CAR  
- CV, GVW, PCV, GCV, tonnage → COMMERCIAL VEHICLE
- Bus → BUS
- Taxi → TAXI
- Tractor, Ambulance, Misd → MISCELLANEOUS

STEP 2: Identify policy type from columns
- 1+1 column = Comp
- SATP column = TP
- If both exist, create TWO separate records

STEP 3: Map to EXACT segment (MANDATORY):

TWO WHEELER:
  IF 1+1 OR Comp OR SAOD → segment = "TW SAOD + COMP"
  IF SATP OR TP → segment = "TW TP"
  IF New/Fresh/1+5 → segment = "1+5"
  NEVER use "2W", "MC", "Scooter" as segment

PRIVATE CAR:
  IF 1+1 OR Comp OR SAOD → segment = "PVT CAR COMP + SAOD"
  IF SATP OR TP → segment = "PVT CAR TP"
  and 4W means 4 wheeler means Private Car 

COMMERCIAL VEHICLE:
  ALWAYS → segment = "All GVW & PCV 3W, GCV 3W"
  (Digit treats all CV the same regardless of tonnage)

BUS:
  IF School → segment = "SCHOOL BUS"
  ELSE → segment = "STAFF BUS"

TAXI:
  segment = "TAXI"

MISCELLANEOUS:
  segment = "Misd, Tractor"

STEP 4: Extract other fields
- policy_type: "Comp" or "TP"
- location: Cluster/Agency name
- payin: ONLY CD2 value as NUMBER (ignore CD1)
- remark: Additional details as STRING

CRITICAL RULES:
- payin must be numeric (63.0 not "63.0%")
- Create separate records if both 1+1 and SATP columns exist
- NEVER use raw names like "2W" in segment
- Handle negative % as positive


If this data is given :
PCVC Auto: Upto 2 years : 69%
above 2 years:70%
4W TP,2W COMP,4W COMP and Non Eb 2.5% VLI for year 25-26

then please consider 

PCV Auto  which is PCV 3w as Auto is 3W which is 69% bove 2 years , 70% and remark should be upto 2 years if parsed 69%
and above 2 years if parsed 70%
and a

I hope you 

also there is one more column , if CD2 or any other column is given then consider that column as payin value,
if it contains multiplestuff

for example : COMP and sub column : CD2 contains for example Tata 30%; any other makes : 28%/26%, then consider the lowest value please , so the output should contain for both , 30% and the remark Tata , and 26% , in the remark other make 


Also note is CV is mentioned upto 2.5TN then consider it as Upto 2.5 GVW segment
and if CV is mentioned above 2.5TN then consider it as All GVW & PCV 3W, GCV 3W segment

Sometimes the data given is in the form of table okay ?
There's one input given where the column name is SAOD and the sub column are petrol , diesel , same for the column Comp and sub column is petrol , diesel
So I want you to extract those values under the sub columns petrol and diesel separately as different records 
please do so 
for example, here is the data given below as an example 

| With NCB | SAOD        |   SAOD      |   Comp      |
|-----------|-------------|-------------|-------------|
|           | Petrol      | Diesel      | Petrol      |       |
|----------|-------------|-------------|-------------|
| East     | 30%         | 30%         | 30%         |
| North    | 30%         | 30%         | 30%         |
| West     | 30%         | 30%         | 30%         |
| South    | 30%         | 30%         | 20%         |


This is how the data is given , so now what I want you to do is 

Segment : "PVT CAR COMP + SAOD"
policy_type : "Comp"
location : East
payin : 30.0
remark : "SAOD Petrol"

DO THIS FOR EVERY value , as in example total 12 values there

Return ONLY JSON array, no markdown.

"""
       
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
        
        # Clean markdown formatting
        cleaned_text = re.sub(r'```json\s*|\s*```', '', extracted_text).strip()
        
        # Extract JSON array
        start_idx = cleaned_text.find('[')
        end_idx = cleaned_text.rfind(']') + 1
        if start_idx != -1 and end_idx > start_idx:
            cleaned_text = cleaned_text[start_idx:end_idx]
        
        # Validate JSON
        json.loads(cleaned_text)
        return cleaned_text
        
    except Exception as e:
        logger.error(f"Error in OCR extraction: {str(e)}")
        return "[]"

def classify_payin(payin_value):
    """Classify payin into categories"""
    try:
        if isinstance(payin_value, (int, float)):
            payin_float = float(payin_value)
        else:
            payin_clean = str(payin_value).replace('%', '').replace(' ', '').replace('-', '').strip()
            if not payin_clean or payin_clean.upper() == 'N/A':
                return 0.0, "Payin Below 20%"
            payin_float = float(payin_clean)
        
        if payin_float <= 20:
            return payin_float, "Payin Below 20%"
        elif payin_float <= 30:
            return payin_float, "Payin 21% to 30%"
        elif payin_float <= 50:
            return payin_float, "Payin 31% to 50%"
        else:
            return payin_float, "Payin Above 50%"
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse payin: {payin_value}, error: {e}")
        return 0.0, "Payin Below 20%"

def determine_lob(segment: str) -> str:
    """Determine LOB from segment"""
    segment_upper = segment.upper()
    
    if any(kw in segment_upper for kw in ['TW', '2W', 'MC', 'SC', '1+5']):
        return "TW"
    elif any(kw in segment_upper for kw in ['PVT CAR', 'CAR', 'PCI']):
        return "PVT CAR"
    elif any(kw in segment_upper for kw in ['CV', 'GVW', 'PCV', 'GCV']):
        return "CV"
    elif 'BUS' in segment_upper:
        return "BUS"
    elif 'TAXI' in segment_upper:
        return "TAXI"
    elif any(kw in segment_upper for kw in ['MISD', 'TRACTOR']):
        return "MISD"
    
    return "UNKNOWN"

# def apply_formula(policy_data):
#     """Apply formula rules and calculate payouts"""
#     if not policy_data:
#         return []
    
#     calculated_data = []
    
#     for record in policy_data:
#         try:
#             segment = str(record.get('segment', ''))
#             payin_value = record.get('Payin_Value', 0)
#             payin_category = record.get('Payin_Category', '')
            
#             lob = determine_lob(segment)
#             segment_upper = segment.upper()
            
#             # Find matching rule
#             matched_rule = None
#             for rule in FORMULA_DATA:
#                 # Match LOB
#                 if rule["LOB"] != lob:
#                     continue
                
#                 # Match Segment
#                 rule_segment = rule["SEGMENT"].upper()
#                 if rule_segment not in segment_upper:
#                     continue
                
#                 # Match Payin Category or NIL
#                 remarks = rule.get("REMARKS", "")
#                 if remarks == "NIL" or payin_category in remarks:
#                     matched_rule = rule
#                     break
            
#             # Calculate payout
#             if matched_rule:
#                 po_formula = matched_rule["PO"]
#                 calculated_payout = payin_value
                
#                 if "90% of Payin" in po_formula:
#                     calculated_payout *= 0.9
#                 elif "88% of Payin" in po_formula:
#                     calculated_payout *= 0.88
#                 elif "Less 2%" in po_formula or "-2%" in po_formula:
#                     calculated_payout -= 2
#                 elif "-3%" in po_formula:
#                     calculated_payout -= 3
#                 elif "-4%" in po_formula:
#                     calculated_payout -= 4
#                 elif "-5%" in po_formula:
#                     calculated_payout -= 5
                
#                 calculated_payout = max(0, calculated_payout)
#                 formula_used = po_formula
#                 rule_explanation = f"Match: LOB={lob}, Segment={rule_segment}, {remarks}"
#             else:
#                 calculated_payout = payin_value
#                 formula_used = "No matching rule"
#                 rule_explanation = f"No rule for LOB={lob}, Segment={segment_upper}"
            
#             # Format remark
#             remark_value = record.get('remark', '')
#             if isinstance(remark_value, list):
#                 remark_value = '; '.join(str(r) for r in remark_value)
            
#             calculated_data.append({
#                 'segment': segment,
#                 'policy type': record.get('policy_type', 'Comp'),
#                 'location': record.get('location', 'N/A'),
#                 'payin': f"{payin_value:.2f}%",
#                 'remark': str(remark_value),
#                 'Calculated Payout': f"{calculated_payout:.2f}%",
#                 'Formula Used': formula_used,
#                 'Rule Explanation': rule_explanation
#             })
            
#         except Exception as e:
#             logger.error(f"Error processing record {record}: {str(e)}")
#             calculated_data.append({
#                 'segment': str(record.get('segment', 'Unknown')),
#                 'policy type': record.get('policy_type', 'Comp'),
#                 'location': record.get('location', 'N/A'),
#                 'payin': str(record.get('payin', '0%')),
#                 'remark': str(record.get('remark', 'Error')),
#                 'Calculated Payout': "Error",
#                 'Formula Used': "Error",
#                 'Rule Explanation': f"Error: {str(e)}"
#             })
    
#     return calculated_data
def apply_formula(policy_data):
    """Apply formula rules and calculate payouts"""
    if not policy_data:
        return []
    
    calculated_data = []
    
    for record in policy_data:
        try:
            segment = str(record.get('segment', '')).strip()
            payin_value = float(record.get('Payin_Value', 0))
            payin_category = record.get('Payin_Category', '').strip()
            
            lob = determine_lob(segment)
            segment_clean = re.sub(r'\s+', ' ', segment.upper())

            # Debug log
            logger.debug(f"Processing: LOB={lob}, Segment='{segment}', Payin={payin_value}, Cat='{payin_category}'")

            # Find matching rule
            matched_rule = None
            matched_explanation = ""
            for rule in FORMULA_DATA:
                rule_lob = rule["LOB"]
                rule_segment_raw = rule["SEGMENT"]
                rule_segment_clean = re.sub(r'\s+', ' ', rule_segment_raw.strip().upper())
                remarks = rule.get("REMARKS", "").strip()
                remarks_lower = remarks.lower()

                # Skip if LOB doesn't match
                if rule_lob != lob:
                    continue

                # Skip if segment doesn't contain rule segment
                if rule_segment_clean not in segment_clean:
                    continue

                # Flexible REMARKS logic
                remarks_match = (
                    remarks == "NIL" or
                    remarks == "" or
                    "all fuel" in remarks_lower or
                    payin_category in remarks
                )

                if remarks_match:
                    matched_rule = rule
                    matched_explanation = (
                        f"Matched: LOB={lob}, "
                        f"Segment='{rule_segment_raw}', "
                        f"REMARKS='{remarks}', "
                        f"PayinCat='{payin_category}'"
                    )
                    logger.debug(f"  Rule Matched: {matched_explanation}")
                    break
                else:
                    logger.debug(f"  Skipped: REMARKS='{remarks}' doesn't match PayinCat='{payin_category}'")

            # Apply payout
            if matched_rule:
                po_formula = matched_rule["PO"]
                calculated_payout = payin_value

                if "90% of Payin" in po_formula:
                    calculated_payout *= 0.9
                elif "88% of Payin" in po_formula:
                    calculated_payout *= 0.88
                elif "Less 2% of Payin" in po_formula or "-2%" in po_formula:
                    calculated_payout -= 2
                elif "-3%" in po_formula:
                    calculated_payout -= 3
                elif "-4%" in po_formula:
                    calculated_payout -= 4
                elif "-5%" in po_formula:
                    calculated_payout -= 5

                calculated_payout = max(0.0, calculated_payout)
                formula_used = po_formula
                rule_explanation = matched_explanation
            else:
                calculated_payout = payin_value
                formula_used = "No matching rule"
                rule_explanation = f"No rule for LOB={lob}, Segment='{segment}', PayinCat='{payin_category}'"
                logger.warning(f"No rule matched: {rule_explanation}")

            # Format remark
            remark_value = record.get('remark', '')
            if isinstance(remark_value, list):
                remark_value = '; '.join(str(r).strip() for r in remark_value if r)
            remark_value = str(remark_value)

            calculated_data.append({
                'segment': segment,
                'policy type': record.get('policy_type', 'Comp'),
                'location': record.get('location', 'N/A'),
                'payin': f"{payin_value:.2f}%",
                'remark': remark_value,
                'Calculated Payout': f"{calculated_payout:.2f}%",
                'Formula Used': formula_used,
                'Rule Explanation': rule_explanation
            })
            
        except Exception as e:
            logger.error(f"Error processing record {record}: {str(e)}", exc_info=True)
            calculated_data.append({
                'segment': str(record.get('segment', 'Unknown')),
                'policy type': record.get('policy_type', 'Comp'),
                'location': record.get('location', 'N/A'),
                'payin': '0.00%',
                'remark': 'Processing Error',
                'Calculated Payout': "Error",
                'Formula Used': "Error",
                'Rule Explanation': f"Error: {str(e)}"
            })
    
    return calculated_data

def process_files(policy_file_bytes: bytes, policy_filename: str, policy_content_type: str, company_name: str):
    """Main processing function"""
    try:
        logger.info(f"🚀 Processing {policy_filename} for {company_name}")
        
        # Extract text
        extracted_text = extract_text_from_file(policy_file_bytes, policy_filename, policy_content_type)
        
        if not extracted_text or extracted_text == "[]":
            raise ValueError("No text extracted from image")
        
        # Parse JSON
        policy_data = json.loads(extracted_text)
        if isinstance(policy_data, dict):
            policy_data = [policy_data]
        
        if not policy_data:
            raise ValueError("No policy data found")
        
        logger.info(f"✅ Parsed {len(policy_data)} records")
        
        # Classify payin
        for record in policy_data:
            payin_val, payin_cat = classify_payin(record.get('payin', 0))
            record['Payin_Value'] = payin_val
            record['Payin_Category'] = payin_cat
        
        # Apply formulas
        calculated_data = apply_formula(policy_data)
        
        if not calculated_data:
            raise ValueError("No data after formula application")
        
        logger.info(f"✅ Calculated {len(calculated_data)} records")
        
        # Create Excel
        df = pd.DataFrame(calculated_data)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Policy Data', startrow=2, index=False)
            worksheet = writer.sheets['Policy Data']
            
            # Format headers
            for col_num, value in enumerate(df.columns, 1):
                cell = worksheet.cell(row=3, column=col_num, value=value)
                cell.font = cell.font.copy(bold=True)
            
            # Add title
            title_cell = worksheet.cell(row=1, column=1, value=f"{company_name} - Policy Data")
            worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(df.columns))
            title_cell.font = title_cell.font.copy(bold=True, size=14)
            title_cell.alignment = title_cell.alignment.copy(horizontal='center')
        
        output.seek(0)
        excel_data_base64 = base64.b64encode(output.read()).decode('utf-8')
        
        # Calculate metrics
        avg_payin = sum([r['Payin_Value'] for r in policy_data]) / len(policy_data)
        formula_summary = {}
        for record in calculated_data:
            formula = record['Formula Used']
            formula_summary[formula] = formula_summary.get(formula, 0) + 1
        
        return {
            "extracted_text": extracted_text,
            "parsed_data": policy_data,
            "calculated_data": calculated_data,
            "excel_data": excel_data_base64,
            "csv_data": df.to_csv(index=False),
            "json_data": json.dumps(calculated_data, indent=2),
            "formula_data": FORMULA_DATA,
            "metrics": {
                "total_records": len(calculated_data),
                "avg_payin": round(avg_payin, 1),
                "unique_segments": len(set([r['segment'] for r in calculated_data])),
                "company_name": company_name,
                "formula_summary": formula_summary
            }
        }
    
    except Exception as e:
        logger.error(f"Error in process_files: {str(e)}", exc_info=True)
        raise

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve HTML frontend"""
    html_path = Path("index.html")
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Insurance Policy Processing System</h1><p>Upload via POST /process</p>")

@app.post("/process")
async def process_policy(company_name: str = Form(...), policy_file: UploadFile = File(...)):
    """Process policy image"""
    try:
        policy_file_bytes = await policy_file.read()
        if not policy_file_bytes:
            return JSONResponse(status_code=400, content={"error": "Empty file"})
        
        results = process_files(policy_file_bytes, policy_file.filename, policy_file.content_type, company_name)
        return JSONResponse(content=results)
        
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Processing failed: {str(e)}"})

@app.get("/health")
async def health_check():       
    """Health check"""
    return JSONResponse(content={"status": "healthy"})

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting server at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
