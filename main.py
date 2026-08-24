import streamlit as st
import numpy as np
import cv2
import pdfplumber
from pdf2image import convert_from_bytes
from collections import defaultdict
import img2pdf

def get_clean_page_image(uploaded_file, page_num):
    """Renders a PDF page to a high-resolution, clear image (300 DPI)."""
    uploaded_file.seek(0)
    images = convert_from_bytes(uploaded_file.read(), dpi=300)
    if page_num < len(images):
        return cv2.cvtColor(np.array(images[page_num]), cv2.COLOR_RGB2BGR)
    return None

def extract_words_grouped_by_rows(uploaded_file, page_num):
    """Extracts words and groups them by their exact row lines using vertical coordinates."""
    uploaded_file.seek(0)
    with pdfplumber.open(uploaded_file) as pdf:
        if page_num < len(pdf.pages):
            page = pdf.pages[page_num]
            scale = 300 / 72  # Convert PDF points to 300 DPI image pixels
            words = page.extract_words()
            
            rows = defaultdict(list)
            for w in words:
                text_clean = w["text"].strip().lower()
                if text_clean:
                    row_key = round(w["top"] / 3) * 3
                    rows[row_key].append({
                        "text": w["text"].strip(),
                        "text_clean": text_clean,
                        "x0": w["x0"],
                        "bbox": [
                            int(w["x0"] * scale),
                            int(w["top"] * scale),
                            int(w["x1"] * scale),
                            int(w["bottom"] * scale)
                        ]
                    })
            
            sorted_rows = []
            for r_key in sorted(rows.keys()):
                sorted_row = sorted(rows[r_key], key=lambda x: x["x0"])
                sorted_rows.append(sorted_row)
            return sorted_rows
    return []

st.set_page_config(page_title="Cell-Level PDF Comparator", layout="wide")
st.title("📄 Fine-Grained Table & Document Comparator")
st.write("Isolates precise value discrepancies within rows. Identical text headers and words remain clean.")

col_up1, col_up2 = st.columns(2)
with col_up1:
    file1 = st.file_uploader("Upload Original PDF", type=["pdf"])
with col_up2:
    file2 = st.file_uploader("Upload Revised PDF", type=["pdf"])

if file1 and file2:
    with st.spinner("Executing grid alignment matching..."):
        try:
            with pdfplumber.open(file1) as p1, pdfplumber.open(file2) as p2:
                max_pages = min(len(p1.pages), len(p2.pages))
            
            hl_color = st.color_picker("Choose Highlight Color", "#FFEB3B")
            hex_val = hl_color.lstrip('#')
            rgb = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
            bgr_color = (int(rgb[2]), int(rgb[1]), int(rgb[0])) # Corrected BGR sequence
            
            report_pages = []
            
            for i in range(max_pages):
                st.markdown(f"### 📄 Page {i + 1}")
                
                img1 = get_clean_page_image(file1, i)
                img2 = get_clean_page_image(file2, i)
                if img1 is None or img2 is None:
                    continue
                
                rows1 = extract_words_grouped_by_rows(file1, i)
                rows2 = extract_words_grouped_by_rows(file2, i)
                
                overlay1 = img1.copy()
                overlay2 = img2.copy()
                
                # Check Document 1 vs Document 2 row records
                for r1 in rows1:
                    row_text_v2 = []
                    for r2 in rows2:
                        row_text_v2.extend([w["text_clean"] for w in r2])
                    for w1 in r1:
                        if w1["text_clean"] not in row_text_v2:
                            b = w1["bbox"]
                            cv2.rectangle(overlay1, (b[0], b[1]), (b[2], b[3]), bgr_color, -1)
                
                # Check Document 2 vs Document 1 row records
                for r2 in rows2:
                    row_text_v1 = []
                    for r1 in rows1:
                        row_text_v1.extend([w["text_clean"] for w in r1])
                    for w2 in r2:
                        if w2["text_clean"] not in row_text_v1:
                            b = w2["bbox"]
                            cv2.rectangle(overlay2, (b[0], b[1]), (b[2], b[3]), bgr_color, -1)
                
                final_img1 = cv2.addWeighted(img1, 0.75, overlay1, 0.25, 0)
                final_img2 = cv2.addWeighted(img2, 0.75, overlay2, 0.25, 0)
                
                # Render screen preview columns
                disp_col1, disp_col2 = st.columns(2)
                with disp_col1:
                    st.caption("Original Version")
                    st.image(cv2.cvtColor(final_img1, cv2.COLOR_BGR2RGB), use_container_width=True)
                with disp_col2:
                    st.caption("Revised Version")
                    st.image(cv2.cvtColor(final_img2, cv2.COLOR_BGR2RGB), use_container_width=True)
                st.markdown("---")
                
                # FIXED: Resize second image to match the height of the first before concatenating
                h1, w1 = final_img1.shape[:2]
                h2, w2 = final_img2.shape[:2]
                if h1 != h2:
                    # Scale width proportionally to maintain aspect ratio without distortion
                    new_w2 = int(w2 * h1 / h2)
                    final_img2_resized = cv2.resize(final_img2, (new_w2, h1))
                else:
                    final_img2_resized = final_img2

                # Combine original and resized layouts safely side-by-side for the PDF report
                side_by_side_canvas = np.hstack((final_img1, final_img2_resized))
                _, encoded_img = cv2.imencode(".png", side_by_side_canvas)
                report_pages.append(encoded_img.tobytes())
            
            # Generate the compiled comparison file
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
            st.error(f"Error executing comparison grid: {e}")
else:
    st.info("Upload your document versions to map targeted line modifications.")
