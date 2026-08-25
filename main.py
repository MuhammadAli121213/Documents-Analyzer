import streamlit as st
import numpy as np
import cv2
import pdfplumber
from pdf2image import convert_from_bytes
import difflib
import img2pdf
from PIL import Image

# --- MONKEY PATCH TO FIX STREAMLIT VERSION COMPATIBILITY ---
import streamlit.elements.image as st_image
if not hasattr(st_image, "image_to_url"):
    try:
        from streamlit.elements.lib.image_utils import image_to_url
        setattr(st_image, "image_to_url", image_to_url)
    except ImportError:
        pass

# Safe to load drawing tools now
from streamlit_drawable_canvas import st_canvas

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
st.title("📄 Hybrid PDF Comparator & Editing Workspace")
st.write("Differences are auto-highlighted below. Use the canvas sidebar tools to add your own markup manually.")

# Sidebar Manual Settings
st.sidebar.subheader("🖌️ Manual Editor Options")
drawing_mode = st.sidebar.selectbox("Drawing Tool:", ("freedraw", "rect", "transform"))
stroke_width = st.sidebar.slider("Brush Size:", 1, 50, 15)
stroke_color = st.sidebar.color_picker("Manual Marker Color:", "#FF5722") # Orange for manual edits
alpha_hex = "80"  # Transparent brush visibility
full_stroke_color = f"{stroke_color}{alpha_hex}"

col_up1, col_up2 = st.columns(2)
with col_up1:
    file1 = st.file_uploader("Upload Original PDF", type=["pdf"])
with col_up2:
    file2 = st.file_uploader("Upload Revised PDF", type=["pdf"])

if file1 and file2:
    with st.spinner("Analyzing text sequences and building layers..."):
        try:
            with pdfplumber.open(file1) as p1, pdfplumber.open(file2) as p2:
                max_pages = min(len(p1.pages), len(p2.pages))
            
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
                
                # Create automatic yellow background highlights
                auto_overlay1 = img1.copy()
                auto_overlay2 = img2.copy()
                yellow_bgr = (0, 235, 255) # Bright Yellow
                
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag != 'equal':
                        for idx in range(i1, i2):
                            if idx < len(words1):
                                b = words1[idx]["bbox"]
                                cv2.rectangle(auto_overlay1, (b[0], b[1]), (b[2], b[3]), yellow_bgr, -1)
                        for idx in range(j1, j2):
                            if idx < len(words2):
                                b = words2[idx]["bbox"]
                                cv2.rectangle(auto_overlay2, (b[0], b[1]), (b[2], b[3]), yellow_bgr, -1)
                
                # Blend the auto highlights into clean translucent sheets
                base_processed1 = cv2.addWeighted(img1, 0.6, auto_overlay1, 0.4, 0)
                base_processed2 = cv2.addWeighted(img2, 0.6, auto_overlay2, 0.4, 0)
                
                # Convert back to RGB format
                from_array_rgb = cv2.cvtColor(base_processed1, cv2.COLOR_BGR2RGB)
                from_array_rgb_2 = cv2.cvtColor(base_processed2, cv2.COLOR_BGR2RGB)
                
                # FIXED: Force layout matrices into standard PIL Image objects to prevent truth value array crash
                pil_background1 = Image.fromarray(from_array_rgb)
                pil_background2 = Image.fromarray(from_array_rgb_2)
                
                img_h, img_w = base_processed1.shape[:2]
                
                disp_col1, disp_col2 = st.columns(2)
                
                with disp_col1:
                    st.caption("Original Version (Auto-Highlighted + Manual Editor)")
                    canvas1 = st_canvas(
                        fill_color="rgba(255, 87, 34, 0.2)",
                        stroke_width=stroke_width,
                        stroke_color=full_stroke_color,
                        background_image=pil_background1,
                        height=img_h,
                        width=img_w,
                        drawing_mode=drawing_mode,
                        key=f"c_orig_{i}",
                    )
                
                with disp_col2:
                    st.caption("Revised Version (Auto-Highlighted + Manual Editor)")
                    canvas2 = st_canvas(
                        fill_color="rgba(255, 87, 34, 0.2)",
                        stroke_width=stroke_width,
                        stroke_color=full_stroke_color,
                        background_image=pil_background2,
                        height=img_h,
                        width=img_w,
                        drawing_mode=drawing_mode,
                        key=f"c_rev_{i}",
                    )
                
                # Process combined outputs for downloads
                if canvas1.image_data is not None and canvas2.image_data is not None:
                    out_img1 = base_processed1.copy()
                    out_img2 = base_processed2.copy()
                    
                    draw1 = cv2.cvtColor(canvas1.image_data, cv2.COLOR_RGBA2BGRA)
                    draw2 = cv2.cvtColor(canvas2.image_data, cv2.COLOR_RGBA2BGRA)
                    
                    for c in range(0, 3):
                        out_img1[:, :, c] = out_img1[:, :, c] * (1 - draw1[:, :, 3] / 255.0) + draw1[:, :, c] * (draw1[:, :, 3] / 255.0)
                        out_img2[:, :, c] = out_img2[:, :, c] * (1 - draw2[:, :, 3] / 255.0) + draw2[:, :, c] * (draw2[:, :, 3] / 255.0)
                    
                    h1, w1 = out_img1.shape[:2]
                    h2, w2 = out_img2.shape[:2]
                    if h1 != h2:
                        out_img2 = cv2.resize(out_img2, (int(w2 * h1 / h2), h1))
                    
                    side_by_side = np.hstack((out_img1, out_img2))
                    _, encoded_img = cv2.imencode(".png", side_by_side)
                    report_pages.append(encoded_img.tobytes())
                st.markdown("---")
                
            if report_pages:
                pdf_data = img2pdf.convert(report_pages)
                st.sidebar.subheader("📥 Export Options")
                st.sidebar.download_button(
                    label="Download Complete Report (PDF)",
                    data=pdf_data,
                    file_name="hybrid_comparison_report.pdf",
                    mime="application/pdf"
                )
                st.sidebar.success("Report compilation ready!")
                
        except Exception as e:
            st.error(f"Error executing workspace canvas view: {e}")
else:
    st.info("Upload your document versions to load the hybrid dashboard.")
