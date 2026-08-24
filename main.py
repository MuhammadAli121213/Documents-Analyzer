import streamlit as st
import difflib
from pypdf import PdfReader

def extract_text_from_pdf(uploaded_file):
    """Extracts all text from a PDF file."""
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text.splitlines()

# Set up page layout
st.set_page_config(page_title="PDF Document Comparator", layout="wide")
st.title("📄 PDF Document Comparison Application")
st.write("Upload two PDF documents to compare text changes side-by-side.")

# Create two upload columns
col1, col2 = st.columns(2)

with col1:
    file1 = st.file_uploader("Upload Original PDF", type=["pdf"])

with col2:
    file2 = st.file_uploader("Upload Revised PDF", type=["pdf"])

# Process files if both are uploaded
if file1 and file2:
    try:
        # Extract text from both PDF files
        doc1_lines = extract_text_from_pdf(file1)
        doc2_lines = extract_text_from_pdf(file2)
        
        st.subheader("Comparison Result")
        st.write("🟢 **Green**: Added | 🔴 **Red**: Deleted | 🟡 **Yellow**: Changed")
        
        # Generate an interactive HTML side-by-side diff
        diff = difflib.HtmlDiff()
        html_diff = diff.make_file(
            doc1_lines, 
            doc2_lines, 
            fromdesc="Original PDF", 
            todesc="Revised PDF"
        )
        
        # Display the comparison table inside the app
        st.components.v1.html(html_diff, height=700, scrolling=True)
        st.success("Comparison complete!")
        
    except Exception as e:
        st.error(f"Error processing files: {e}. Ensure they are valid, text-based PDF files.")
else:
    st.info("Please upload both PDF documents to see the differences.")
