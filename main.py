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

def extract_words_with_positions(uploaded_file, page_num):
    """Extracts whole text words along with their clean spatial coordinates."""
    uploaded_file.seek(0)
    with pdfplumber.open(uploaded_file) as pdf:
        if page_num < len(pdf.pages):
            page = pdf.pages[page_num]
            scale = 300 / 72  # Map standard 72 DPI PDF coordinates to 300 DPI high-res canvas
            
            words = page.extract_words()
            processed_words = []
            for w in words:
                text_clean = w["text"].strip()
                if text_clean:
                    processed_words.append({
                        "text": text_clean,
                        "text_lower": text_clean.lower(),
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
            
            # Unpack color properly for OpenCV (BGR Format)
            bgr_color = (int(rgb[2]), int(rgb[1]), int(rgb[0]))
            
            report_pages = []
            
            for i in range(max_pages):
                st.markdown(f"### 📄 Page {i + 1}")
                
                img1 = get_clean_page_image(file1, i)
                img2 = get_clean_page_image(file2, i)
                if img1 is None or img2 is None:
                    continue
                
                words1 = extract_words_with_positions(file1, i)
                words2 = extract_words_with_positions(file2, i)
                
                str1 = [w["text_lower"] for w in words1]
                str2 = [w["text_lower"] for w in words2]
                
                matcher = difflib.SequenceMatcher(None, str1, str2)
                
                overlay1 = img1.copy()
                overlay2 = img2.copy()
                
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag != 'equal':
                        # Highlight discrepancies on the Original Document (Left side)
                        for idx in range(i1, i2):
                            if idx < len(words1):
                                b = words1[idx]["bbox"]
                                cv2.rectangle(overlay1, (b[0], b[1]), (b[2], b[3]), bgr_color, -1)
                        
                        # Highlight discrepancies on the Revised Document (Right side)
                        for idx in range(j1, j2):
                            if idx < len(words2):
                                b = words2[idx]["bbox"]
                                cv2.rectangle(overlay2, (b[0], b[1]), (b[2], b[3]), bgr_color, -1)
                
                # Fixed Alpha Blend values: 0.5/0.5 ratio preserves sharp high-contrast yellow tags clearly
                final_img1 = cv2.addWeighted(img1, 0.5, overlay1, 0.5, 0)
                final_img2 = cv2.addWeighted(img2, 0.5, overlay2, 0.5, 0)
                
                # Render clear side-by-side columns
                disp_col1, disp_col2 = st.columns(2)
                with disp_col1:
                    st.caption("Original Version (Differences Highlighted)")
                    st.image(cv2.cvtColor(final_img1, cv2.COLOR_BGR2RGB), use_container_width=True)
                with disp_col2:
                    st.caption("Revised Version (Differences Highlighted)")
                    st.image(cv2.cvtColor(final_img2, cv2.COLOR_BGR2RGB), use_container_width=True)
                st.markdown("---")
                
                # Combine original and revised layouts into a side-by-side image for the PDF report
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
            st.error(f"Error executing comparison sequence: {e}")
else:
    st.info("Upload two PDF files to observe matching highlights side-by-side.")
