import requests
import streamlit as st


st.set_page_config(page_title="EduReg Agent", layout="wide")

st.title("EduReg Agent")
st.caption("Vietnamese University Regulation RAG Assistant")

backend_url = st.sidebar.text_input("Backend URL", "http://backend:8000")

if st.sidebar.button("Check backend"):
    try:
        response = requests.get(f"{backend_url}/health", timeout=5)
        response.raise_for_status()
        st.sidebar.success("Backend is healthy")
        st.sidebar.json(response.json())
    except Exception as exc:
        st.sidebar.error(f"Backend error: {exc}")

st.subheader("Chat")
question = st.text_input("Ask about university regulations")

if st.button("Send", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        st.info("Chat API will be implemented in the next phase.")
