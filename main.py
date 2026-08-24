import streamlit as st
import numpy as np
import cv2
import pdfplumber
from pdf2image import convert_from_bytes
import difflib

def get_clean_page_image(uploaded_file, page_num):
    """Renders a PDF page to a high-resolution, clear image (300 DPI)."""
    uploaded_file.seek(0)
    # 300 DPI ensures text and lines stay razor-sharp and legible
    images = convert_from_bytes(uploaded_file.read(), dpi=300)
    if page_num < len(images):
        img = cv2.cvtColor(np.array(images[page_num]), cv2.COLOR_RGB2BGR)
        return img
    return None

def extract_words_with_positions(uploaded_file, page_num):
    """Extracts words and their exact spatial coordinates on the page."""
    uploaded_file.seek(0)
    with pdfplumber.open(uploaded_file) as pdf:
        if page_num < len(pdf.pages):
            page = pdf.pages[page_num]
            # Get text bounding boxes scaled to 300 DPI resolution coordinates
            width, height = page.width, page.height
            scale = 300 / 72  # Convert PDF points (72dpi) to image pixels (300dpi)
            
            words = page.extract_words()
            processed_words = []
            for w in words:
                processed_words.append({
                    "text": w["text"].strip(),
                    "bbox": [
                        int(w["x0"] * scale),
                        int(w["top"] * scale),
                        int(w["x1"] * scale),
                        int(w["bottom"] * scale)
                    ]
                })
            return processed_words
    return []

st.set_page_config(page_title="High-Res PDF Comparator", layout="wide")
st.title("📄 High-Resolution Document Comparison")
st.write("Compare text changes side-by-side with clear, sharp text rendering and targeted highlights.")

# Upload fields
col_up1, col_up2 = st.columns(2)
with col_up1:
    file1 = st.file_uploader("Upload Original PDF", type=["pdf"])
with col_up2:
    file2 = st.file_uploader("Upload Revised PDF", type=["pdf"])

if file1 and file2:
    with st.spinner("Analyzing document text structures..."):
        try:
            # Read total page count using pdfplumber
            with pdfplumber.open(file1) as p1, pdfplumber.open(file2) as p2:
                max_pages = min(len(p1.pages), len(p2.pages))
            
            # Interactive highlight color selection
            hl_color = st.color_picker("Choose Highlight Color", "#FFEB3B") # Defaults to your clean Yellow
            # Convert Hex color to BGR for OpenCV processing
            hex_val = hl_color.lstrip('#')
            rgb = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
            bgr_color = (rgb[2], rgb[1], rgb[0])
            
            for i in range(max_pages):
                st.markdown(f"### 📄 Page {i + 1}")
                
                # Fetch high-resolution background templates
                img1 = get_clean_page_image(file1, i)
                img2 = get_clean_page_image(file2, i)
                
                if img1 is None or img2 is None:
                    continue
                
                # Pull words and geometry mappings
                words1 = extract_words_with_positions(file1, i)
                words2 = extract_words_with_positions(file2, i)
                
                text_list1 = [w["text"] for w in words1]
                text_list2 = [w["text"] for w in words2]
                
                # SequenceMatcher pinpoints exactly which words changed, were added, or removed
                matcher = difflib.SequenceMatcher(None, text_list1, text_list2)
                
                overlay1 = img1.copy()
                overlay2 = img2.copy()
                
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag != 'equal':
                        # Highlight discrepancies on the original document surface
                        for idx in range(i1, i2):
                            if idx < len(words1):
                                box = words1[idx]["bbox"]
                                cv2.rectangle(overlay1, (box[0], box[1]), (box[2], box[3]), bgr_color, -1)
                        
                        # Highlight discrepancies on the revised document surface
                        for idx in range(j1, j2):
                            if idx < len(words2):
                                box = words2[idx]["bbox"]
                                cv2.rectangle(overlay2, (box[0], box[1]), (box[2], box[3]), bgr_color, -1)
                
                # Blend the solid highlight boxes with the document for transparency (keeps text visible underneath)
                final_img1 = cv2.addWeighted(img1, 0.6, overlay1, 0.4, 0)
                final_img2 = cv2.addWeighted(img2, 0.6, overlay2, 0.4, 0)
                
                # Show crisp side-by-side structures in Streamlit
                disp_col1, disp_col2 = st.columns(2)
                with disp_col1:
                    st.caption("Original Version")
                    st.image(cv2.cvtColor(final_img1, cv2.COLOR_BGR2RGB), use_container_width=True)
                with disp_col2:
                    st.caption("Revised Version")
                    st.image(cv2.cvtColor(final_img2, cv2.COLOR_BGR2RGB), use_container_width=True)
                st.markdown("---")
                
        except Exception as e:
            st.error(f"Error rendering visual display: {e}")
else:
    st.info("Upload two purchase orders or documents to view clear highlights side-by-side.")
