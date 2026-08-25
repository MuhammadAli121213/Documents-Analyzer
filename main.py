import streamlit as st
import numpy as np
import cv2
import pdfplumber
from pdf2image import convert_from_bytes
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import img2pdf

def get_clean_page_image(uploaded_file, page_num):
    """Renders a PDF page to a high-resolution, clear image (300 DPI)."""
    uploaded_file.seek(0)
    images = convert_from_bytes(uploaded_file.read(), dpi=300)
    if page_num < len(images):
        # Return as standard PIL Image for the interactive canvas tool
        return images[page_num]
    return None

st.set_page_config(page_title="Interactive PDF Highlights Editor", layout="wide")
st.title("✍️ Interactive Document Comparison & Manual Highlighter")
st.write("Review your document structures side-by-side. Use the drawing controls to manually highlight differences.")

# Setup controls in the sidebar tool panel
st.sidebar.subheader("🖌️ Highlight Controls")
drawing_mode = st.sidebar.selectbox("Tool:", ("freedraw", "rect", "transform"))
stroke_width = st.sidebar.slider("Brush Size / Thickness:", 1, 50, 20)
stroke_color = st.sidebar.color_picker("Highlight Color:", "#FFEB3B")
# Add a translucent opacity alpha to the hex code so text remains perfectly legible underneath markings
alpha_hex = "80"  # 50% transparency layer
full_stroke_color = f"{stroke_color}{alpha_hex}"

col_up1, col_up2 = st.columns(2)
with col_up1:
    file1 = st.file_uploader("Upload Original PDF", type=["pdf"])
with col_up2:
    file2 = st.file_uploader("Upload Revised PDF", type=["pdf"])

if file1 and file2:
    try:
        with pdfplumber.open(file1) as p1, pdfplumber.open(file2) as p2:
            max_pages = min(len(p1.pages), len(p2.pages))
        
        report_pages = []
        
        for i in range(max_pages):
            st.markdown(f"### 📄 Page {i + 1}")
            
            img1_pil = get_clean_page_image(file1, i)
            img2_pil = get_clean_page_image(file2, i)
            
            if img1_pil is None or img2_pil is None:
                continue
                
            disp_col1, disp_col2 = st.columns(2)
            
            # Interactive Canvas for the Original Document (Left)
            with disp_col1:
                st.caption("Original Version (Draw / Highlight here)")
                canvas_original = st_canvas(
                    fill_color="rgba(255, 235, 59, 0.3)",  # semi-transparent fill for box tools
                    stroke_width=stroke_width,
                    stroke_color=full_stroke_color,
                    background_image=img1_pil,
                    update_streamlit=True,
                    height=img1_pil.height,
                    width=img1_pil.width,
                    drawing_mode=drawing_mode,
                    key=f"canvas_orig_{i}",
                )
            
            # Interactive Canvas for the Revised Document (Right)
            with disp_col2:
                st.caption("Revised Version (Draw / Highlight here)")
                canvas_revised = st_canvas(
                    fill_color="rgba(255, 235, 59, 0.3)",
                    stroke_width=stroke_width,
                    stroke_color=full_stroke_color,
                    background_image=img2_pil,
                    update_streamlit=True,
                    height=img2_pil.height,
                    width=img2_pil.width,
                    drawing_mode=drawing_mode,
                    key=f"canvas_rev_{i}",
                )
            
            # Flatten background sheets and manually drawn vectors together to build export data
            if canvas_original.image_data is not None and canvas_revised.image_data is not None:
                # Convert canvas layer modifications to OpenCV arrays
                orig_bg = cv2.cvtColor(np.array(img1_pil), cv2.COLOR_RGB2BGR)
                rev_bg = cv2.cvtColor(np.array(img2_pil), cv2.COLOR_RGB2BGR)
                
                # Extract drawn lines
                orig_draw = cv2.cvtColor(canvas_original.image_data, cv2.COLOR_RGBA2BGRA)
                rev_draw = cv2.cvtColor(canvas_revised.image_data, cv2.COLOR_RGBA2BGRA)
                
                # Overlay manually drawn markings on top of the original text templates
                for c in range(0, 3):
                    orig_bg[:, :, c] = orig_bg[:, :, c] * (1 - orig_draw[:, :, 3] / 255.0) + orig_draw[:, :, c] * (orig_draw[:, :, 3] / 255.0)
                    rev_bg[:, :, c] = rev_bg[:, :, c] * (1 - rev_draw[:, :, 3] / 255.0) + rev_draw[:, :, c] * (rev_draw[:, :, 3] / 255.0)
                
                # Normalize sheet height differentials safely prior to final export rendering
                h1, w1 = orig_bg.shape[:2]
                h2, w2 = rev_bg.shape[:2]
                if h1 != h2:
                    new_w2 = int(w2 * h1 / h2)
                    rev_bg_resized = cv2.resize(rev_bg, (new_w2, h1))
                else:
                    rev_bg_resized = rev_bg
                
                side_by_side_canvas = np.hstack((orig_bg, rev_bg_resized))
                _, encoded_img = cv2.imencode(".png", side_by_side_canvas)
                report_pages.append(encoded_img.tobytes())
                
            st.markdown("---")
            
        # Output interactive saved data download actions
        if report_pages:
            pdf_data = img2pdf.convert(report_pages)
            st.sidebar.subheader("📥 Export Options")
            st.sidebar.download_button(
                label="Download Edited Report (PDF)",
                data=pdf_data,
                file_name="manual_highlight_report.pdf",
                mime="application/pdf"
            )
            st.sidebar.success("Export compilation prepared!")
            
    except Exception as e:
        st.error(f"Error initializing workspace framework canvas: {e}")
else:
    st.info("Upload your document sets to enable custom visual editing tools.")
