import streamlit as st
import fitz  # PyMuPDF
import difflib
import re
import io
from datetime import datetime


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="PDF Document Comparison & Editor",
    page_icon="📄",
    layout="wide"
)


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_pdf_text(pdf_bytes):
    """Extract all text from a PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    pages = []

    for page_number, page in enumerate(doc):
        text = page.get_text("text")

        pages.append({
            "page": page_number + 1,
            "text": text
        })

    doc.close()

    return pages


def get_full_text(pdf_bytes):
    """Combine all PDF pages into one text string."""
    pages = extract_pdf_text(pdf_bytes)

    return "\n\n".join(
        f"--- PAGE {p['page']} ---\n{p['text']}"
        for p in pages
    )


# ============================================================
# TEXT COMPARISON
# ============================================================

def compare_text(text1, text2):
    """
    Compare two documents using word-level comparison.
    """

    words1 = re.findall(r"\S+", text1)
    words2 = re.findall(r"\S+", text2)

    matcher = difflib.SequenceMatcher(None, words1, words2)

    differences = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == "equal":
            continue

        differences.append({
            "type": tag,
            "old_text": " ".join(words1[i1:i2]),
            "new_text": " ".join(words2[j1:j2])
        })

    return differences


def generate_diff_html(text1, text2):
    """
    Create HTML showing differences between documents.
    """

    words1 = re.findall(r"\S+", text1)
    words2 = re.findall(r"\S+", text2)

    matcher = difflib.SequenceMatcher(None, words1, words2)

    html_parts = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == "equal":

            html_parts.append(
                " ".join(words1[i1:i2])
            )

        elif tag == "delete":

            html_parts.append(
                f'<span style="background-color:#ffcccc;'
                f'text-decoration:line-through;">'
                f'{" ".join(words1[i1:i2])}'
                f'</span>'
            )

        elif tag == "insert":

            html_parts.append(
                f'<span style="background-color:#ccffcc;">'
                f'{" ".join(words2[j1:j2])}'
                f'</span>'
            )

        elif tag == "replace":

            html_parts.append(
                f'<span style="background-color:#ffcccc;'
                f'text-decoration:line-through;">'
                f'{" ".join(words1[i1:i2])}'
                f'</span> '
                f'<span style="background-color:#ccffcc;">'
                f'{" ".join(words2[j1:j2])}'
                f'</span>'
            )

    return " ".join(html_parts)


# ============================================================
# FIND TEXT LOCATIONS IN PDF
# ============================================================

def find_text_in_pdf(pdf_bytes, search_text):
    """
    Find exact text inside a PDF and return its page and coordinates.
    """

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    results = []

    for page_index, page in enumerate(doc):

        rectangles = page.search_for(search_text)

        for rect in rectangles:

            results.append({
                "page": page_index + 1,
                "rect": rect,
                "page_index": page_index
            })

    doc.close()

    return results


# ============================================================
# REPLACE TEXT IN PDF
# ============================================================

def replace_text_in_pdf(
    pdf_bytes,
    search_text,
    replacement_text,
    page_number=None
):
    """
    Replace text in a PDF using redaction + inserted text.

    This preserves the page but may require manual adjustment
    when replacement text is longer than the original.
    """

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    replacement_count = 0

    for page_index, page in enumerate(doc):

        if page_number is not None:
            if page_index + 1 != page_number:
                continue

        matches = page.search_for(search_text)

        for rect in matches:

            # Redact original text
            page.add_redact_annot(
                rect,
                fill=(1, 1, 1)
            )

            replacement_count += 1

        if matches:

            page.apply_redactions()

            for rect in matches:

                # Slightly reduce the rectangle height
                insert_rect = fitz.Rect(
                    rect.x0,
                    rect.y0,
                    rect.x1,
                    rect.y1 + 2
                )

                page.insert_textbox(
                    insert_rect,
                    replacement_text,
                    fontsize=max(
                        6,
                        min(12, rect.height * 0.75)
                    ),
                    fontname="helv",
                    color=(0, 0, 0),
                    align=0
                )

    output = io.BytesIO()

    doc.save(
        output,
        garbage=4,
        deflate=True
    )

    doc.close()

    return output.getvalue(), replacement_count


# ============================================================
# DOWNLOAD COMPARISON REPORT
# ============================================================

def create_comparison_report(differences):

    report = []

    report.append(
        "PDF DOCUMENT COMPARISON REPORT"
    )

    report.append(
        "=" * 60
    )

    report.append(
        f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    )

    report.append("")

    if not differences:

        report.append(
            "No text differences detected."
        )

    else:

        report.append(
            f"Total differences: {len(differences)}"
        )

        report.append("")

        for number, diff in enumerate(
            differences,
            start=1
        ):

            report.append(
                f"Difference {number}"
            )

            report.append(
                f"Type: {diff['type']}"
            )

            report.append(
                f"Original: {diff['old_text']}"
            )

            report.append(
                f"New: {diff['new_text']}"
            )

            report.append("-" * 60)

    return "\n".join(report)


# ============================================================
# SESSION STATE
# ============================================================

if "edited_pdf" not in st.session_state:
    st.session_state.edited_pdf = None

if "replacement_count" not in st.session_state:
    st.session_state.replacement_count = 0


# ============================================================
# HEADER
# ============================================================

st.title("📄 PDF Document Comparison & Editor")

st.markdown(
    """
    **Compare contracts, agreements, letters and other PDF documents,
    identify differences, and make controlled text replacements.**
    """
)


# ============================================================
# SIDEBAR
# ============================================================

menu = st.sidebar.radio(
    "System",
    [
        "🔍 Compare Documents",
        "✏️ Edit PDF",
        "📋 Document Information"
    ]
)


# ============================================================
# PAGE 1 — COMPARE DOCUMENTS
# ============================================================

if menu == "🔍 Compare Documents":

    st.header("🔍 Compare Two Documents")

    col1, col2 = st.columns(2)

    with col1:

        pdf1 = st.file_uploader(
            "Upload Original Document",
            type=["pdf"],
            key="pdf_original"
        )

    with col2:

        pdf2 = st.file_uploader(
            "Upload Revised Document",
            type=["pdf"],
            key="pdf_revised"
        )

    if pdf1 and pdf2:

        st.success(
            "Both documents uploaded successfully."
        )

        compare_button = st.button(
            "🔎 Compare Documents",
            type="primary"
        )

        if compare_button:

            with st.spinner(
                "Reading and comparing documents..."
            ):

                original_bytes = pdf1.getvalue()
                revised_bytes = pdf2.getvalue()

                original_text = get_full_text(
                    original_bytes
                )

                revised_text = get_full_text(
                    revised_bytes
                )

                differences = compare_text(
                    original_text,
                    revised_text
                )

                st.session_state["original_text"] = original_text
                st.session_state["revised_text"] = revised_text
                st.session_state["differences"] = differences

        if "differences" in st.session_state:

            differences = st.session_state[
                "differences"
            ]

            st.divider()

            # ==================================================
            # SUMMARY
            # ==================================================

            st.subheader("📊 Comparison Summary")

            added = len([
                d for d in differences
                if d["type"] == "insert"
            ])

            removed = len([
                d for d in differences
                if d["type"] == "delete"
            ])

            changed = len([
                d for d in differences
                if d["type"] == "replace"
            ])

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Total Differences",
                len(differences)
            )

            c2.metric(
                "Added",
                added
            )

            c3.metric(
                "Removed",
                removed
            )

            c4.metric(
                "Changed",
                changed
            )

            # ==================================================
            # DIFFERENCE TABLE
            # ==================================================

            st.subheader(
                "📋 Detailed Differences"
            )

            if differences:

                for number, diff in enumerate(
                    differences,
                    start=1
                ):

                    if diff["type"] == "insert":

                        st.success(
                            f"### Difference {number} — Added"
                        )

                        st.write(
                            diff["new_text"]
                        )

                    elif diff["type"] == "delete":

                        st.error(
                            f"### Difference {number} — Removed"
                        )

                        st.write(
                            diff["old_text"]
                        )

                    else:

                        st.warning(
                            f"### Difference {number} — Changed"
                        )

                        left, right = st.columns(2)

                        with left:

                            st.markdown(
                                "**Original**"
                            )

                            st.error(
                                diff["old_text"]
                            )

                        with right:

                            st.markdown(
                                "**Revised**"
                            )

                            st.success(
                                diff["new_text"]
                            )

                    st.divider()

            else:

                st.success(
                    "✅ No differences detected."
                )

            # ==================================================
            # VISUAL DIFF
            # ==================================================

            st.subheader(
                "🖍️ Visual Text Comparison"
            )

            diff_html = generate_diff_html(
                st.session_state["original_text"],
                st.session_state["revised_text"]
            )

            st.markdown(
                f"""
                <div style="
                    padding:20px;
                    border:1px solid #cccccc;
                    border-radius:8px;
                    line-height:1.8;
                    font-size:16px;
                    max-height:600px;
                    overflow-y:auto;
                ">
                {diff_html}
                </div>
                """,
                unsafe_allow_html=True
            )

            # ==================================================
            # DOWNLOAD REPORT
            # ==================================================

            report = create_comparison_report(
                differences
            )

            st.download_button(
                "📥 Download Comparison Report",
                data=report,
                file_name="document_comparison_report.txt",
                mime="text/plain"
            )


# ============================================================
# PAGE 2 — PDF EDITOR
# ============================================================

elif menu == "✏️ Edit PDF":

    st.header("✏️ Manual PDF Text Editor")

    st.info(
        """
        Upload a PDF, search for existing text, and replace it.
        The application redacts the original text and places the
        replacement text in the same area.
        """
    )

    editor_pdf = st.file_uploader(
        "Upload PDF to Edit",
        type=["pdf"],
        key="editor_pdf"
    )

    if editor_pdf:

        pdf_bytes = editor_pdf.getvalue()

        doc = fitz.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        total_pages = len(doc)

        doc.close()

        st.success(
            f"PDF loaded successfully — {total_pages} pages."
        )

        page_number = st.number_input(
            "Page Number",
            min_value=1,
            max_value=total_pages,
            value=1
        )

        search_text = st.text_input(
            "Text to Find",
            placeholder="Example: 31 December 2026"
        )

        replacement_text = st.text_input(
            "Replace With",
            placeholder="Example: 31 December 2027"
        )

        if search_text:

            matches = find_text_in_pdf(
                pdf_bytes,
                search_text
            )

            if matches:

                st.success(
                    f"Found {len(matches)} occurrence(s)."
                )

                pages_found = sorted(
                    set(
                        m["page"]
                        for m in matches
                    )
                )

                st.write(
                    "Found on page(s):",
                    pages_found
                )

            else:

                st.warning(
                    "Text was not found in the PDF."
                )

        if st.button(
            "✏️ Replace Text",
            type="primary"
        ):

            if not search_text.strip():

                st.error(
                    "Please enter the text to find."
                )

            elif not replacement_text.strip():

                st.error(
                    "Please enter replacement text."
                )

            else:

                with st.spinner(
                    "Editing PDF..."
                ):

                    edited_pdf, count = (
                        replace_text_in_pdf(
                            pdf_bytes,
                            search_text,
                            replacement_text,
                            page_number
                        )
                    )

                if count > 0:

                    st.session_state.edited_pdf = (
                        edited_pdf
                    )

                    st.session_state.replacement_count = (
                        count
                    )

                    st.success(
                        f"Successfully replaced {count} occurrence(s)."
                    )

                else:

                    st.error(
                        "No matching text was found on this page."
                    )

        # ======================================================
        # DOWNLOAD EDITED PDF
        # ======================================================

        if st.session_state.edited_pdf:

            st.divider()

            st.subheader(
                "📥 Revised PDF"
            )

            st.download_button(
                label="📥 Download Edited PDF",
                data=st.session_state.edited_pdf,
                file_name="revised_document.pdf",
                mime="application/pdf"
            )


# ============================================================
# PAGE 3 — DOCUMENT INFORMATION
# ============================================================

elif menu == "📋 Document Information":

    st.header("📋 Document Information")

    st.markdown(
        """
        ### Supported Functions

        **Document Comparison**
        - Compare two PDF documents
        - Detect additions
        - Detect removals
        - Detect changed text
        - Display comparison summary
        - Generate comparison report

        **PDF Editing**
        - Search text inside PDF
        - Find occurrences
        - Select page
        - Replace text
        - Download revised PDF

        ### Recommended Use

        This system can be used for:

        - Contract agreements
        - Subcontract agreements
        - Amendments
        - Service agreements
        - Supplier agreements
        - NDA documents
        - Policies
        - Letters
        - Commercial documents
        """
    )

    st.warning(
        """
        Scanned/image-only PDFs require OCR before text comparison
        or text replacement will work.
        """
    )
