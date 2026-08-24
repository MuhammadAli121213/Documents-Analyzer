import streamlit as st
import numpy as np
import cv2
import pdfplumber
from pdf2image import convert_from_bytes
import difflib

def get_clean_page_image(uploaded_file, page_num):
    """Renders a PDF page to a high-resolution, clear image (300 DPI)."""
    uploaded_file.seek(0)
    images = convert_from_bytes(uploaded_file.read(), dpi=300)
    if page_num < len(images):
        return cv2.cvtColor(np.array(images[page_num]), cv2.COLOR_RGB2BGR)
    return None

def extract_words_with_positions(uploaded_file, page_num):
    """Extracts words and their exact spatial coordinates on the page."""
    uploaded_file.seek(0)
    with pdfplumber.open(uploaded_file) as pdf:
        if page_num < len(pdf.pages):
            page = pdf.pages[page_num]
            scale = 300 / 72  # Map 72 DPI PDF coordinates to 300 DPI high-res canvas
            
            words = page.extract_words()
            processed_words = []
            for w in words:
                text_clean = w["text"].strip().lower()
                if text_clean:
                    processed_words.append({
                        "text": w["text"].strip(),
                        "text_clean": text_clean,
                        "bbox": [
                            int(w["x0"] * scale),
                            int(w["top"] * scale),
                            int(w["x1"] * scale),
                            int(w["bottom"] * scale)
                        ]
                    })
            return processed_words
    return []

st.set_page_config(page_title="Symmetrical PDF Comparator", layout="wide")
st.title("📄 Symmetrical Side-by-Side Comparison")
st.write("Displays clear differences highlighted on BOTH versions simultaneously while ignoring case variations.")

col_up1, col_up2 = st.columns(2)
with col_up1:
    file1 = st.file_uploader("Upload Original PDF", type=["pdf"])
with col_up2:
    file2 = st.file_uploader("Upload Revised PDF", type=["pdf"])

if file1 and file2:
    with st.spinner("Analyzing document differences symmetrically..."):
        try:
            with pdfplumber.open(file1) as p1, pdfplumber.open(file2) as p2:
                max_pages = min(len(p1.pages), len(p2.pages))
            
            # Highlight color configuration
            hl_color = st.color_picker("Choose Highlight Color", "#FFEB3B")
            hex_val = hl_color.lstrip('#')
            rgb = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
            bgr_color = (int(rgb[2]), int(rgb[1]), int(rgb[0])) # Correctly ordered BGR integer tuple
            
            for i in range(max_pages):
                st.markdown(f"### 📄 Page {i + 1}")
                
                img1 = get_clean_page_image(file1, i)
                img2 = get_clean_page_image(file2, i)
                
                if img1 is None or img2 is None:
                    continue
                
                words1 = extract_words_with_positions(file1, i)
                words2 = extract_words_with_positions(file2, i)
                
                text_list1 = [w["text_clean"] for w in words1]
                text_list2 = [w["text_clean"] for w in words2]
                
                matcher = difflib.SequenceMatcher(None, text_list1, text_list2)
                
                overlay1 = img1.copy()
                overlay2 = img2.copy()
                
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag != 'equal':
                        # Highlight changes on the Original Document (Left side)
                        for idx in range(i1, i2):
                            if idx < len(words1):
                                b = words1[idx]["bbox"]
                                # Fixed: Mapping [x0, top, x1, bottom] coordinates correctly
                                cv2.rectangle(overlay1, (b[0], b[1]), (b[2], b[3]), bgr_color, -1)
                        
                        # Highlight changes on the Revised Document (Right side)
                        for idx in range(j1, j2):
                            if idx < len(words2):
                                b = words2[idx]["bbox"]
                                # Fixed: Mapping [x0, top, x1, bottom] coordinates correctly
                                cv2.rectangle(overlay2, (b[0], b[1]), (b[2], b[3]), bgr_color, -1)
                
                # Translucent opacity blend over the original high-resolution texts
                final_img1 = cv2.addWeighted(img1, 0.7, overlay1, 0.3, 0)
                final_img2 = cv2.addWeighted(img2, 0.7, overlay2, 0.3, 0)
                
                disp_col1, disp_col2 = st.columns(2)
                with disp_col1:
                    st.caption("Original Version (Differences Highlighted)")
                    st.image(cv2.cvtColor(final_img1, cv2.COLOR_BGR2RGB), use_container_width=True)
                with disp_col2:
                    st.caption("Revised Version (Differences Highlighted)")
                    st.image(cv2.cvtColor(final_img2, cv2.COLOR_BGR2RGB), use_container_width=True)
                st.markdown("---")
                
        except Exception as e:
            st.error(f"Error executing comparison sequence: {e}")
else:
    st.info("Upload two PDF files to observe matching highlights side-by-side.")
