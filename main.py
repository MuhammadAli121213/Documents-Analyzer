import streamlit as st
import numpy as np
import cv2
from pdf2image import convert_from_bytes

def process_pdf_to_images(uploaded_file):
    """Converts a PDF file into a list of OpenCV images."""
    images = convert_from_bytes(uploaded_file.read())
    # Convert PIL images to OpenCV format (BGR array)
    cv_images = [cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR) for img in images]
    return cv_images

st.set_page_config(page_title="Visual PDF Comparator", layout="wide")
st.title("👁️ Visual PDF Document Comparison")
st.write("Compare documents by layout. Additions and deletions are highlighted directly on the page.")

col1, col2 = st.columns(2)
with col1:
    file1 = st.file_uploader("Upload Original PDF", type=["pdf"])
with col2:
    file2 = st.file_uploader("Upload Revised PDF", type=["pdf"])

if file1 and file2:
    with st.spinner("Analyzing document structures..."):
        try:
            # Render PDF pages to images to preserve exact appearance
            pages1 = process_pdf_to_images(file1)
            pages2 = process_pdf_to_images(file2)
            
            # Find the common number of pages to safely compare
            max_pages = min(len(pages1), len(pages2))
            
            st.subheader("Visual Highlights")
            st.write("🔴 **Red Masks**: Structural differences, text adjustments, or layout movement.")
            
            for i in range(max_pages):
                img1 = pages1[i]
                img2 = pages2[i]
                
                # Resize images to match exactly if sizes differ slightly
                if img1.shape != img2.shape:
                    img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
                
                # Convert to grayscale to evaluate structural changes
                gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
                
                # Calculate absolute differences between the two layouts
                diff = cv2.absdiff(gray1, gray2)
                _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
                
                # Generate a red highlight mask over changes
                highlighted_page = img2.copy()
                highlighted_page[thresh > 0] = [0, 0, 255] # Red highlight mask
                
                # Blend the highlight with the original layout for transparency
                overlay = cv2.addWeighted(img2, 0.7, highlighted_page, 0.3, 0)
                
                # Display the native document layout with inline markings
                st.markdown(f"#### Page {i + 1}")
                st.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB), use_container_width=True)
                
            if len(pages1) != len(pages2):
                st.warning(f"Note: Document page counts differ. (Original: {len(pages1)} pages, Revised: {len(pages2)} pages). Only matching pages were compared.")
                
        except Exception as e:
            st.error(f"Could not generate visual comparison: {e}")
else:
    st.info("Upload two PDF files to visually track changes.")
