# This is the frontend of the app, using Streamlit to create a user interface.
# We will take in input files from the user, such as excel, PDF, etc. 
# and then pass them to the backend for processing.
import json
import streamlit as st
from PIL import Image

logo_path = "./assets/gridstorm-logo.png"

from pathlib import Path
from backend.extractor import extract_fields
from backend.validator import validate
from backend.urgency import apply_routing


from backend.extract_to_txt import (
    dump_image_to_txt,
    dump_xlsx_to_txt,
    dump_pdf_to_txt
)


def get_record_for_ui(raw_input: str) -> dict:
    # TODO later: call backend -> return InspectionRecord JSON

     return {
          
        #auto-generated metadata
        "incident_id": "abc123",
        "timestamp": "2024-01-01T12:00:00",
        "raw_input": raw_input,

        #extracted fields
        "permit_number": "123456",
        "inspection_type": "RES GAS TEST",
        "result": "PASS",                     # normalized enum values
        "permit_category": "residential",
        "site_address": "123 Main St",
        "county": "Richland",
        "inspection_date": "2024-01-01",
        "description": "Gas inspection for residential property",
        "contact_name": "John Smith",
        "contact_phone": "(555) 123-4567",
        "contact_email": "john.smith@example.com",
        "inspector": "Jane Doe",

        # routing/computed
        "urgency": "high",
        "urgency_score": 4,
        "user_selected_urgency": None, #added for front end user can change
        "user_override": False,
        "routed_to": "field_ops",
        "confidence_score": 0.82,
        "human_review_flag": False,
        "review_reason": None,

     }

def render_badge(label: str, color: str):
    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:6px 14px;
            border-radius:999px;
            background:{color};
            color:white;
            font-weight:700;
            font-size:13px;
            letter-spacing:0.4px;
        ">
            {label.upper()}
        </div>
        """,
        unsafe_allow_html=True
    )


# EXAMPLE 
def main() -> None:
    record = get_record_for_ui(raw_input="dummy raw input string")

    #set page configuration to be wide
    UPLOAD_DIR = Path("data/samples")
    OUT_DIR = Path("data/processed_text")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    
    st.set_page_config(page_title="SmartRoute", layout="wide")

    # Initialize session state for uploaded files and active file selection
    if "files" not in st.session_state:
        st.session_state["files"] = {} 

    # Which file is selected
    if "active_file_id" not in st.session_state:
        st.session_state["active_file_id"] = None

    st.image(logo_path, width=150)
    st.title("SmartRoute: Email and Message Information Extraction")
    st.subheader("Upload your excel files, emails and messages here, and we will extract infomration.")

    #---File uploaders---
    
    # File uploader for Excel files
    user_upload_files = st.file_uploader("Upload a pdf, jpg, png, or xlsx file", type=["xlsx", "jpg", "png", "pdf"], 
                                         accept_multiple_files=True)
    
    if user_upload_files is not None: 
        for uploaded_file in user_upload_files:
            save_path = UPLOAD_DIR / uploaded_file.name
            
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Saved {uploaded_file.name} to {save_path}")
    
    #Chance method for register uploaded files
    if user_upload_files:
        for f in user_upload_files:
            file_id = f"{f.name}-{f.size}"  # simple stable key for hackathon

            if file_id not in st.session_state["files"]:
                st.session_state["files"][file_id] = {
                    "meta": {"name": f.name, "type": f.type, "size": f.size},
                    "record": None,  # will fill after extraction/backend later
                    "ui": {"urgency": None, "routed_to": None, "confirmed": False},
                }

    # ---pick a default active file---
    # checks to see if the dict of files is not empty and if there is no active file selected, 
    # then it selects the first file in the dict as the active file.
    if st.session_state["active_file_id"] is None and len(st.session_state["files"]) > 0: 
        st.session_state["active_file_id"] = next(iter(st.session_state["files"]))

    if st.button("Run Extraction"):
        files = sorted(UPLOAD_DIR.iterdir())
        if not files:
            st.warning("No files uploaded.")
        else:
            results = []
            extracted_records = []  # list of tuples (filename, record_dict or error_str)
            with st.spinner("Running extraction and calling Ollama..."):
                # 1) run your dump_* functions (this is what you already do)
                for p in files:
                    suffix = p.suffix.lower()
                    try:
                        if suffix == ".xlsx":
                            dump_xlsx_to_txt(p, OUT_DIR)
                            results.append((p.name, "xlsx -> dumped"))
                        elif suffix in [".png", ".jpg", ".jpeg"]:
                            dump_image_to_txt(p, OUT_DIR)
                            results.append((p.name, "image -> dumped"))
                        elif suffix == ".pdf":
                            dump_pdf_to_txt(p, OUT_DIR)
                            results.append((p.name, "pdf -> dumped"))
                        else:
                            results.append((p.name, "skipped (unknown type)"))
                    except Exception as e:
                        results.append((p.name, f"DUMP FAILED: {e}"))

                # 2) For each produced .txt in OUT_DIR, run Ollama via extractor.extract_fields
                txt_files = sorted(OUT_DIR.glob("*.txt"))
                for t in txt_files:
                    try:
                        raw_text = t.read_text(encoding="utf-8")
                    except Exception as e:
                        extracted_records.append((t.name, f"READ TXT FAILED: {e}"))
                        continue

                    # Call the Ollama-backed extractor
                    try:
                        llm_extraction = extract_fields(raw_text)  # returns LLMExtraction object per backend/extractor.py
                        # If it's a Pydantic model or dataclass, convert to dict for display
                        try:
                            record_dict = llm_extraction.model_dump(mode="json")  # if Pydantic v2 / pydantic-core
                        except Exception:
                            # fallback: try dict()
                            record_dict = llm_extraction.__dict__ if hasattr(llm_extraction, "__dict__") else dict(llm_extraction)
                        # Optionally validate / route
                        try:
                            validated = validate(llm_extraction, raw_text)
                            routed = apply_routing(validated)
                            # routed may be a pydantic model; convert for display
                            try:
                                routed_dict = routed.model_dump(mode="json")
                            except Exception:
                                routed_dict = getattr(routed, "__dict__", routed)
                        except Exception:
                            # if you don't have validator/urgency set up, skip silently
                            routed_dict = record_dict

                        extracted_records.append((t.name, routed_dict))
                        results.append((t.name, "extraction -> ok"))
                    except ConnectionError as ce:
                        extracted_records.append((t.name, f"OLLM ERROR: {ce}"))
                        results.append((t.name, f"extraction -> failed (Ollama connection)"))
                    except ValueError as ve:
                        extracted_records.append((t.name, f"EXTRACTION ERROR: {ve}"))
                        results.append((t.name, f"extraction -> failed (parse/validation)"))
                    except Exception as e:
                        extracted_records.append((t.name, f"UNEXPECTED ERROR: {e}"))
                        results.append((t.name, f"extraction -> failed ({e})"))

            # end spinner
            st.success("Extraction + LLM pass finished.")
            st.write("Dump results:")
            for name, status in results:
                st.write(f"- {name}: {status}")

            # show extracted records (first one prominently; list others)
            if extracted_records:
                st.divider()
                st.header("LLM-extracted Records (from processed .txt files)")
                for fname, record in extracted_records:
                    st.subheader(fname)
                    if isinstance(record, str):
                        st.error(record)
                    else:
                        st.json(record)
    #-----Dummy JSON for testing purposes-------
    dummy_json = {
    "name" : "John Doe",
    "urgency": "High",
    "confidence_score" : 0.82,
    "reasons": ["damage", "outage", "safety"],
    "human_review_flag": False,
    "review_reason": "string",
    "user_selected_urgency": None,
    "user_override": False,
    "permit_number" : "123456",
    "permit_type" : "residential",
    "date_inspection" : "01-01-2026",

    }

    st.divider()

    #Columns to display extracted info and structured JSON side by side
    col_left, col_right = st.columns(2, gap="small")

    with col_left:
          st.header("Extracted Information")
          # Here you can display the extracted information from the files
          st.text_area("Extracted Information will be displayed here", height=300)
    with col_right:
        st.header("Structured JSON")

        #changed to function that'll read from backend later
        st.json(record)
        
       
   
    #-----Routing-------
        
    st.divider()
    # st.header("Routing")

    # st.json(dummy_json)


    # Determine if human review is required based on confidence score and human review flag
    confidence = float(record["confidence_score"])
    human_review_required = (confidence < 0.70) or bool(record["human_review_flag"])

# Display human review alert if required
   


    #Style the badges based on urgency levels
    URGENCY_COLORS = {
        "critical": "red",
        "high": "orange",
        "medium": "yellow",
        "low": "grey"
    }

    ROUTE_LABELS  = {
         "field_ops": "Field Operations",
         "scheduling": "Scheduling",
         "safety_team": "Safety Team",
         "maintenance": "Maintenance",
        "human_review": "Human Review"
         
    }

    st.markdown("""
        <style>
            /* Style only the bordered container that contains our routing marker */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.routing-marker) {
                background: #eef2ff;              /* light indigo */
                border: 1px solid #c7d2fe;        /* indigo border */
                border-radius: 14px;
                padding: 14px 16px;
            }

            /* Optional: tighten spacing inside the card */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.routing-marker) .block-container {
                padding-top: 0;
            }

            /* Optional: make the Routing header align nicer inside card */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.routing-marker) h2,
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.routing-marker) h3 {
                margin-top: 0.2rem;
            }
        </style>
    """, unsafe_allow_html=True)



    

    # st.markdown(
    # """
    # <div style="background:#eef2ff;padding:12px 14px;border-radius:12px;font-weight:800;margin:12px 0;">
    #     Routing <span title="Urgency = severity, Confidence = model certainty, Route = destination queue." style="cursor:help;color:#666;">ⓘ</span>
    # </div>
    # """,
    # unsafe_allow_html=True
    # )

    

    # List all uploaded files and allow user to select which one to review
    with st.container(border=True):

        st.markdown('<span class="routing-marker" style="display:none;"></span>', unsafe_allow_html=True)

        st.header("Routing")

        file_ids = list(st.session_state["files"].keys())

        if not file_ids:
            st.info("Upload at least one file to review routing.")
            return  # stops the rest of main() so we don't access active_file_id
        
        if st.session_state["active_file_id"] not in st.session_state["files"]:
            st.session_state["active_file_id"] = file_ids[0]

        if file_ids:
            st.session_state["active_file_id"] = st.selectbox(
                "Select a file to review",
                options=file_ids,
                format_func=lambda fid: st.session_state["files"][fid]["meta"]["name"],
            )

        # Get the active file's record and UI state
        active = st.session_state["files"][st.session_state["active_file_id"]]
        ui = active["ui"]
        meta = active["meta"]

        if human_review_required:
                st.markdown(
                """
                <div style="
                    background-color:#ff4b4b;
                    color:white;
                    padding:12px;
                    border-radius:8px;
                    font-weight:800;
                    text-align:center;
                    margin-bottom:10px;
                ">
                    ! HUMAN REVIEW REQUIRED
                </div>
                """,
                unsafe_allow_html=True,
        )

        urgencyScore = record["urgency_score"]

        #Horizontal Routing Role
        r1, r2, r3 = st.columns([1, 1, 2])

        with r1:
                st.metric (
                label = "Urgency",
                value = record["urgency"],
                delta = URGENCY_COLORS.get(record["urgency"], "#7f8c8d"),
                help = f"Predicted urgency based on extracted text. Override if the model is incorrect. Score: {record['urgency_score']} / 5"
                )
            # st.text("Urgency")
            # render_badge(record["urgency"], URGENCY_COLORS.get(record["urgency"], "#7f8c8d"))
            # st.caption(f"Score: {record['urgency_score']} / 5")

        with r2:
            #Creates the ? for the user to see what confidence means
            st.metric(
                label="Confidence",
                value=f"{confidence:.2f}",
                help="0–1 certainty score. Below 0.70 triggers human review."
            )

        with r3:
            st.metric (
                label = "Routed To",
                value = ROUTE_LABELS.get(record["routed_to"], record["routed_to"]),
                help = "The team or department the record is routed to."
            )
            # st.caption("Routing Destination")
            # st.write(ROUTE_LABELS.get(record["routed_to"], record["routed_to"]))



        # ----- User selection (override) -----
        # user override urgency (always allowed)
        URGENCY_OPTIONS = ["critical", "high", "medium", "low"]
        URGENCY_LABELS = {"critical":"Critical", "high":"High", "medium":"Medium", "low":"Low"}

        default_urgency = record["urgency"]



        choice = st.selectbox(
            label="Urgency (you can override)",
            options=URGENCY_OPTIONS,
            index=URGENCY_OPTIONS.index(record["urgency"]),
            help="Predicted urgency based on extracted text. Override if the model is incorrect."
        )

        record["user_selected_urgency"] = choice
        record["user_override"] = (choice != record["urgency"])

        # allow routing override ONLY if human review
        if human_review_required:
            route_choice = st.selectbox(
                "Route to (required for human review)",
                options=list(ROUTE_LABELS.keys()),
                index=list(ROUTE_LABELS.keys()).index(record["routed_to"]),
                format_func=lambda x: ROUTE_LABELS[x],
            )
        record["routed_to"] = route_choice

    st.markdown('</div>', unsafe_allow_html=True)




        


if __name__ == "__main__":
            main()