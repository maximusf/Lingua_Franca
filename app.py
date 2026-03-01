# This is the frontend of the app, using Streamlit to create a user interface.
# We will take in input files from the user, such as excel, PDF, etc. 
# and then pass them to the backend for processing.
import json
import streamlit as st

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

    #-----Dummy JSON for testing purposes-------
    dummy_json = {
    "name" : "John Doe",
    "predicted_urgency": "High",
    "confidence_score" : 0.82,
    "reasons": ["damage", "outage", "safety"],
    "human_review": False,
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
        st.json(dummy_json)
       

    #-----Routing-------
        
    st.divider()
    st.header("Routing")

    # st.json(dummy_json)


    # Determine if human review is required based on confidence score and human review flag
    confidence = float(dummy_json["confidence_score"])
    human_review_required = (confidence < 0.70) or bool(dummy_json["human_review"])

# Display human review alert if required
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


    #Style the badges based on urgency levels
    urgency_colors = {
        "Critical Urgency": "red",
        "High Urgency": "orange",
        "Medium Urgency": "yellow",
        "Low Urgency": "grey"
    }

    predicted = dummy_json["predicted_urgency"]

    #Horizontal Routing Role
    r1, r2, r3 = st.columns([1, 1, 2])
    with r1:
        st.caption("Predicted Urgency")
        render_badge(predicted, urgency_colors.get(predicted, "grey"))
    with r2:
        st.caption("Predicted Urgency")
        st.metric("Confidence Score", f"{confidence:.2f}")
    with r3:
        st.caption("Reasons / Keywords")
        st.write(", ".join(dummy_json["reasons"]) if dummy_json["reasons"] else "—")


    # if dummy_json["reasons"]: #if reasons exist show them
    #         st.write(", ".join(dummy_json["reasons"]))
    # else: #if reasons dont exist put a line
    #     st.write("—")

    # ----- User selection (override) -----
    urgency_options = ["Critical", "High", "Medium", "Low"]

    if human_review_required:
        selection = st.selectbox(
            "Select urgency to proceed",
            options=["Select…"] + urgency_options,
            index=0,
        )
        confirmed = st.checkbox("I confirm this urgency is correct", value=False)
        can_proceed = (selection != "Select…") and confirmed
    else:
        default_index = urgency_options.index(predicted)
        selection = st.selectbox(
            "Urgency (you can override)",
            options=urgency_options,
            index=default_index,
        )
        can_proceed = True

    # Update JSON based on user selection
    if selection == "Select…":
        dummy_json["user_selected_urgency"] = None
    else:
        dummy_json["user_selected_urgency"] = selection

        # Set user_override to True if user selection differs from predicted urgency
    dummy_json["user_override"] = (
        dummy_json["user_selected_urgency"] is not None
        and dummy_json["user_selected_urgency"] != predicted
    )

    if human_review_required and not can_proceed:
        st.warning("Select an urgency and confirm to proceed.")
        st.button("Confirm & Continue", disabled=True)
    else:
        if st.button("Confirm & Continue"):
            st.success("Selection saved (dummy). Ready to wire to backend later.")

    # ----- Show JSON output -----
    st.subheader("JSON Output")
    st.json(dummy_json)

    # Optional: download JSON
    st.download_button(
        "Download JSON",
        data=json.dumps(dummy_json, indent=2),
        file_name="smartroute_output.json",
        mime="application/json",
    )


        


if __name__ == "__main__":
            main()