import os
print("RUNNING FILE:", os.path.abspath(__file__))
import streamlit as st
from extractor import extract_fields

# =========================
# Page Config
# =========================

st.set_page_config(page_title="Raw Text AI Extraction", layout="wide")

st.title("AI Raw Text Extraction")
st.markdown("Upload a .txt file to extract structured JSON using Ollama.")

# =========================
# File Upload (TXT ONLY)
# =========================

uploaded_file = st.file_uploader(
    "Upload .txt File",
    type=["txt"]
)

# =========================
# Main Processing
# =========================

if uploaded_file is not None:

    try:
        raw_text = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.error("Failed to read text file.")
        st.exception(e)
        st.stop()

    st.subheader("Raw Text Preview")
    st.text_area("Preview", raw_text[:3000], height=250)

    if raw_text.strip():

        with st.spinner("Running AI extraction via Ollama..."):
            try:
                extracted = extract_fields(raw_text)

                st.success("Extraction Complete")
                st.subheader("Extracted JSON")
                st.json(extracted)

            except Exception as e:
                st.error("AI extraction failed")
                st.exception(e)

    else:
        st.warning("Uploaded file is empty.")

else:
    st.info("Upload a .txt file to begin.")