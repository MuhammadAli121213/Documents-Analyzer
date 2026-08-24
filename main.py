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

st.set_page_config(page_title="Side-by-Side PDF Comparator", layout="wide")
st.title("👁️ Side-by-Side Visual PDF Comparison")
st.write("Compare document variations side-by-side with localized structural adjustments highlighted.")

# Global file upload interface
col_upload1, col_upload2 = st.columns(2)
with col_upload1:
    file1 = st.file_uploader("Upload Original PDF", type=["pdf"])
with col_upload2:
    file2 = st.file_uploader("Upload Revised PDF", type=["pdf"])

if file1 and file2:
    with st.spinner("Aligning layout structures..."):
        try:
            # Render PDF pages to native image formats
            pages1 = process_pdf_to_images(file1)
            pages2 = process_pdf_to_images(file2)
            
            # Find the common number of pages to safely compare
            max_pages = min(len(pages1), len(pages2))
            
            st.subheader("Comparison View")
            st.write("🔴 **Red Highlights**: Indicate content differences, formatting movement, or design shifts.")
            
            for i in range(max_pages):
                img1 = pages1[i].copy()
                img2 = pages2[i].copy()
                
                # Enforce identical image canvas sizing to line up comparison points
                if img1.shape != img2.shape:
                    img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
                
                # Convert to grayscale to map physical structural variations
                gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
                
                # Calculate absolute structural changes between layouts
                diff = cv2.absdiff(gray1, gray2)
                _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
                
                # Create red tint sheets for isolated changes
                highlight1 = img1.copy()
                highlight2 = img2.copy()
                
                # Apply red indicator masks to coordinates where changes appear
                highlight1[thresh > 0] = [0, 0, 255]
                highlight2[thresh > 0] = [0, 0, 255]
                
                # Merge the highlight sheet back with the clean layout for clear transparency
                overlay1 = cv2.addWeighted(img1, 0.75, highlight1, 0.25, 0)
                overlay2 = cv2.addWeighted(img2, 0.75, highlight2, 0.25, 0)
                
                st.markdown(f"### 📄 Page {i + 1}")
                
                # Partition the page preview area into side-by-side blocks
                display_col1, display_col2 = st.columns(2)
                
                with display_col1:
                    st.caption("Original Version")
                    st.image(cv2.cvtColor(overlay1, cv2.COLOR_BGR2RGB), use_container_width=True)
                    
                with display_col2:
                    st.caption("Revised Version")
                    st.image(cv2.cvtColor(overlay2, cv2.COLOR_BGR2RGB), use_container_width=True)
                
                st.markdown("---") # Visual separation line between pages
                
            if len(pages1) != len(pages2):
                st.warning(f"Note: Document page counts differ. (Original: {len(pages1)} pages, Revised: {len(pages2)} pages). Only overlapping pages are shown.")
                
        except Exception as e:
            st.error(f"Could not generate visual comparison: {e}")
else:
    st.info("Upload two PDF files to visually track changes side-by-side.")
