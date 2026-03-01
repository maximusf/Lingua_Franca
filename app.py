# This is the frontend of the app, using Streamlit to create a user interface.
# We will take in input files from the user, such as excel, PDF, etc. 
# and then pass them to the backend for processing.
import json
import streamlit as st

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
    st.set_page_config(page_title="SmartRoute", layout="wide")
    st.title("SmartRoute: Email and Message Information Extraction")
    st.write("Upload your excel files, emails and messages here, and we will extract infomration.")

    #---File uploaders---
    
    # File uploader for Excel files
    excel_file = st.file_uploader("Upload an Excel file", type=["xlsx"])
    # File uploader for PDF files
    pdf_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    
    if excel_file is not None:
        st.write("Excel file uploaded successfully!")
        # Here you can add code to process the Excel file and display results
        
    if pdf_file is not None:
        st.write("PDF file uploaded successfully!")
        # Here you can add code to process the PDF file and display results

    result = {
        ""
    }

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

    st.header("Routing")

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


        


if __name__ == "__main__":
            main()