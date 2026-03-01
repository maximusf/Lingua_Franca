# This is the frontend of the app, using Streamlit to create a user interface.
# We will take in input files from the user, such as excel, PDF, etc.
# and then pass them to the backend for processing.
import re
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
    dump_pdf_to_txt,
    safe_name
)


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


def main() -> None:
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
    st.write("Upload your excel files, emails and messages here, and we will extract information.")

    #---File uploaders---

    # File uploader for Excel files
    user_upload_files = st.file_uploader("Upload a pdf, jpg, png, or xlsx file", type=["xlsx", "jpg", "png", "pdf", "jpeg"],
                                         accept_multiple_files=True)

    if user_upload_files is not None:
        for uploaded_file in user_upload_files:
            save_path = UPLOAD_DIR / uploaded_file.name

            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Saved {uploaded_file.name} to {save_path}")

    #Register uploaded files in session state
    if user_upload_files:
        for f in user_upload_files:
            file_id = f"{f.name}-{f.size}"  # simple stable key for hackathon

            if file_id not in st.session_state["files"]:
                st.session_state["files"][file_id] = {
                    "meta": {"name": f.name, "type": f.type, "size": f.size},
                    "record": None,  # will fill after extraction
                    "raw_text": None,  # raw OCR/parsed text
                    "ui": {"urgency": None, "routed_to": None, "confirmed": False},
                }

    # ---pick a default active file---
    if st.session_state["active_file_id"] is None and len(st.session_state["files"]) > 0:
        st.session_state["active_file_id"] = next(iter(st.session_state["files"]))

    if st.button("Run Extraction"):
        # Only process files that were uploaded (in session state), not everything in the directory
        uploaded_names = [
            file_data["meta"]["name"]
            for file_data in st.session_state["files"].values()
        ]
        if not uploaded_names:
            st.warning("No files uploaded.")
        else:
            results = []
            with st.spinner("Running extraction and calling Ollama..."):
                # 1) Dump each uploaded file to .txt
                for name in uploaded_names:
                    p = UPLOAD_DIR / name
                    if not p.exists():
                        results.append((name, "file not found on disk"))
                        continue
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

                # 2) For each uploaded file, find its .txt and run LLM extraction
                for file_id, file_data in st.session_state["files"].items():
                    orig_name = file_data["meta"]["name"]
                    orig_stem = Path(orig_name).stem
                    txt_name = f"{safe_name(orig_stem)}.txt"
                    txt_path = OUT_DIR / txt_name

                    if not txt_path.exists():
                        results.append((orig_name, "extraction -> skipped (no .txt found)"))
                        continue

                    try:
                        raw_text = txt_path.read_text(encoding="utf-8")
                    except Exception as e:
                        results.append((orig_name, f"READ TXT FAILED: {e}"))
                        continue

                    try:
                        llm_extraction = extract_fields(raw_text)
                        validated = validate(llm_extraction, raw_text)
                        routed = apply_routing(validated)
                        try:
                            routed_dict = routed.model_dump(mode="json")
                        except Exception:
                            routed_dict = getattr(routed, "__dict__", {})

                        # Store results in session state for this file
                        file_data["record"] = routed_dict
                        file_data["raw_text"] = raw_text
                        results.append((orig_name, "extraction -> ok"))
                    except ConnectionError as ce:
                        results.append((orig_name, f"extraction -> failed (Ollama connection: {ce})"))
                    except ValueError as ve:
                        results.append((orig_name, f"extraction -> failed (parse/validation: {ve})"))
                    except Exception as e:
                        results.append((orig_name, f"extraction -> failed ({e})"))

            # end spinner
            st.success("Extraction + LLM pass finished.")
            st.write("Dump results:")
            for name, status in results:
                st.write(f"- **{name}**: {status}")


    #Columns to display extracted info and structured JSON side by side
    st.divider()
    col_left, col_right = st.columns(2, gap="small")

    # Get the active file's data for display
    active_data = _get_active_file_data()

    with col_left:
        st.header("Extracted Information")
        if active_data and active_data.get("raw_text"):
            st.text_area("Raw extracted text", value=active_data["raw_text"], height=300, disabled=True)
        else:
            st.text_area("Extracted Information will be displayed here", height=300, disabled=True)

    with col_right:
        st.header("Structured JSON")
        if active_data and active_data.get("record"):
            st.json(active_data["record"])
        else:
            st.info("Run extraction to see structured results.")

    #-----Routing-------

    st.divider()

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

    # Styled routing card CSS
    st.markdown("""
        <style>
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.routing-marker) {
                background: #eef2ff;
                border: 1px solid #c7d2fe;
                border-radius: 14px;
                padding: 14px 16px;
            }

            div[data-testid="stVerticalBlockBorderWrapper"]:has(.routing-marker) .block-container {
                padding-top: 0;
            }

            div[data-testid="stVerticalBlockBorderWrapper"]:has(.routing-marker) h2,
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.routing-marker) h3 {
                margin-top: 0.2rem;
            }
        </style>
    """, unsafe_allow_html=True)

    # Routing card
    with st.container(border=True):

        st.markdown('<span class="routing-marker" style="display:none;"></span>', unsafe_allow_html=True)

        st.header("Routing")

        file_ids = list(st.session_state["files"].keys())

        if not file_ids:
            st.info("Upload at least one file to review routing.")
            return

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
        record = active.get("record")

        if record is None:
            st.info("No extraction results yet for this file. Run extraction first.")
            return

        # Determine if human review is required based on confidence score and human review flag
        confidence = float(record.get("confidence_score", 0))
        human_review_required = (confidence < 0.70) or bool(record.get("human_review_flag", False))

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

        #Horizontal Routing Row
        r1, r2, r3 = st.columns([1, 1, 2])

        urgency_val = record.get("urgency", "unknown")

        with r1:
            st.metric(
                label="Urgency",
                value=urgency_val,
                delta=URGENCY_COLORS.get(urgency_val, "#7f8c8d"),
                help=f"Predicted urgency based on extracted text. Override if the model is incorrect. Score: {record.get('urgency_score', 'N/A')} / 5"
            )

        with r2:
            st.metric(
                label="Confidence",
                value=f"{confidence:.2f}",
                help="0-1 certainty score. Below 0.70 triggers human review."
            )

        with r3:
            routed_to = record.get("routed_to", "unknown")
            st.metric(
                label="Routed To",
                value=ROUTE_LABELS.get(routed_to, routed_to),
                help="The team or department the record is routed to."
            )

        # ----- User selection (override) -----
        # user override urgency (always allowed)
        URGENCY_OPTIONS = ["critical", "high", "medium", "low"]

        default_idx = URGENCY_OPTIONS.index(urgency_val) if urgency_val in URGENCY_OPTIONS else 1

        choice = st.selectbox(
            label="Urgency (you can override)",
            options=URGENCY_OPTIONS,
            index=default_idx,
            help="Predicted urgency based on extracted text. Override if the model is incorrect."
        )

        record["user_selected_urgency"] = choice
        record["user_override"] = (choice != urgency_val)

        # allow routing override ONLY if human review
        if human_review_required:
            route_choice = st.selectbox(
                "Route to (required for human review)",
                options=list(ROUTE_LABELS.keys()),
                index=list(ROUTE_LABELS.keys()).index(routed_to) if routed_to in ROUTE_LABELS else 0,
                format_func=lambda x: ROUTE_LABELS[x],
            )
            record["routed_to"] = route_choice

    # Show raw_input in an expander
    raw_input = record.get("raw_input")
    if raw_input:
        with st.expander("raw_input"):
            st.text(raw_input)


def _get_active_file_data() -> dict | None:
    """Get the active file's data from session state."""
    active_id = st.session_state.get("active_file_id")
    if active_id and active_id in st.session_state.get("files", {}):
        return st.session_state["files"][active_id]
    return None


if __name__ == "__main__":
    main()
