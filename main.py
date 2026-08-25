import streamlit as st
import numpy as np
import cv2
import pdfplumber
from pdf2image import convert_from_bytes
import difflib
import img2pdf

def get_clean_page_image(uploaded_file, page_num):
    """Renders a PDF page to a high-resolution, clear image (300 DPI)."""
    uploaded_file.seek(0)
    images = convert_from_bytes(uploaded_file.read(), dpi=300)
    if page_num < len(images):
        return cv2.cvtColor(np.array(images[page_num]), cv2.COLOR_RGB2BGR)
    return None

def extract_characters_with_positions(uploaded_file, page_num):
    """Extracts every individual character and its exact spatial coordinate."""
    uploaded_file.seek(0)
    with pdfplumber.open(uploaded_file) as pdf:
        if page_num < len(pdf.pages):
            page = pdf.pages[page_num]
            scale = 300 / 72  # Convert standard PDF points to 300 DPI canvas pixels
            
            chars = page.chars
            processed_chars = []
            for c in chars:
                text_clean = c["text"]
                processed_chars.append({
                    "text": text_clean,
                    "text_lower": text_clean.lower(),
                    "bbox": [
                        int(c["x0"] * scale),
                        int(c["top"] * scale),
                        int(c["x1"] * scale),
                        int(c["bottom"] * scale)
                    ]
                })
            return processed_chars
    return []

st.set_page_config(page_title="Sequence PDF Comparator", layout="wide")
st.title("📄 High-Precision Text Sequence Comparator")
st.write("Tracks exact character additions, deletions, and alterations on both documents side-by-side.")

col_up1, col_up2 = st.columns(2)
with col_up1:
    file1 = st.file_uploader("Upload Original PDF", type=["pdf"])
with col_up2:
    file2 = st.file_uploader("Upload Revised PDF", type=["pdf"])

if file1 and file2:
    with st.spinner("Analyzing text sequences..."):
        try:
            with pdfplumber.open(file1) as p1, pdfplumber.open(file2) as p2:
                max_pages = min(len(p1.pages), len(p2.pages))
            
            hl_color = st.color_picker("Choose Highlight Color", "#FFEB3B")
            hex_val = hl_color.lstrip('#')
            rgb = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
            
            # FIXED: Correctly unpack the tuple items individually into BGR values
            bgr_color = (int(rgb[2]), int(rgb[1]), int(rgb[0]))
            
            report_pages = []
            
            for i in range(max_pages):
                st.markdown(f"### 📄 Page {i + 1}")
                
                img1 = get_clean_page_image(file1, i)
                img2 = get_clean_page_image(file2, i)
                if img1 is None or img2 is None:
                    continue
                
                chars1 = extract_characters_with_positions(file1, i)
                chars2 = extract_characters_with_positions(file2, i)
                
                str1 = [c["text_lower"] for c in chars1]
                str2 = [c["text_lower"] for c in chars2]
                
                matcher = difflib.SequenceMatcher(None, str1, str2)
                
                overlay1 = img1.copy()
                overlay2 = img2.copy()
                
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag != 'equal':
                        # Highlights: Left Side Changes
                        for idx in range(i1, i2):
                            if idx < len(chars1):
                                b = chars1[idx]["bbox"]
                                cv2.rectangle(overlay1, (b[0], b[1]), (b[2], b[3]), bgr_color, -1)
                        
                        # Highlights: Right Side Changes
                        for idx in range(j1, j2):
                            if idx < len(chars2):
                                b = chars2[idx]["bbox"]
                                cv2.rectangle(overlay2, (b[0], b[1]), (b[2], b[3]), bgr_color, -1)
                
                final_img1 = cv2.addWeighted(img1, 0.75, overlay1, 0.25, 0)
                final_img2 = cv2.addWeighted(img2, 0.75, overlay2, 0.25, 0)
                
                # Screen visualization output
                disp_col1, disp_col2 = st.columns(2)
                with disp_col1:
                    st.caption("Original Version")
                    st.image(cv2.cvtColor(final_img1, cv2.COLOR_BGR2RGB), use_container_width=True)
                with disp_col2:
                    st.caption("Revised Version")
                    st.image(cv2.cvtColor(final_img2, cv2.COLOR_BGR2RGB), use_container_width=True)
                st.markdown("---")
                
                # Dimension normalization to prevent hstack report rendering crashes
                h1, w1 = final_img1.shape[:2]
                h2, w2 = final_img2.shape[:2]
                if h1 != h2:
                    new_w2 = int(w2 * h1 / h2)
                    final_img2_resized = cv2.resize(final_img2, (new_w2, h1))
                else:
                    final_img2_resized = final_img2

                side_by_side_canvas = np.hstack((final_img1, final_img2_resized))
                _, encoded_img = cv2.imencode(".png", side_by_side_canvas)
                report_pages.append(encoded_img.tobytes())
            
            if report_pages:
                pdf_data = img2pdf.convert(report_pages)
                st.sidebar.subheader("📥 Export Options")
                st.sidebar.download_button(
                    label="Download Comparison Report (PDF)",
                    data=pdf_data,
                    file_name="document_comparison_report.pdf",
                    mime="application/pdf"
                )
                st.sidebar.success("Report generation ready in sidebar!")
                
        except Exception as e:
            st.error(f"Error executing sequence matrix verification: {e}")
else:
    st.info("Upload your document versions to map targeted line modifications.")
