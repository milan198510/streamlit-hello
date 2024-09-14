
DOCUMENT_TYPES = [
    "Asset Purchase Agreement", "Collaboration Agreement", "Confidentiality Agreement",
    "Copyright Assignment Agreement", "Copyright License Agreement", "Escrow Agreement",
    "Franchise Agreement", "Guarantee Deed", "Indemnification Agreement",
    "Joint Venture Agreement", "License Agreement", "Loan Agreement",
    "Loan Purchase Agreement", "Investment Agreement", "Share Purchase Agreement",
    "Non-Compete Agreement", "Non-Disclosure Agreement", "Partnership Agreement",
    "Pledge Agreement", "Real Estate Agreement to Sell", "Real Estate Purchase Agreement",
    "Lease Agreement", "Employment Agreement", "Shareholders' Agreement",
    "Services Agreement", "Manufacturing Agreement", "Tolling Agreement",
    "Slump Sale Agreement", "Patent Assignment Agreement", "Technology License Agreement"
]


def extract_text(file_path):
    _, ext = os.path.splitext(file_path.lower())
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        return extract_text_from_docx(file_path)
    elif ext in ['.png', '.jpg', '.jpeg']:
        return extract_text_from_image(file_path)
    else:
        return ""  # Unsupported file type


def extract_text_from_pdf(file_path):
    with open(file_path, 'rb') as file:
        pdf_reader = PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def extract_text_from_docx(file_path):
    doc = Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


def extract_text_from_image(file_path):
    image = Image.open(file_path)
    model = genai.GenerativeModel('gemini-pro-vision')
    response = model.generate_content(["Describe the text content of this image", image])
    return response.text


def categorize_risk(text):
    risk_categories = {
        'High': ['breach', 'termination', 'litigation', 'penalty', 'liability', 'damages'],
        'Medium': ['dispute', 'delay', 'modification', 'confidentiality', 'intellectual property'],
        'Low': ['notice', 'amendment', 'assignment', 'waiver']
    }

    text_lower = text.lower()
    for category, keywords in risk_categories.items():
        if any(keyword in text_lower for keyword in keywords):
            return category
    return 'No Risk'


def highlight_risky_clauses(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    highlighted_sentences = []
    for sentence in sentences:
        risk_level = categorize_risk(sentence)
        if risk_level != 'No Risk':
            highlighted_sentences.append((sentence, risk_level))
    return highlighted_sentences


def analyze_document(text):
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""Analyze the following legal document and provide a structured response:

0. Summary of the document (2-3 sentences)
1. Type of document (choose from the following list): {', '.join(DOCUMENT_TYPES)}
2. Next action items
3. What would constitute a breach
4. Obligations summary
5. Term
6. Termination rights
7. Consequences of termination
8. Is personal information being captured? (Yes/No)
9. Is it a constitutional document, operational document, or financial document?
10. Does it pertain to a listed company? If yes, does it have any price sensitive information?
11. Date-wise summary of key points
12. Identify and list any clauses that might pose risks or require special attention

Here's the document text:

{text[:15000]}  # Limiting to 15000 characters to avoid token limits

Provide your analysis in a structured format, using the numbers above as headers.
"""
    response = model.generate_content(prompt)
    return response.text


def parse_analysis(analysis):
    sections = re.split(r'\n\d+\.\s', analysis)
    parsed = []
    if sections:
        summary = sections[0].strip()
        parsed = [summary] + [section.strip() for section in sections[1:]]

    # Ensure we always have 13 items (0-12)
    parsed = (parsed + [''] * 13)[:13]
    return parsed


def clean_document_type(doc_type):
    # Remove variations of "type of document" and any leading/trailing whitespace
    cleaned = re.sub(r'(?i)type\s+of\s+document:?\s*', '', doc_type)
    cleaned = re.sub(r'^\s*|\s*$', '', cleaned)  # Remove leading/trailing whitespace
    return cleaned


def extract_date(date_summary):
    # Simple date extraction, assuming format like "DD/MM/YYYY" or "DD-MM-YYYY"
    date_pattern = r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b'
    match = re.search(date_pattern, date_summary)
    if match:
        date_str = match.group(0)
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except ValueError:
            try:
                return datetime.strptime(date_str, '%d-%m-%Y')
            except ValueError:
                return None
    return None


def process_folder(folder_path, max_files=5):
    results = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            text = extract_text(file_path)
            if text:
                analysis = analyze_document(text)
                parsed_analysis = parse_analysis(analysis)
                risky_clauses = highlight_risky_clauses(text)
                overall_risk = categorize_risk(text)
                results.append({
                    'File Name': file,
                    'File Path': file_path,
                    'Summary': parsed_analysis[0],
                    'Document Type': parsed_analysis[1],
                    'Next Action Items': parsed_analysis[2],
                    'Breach Conditions': parsed_analysis[3],
                    'Obligations Summary': parsed_analysis[4],
                    'Term': parsed_analysis[5],
                    'Termination Rights': parsed_analysis[6],
                    'Termination Consequences': parsed_analysis[7],
                    'Personal Info Captured': parsed_analysis[8],
                    'Document Category': parsed_analysis[9],
                    'Listed Company Info': parsed_analysis[10],
                    'Date-wise Summary': parsed_analysis[11],
                    'Risky Clauses': parsed_analysis[12],
                    'Highlighted Risky Clauses': risky_clauses,
                    'Overall Risk Level': overall_risk
                })
            if len(results) == max_files:
                break
        if len(results) == max_files:
            break
    return results


def create_dashboard(results):
    df = pd.DataFrame(results)

    # Clean the 'Document Type' column
    df['Document Type'] = df['Document Type'].apply(clean_document_type)

    col1, col2 = st.columns(2)

    with col1:
        # Document Classification Count
        doc_type_count = df['Document Type'].value_counts()
        fig_doc_type = px.bar(
            doc_type_count,
            x=doc_type_count.index,
            y=doc_type_count.values,
            title="Document Classification",
            labels={'y': 'Count', 'x': ''},
            color=doc_type_count.values,
            color_continuous_scale='Viridis'
        )
        fig_doc_type.update_layout(
            xaxis_tickangle=-45,
            xaxis_title="",
            yaxis_title="Count",
            height=400
        )
        st.plotly_chart(fig_doc_type, use_container_width=True)

    with col2:
        # Risk Analysis
        risk_count = df['Overall Risk Level'].value_counts()
        fig_risk = go.Figure(data=[go.Pie(labels=risk_count.index, values=risk_count.values, hole=.3)])
        fig_risk.update_layout(title_text="Overall Risk Distribution")
        st.plotly_chart(fig_risk, use_container_width=True)

    # Execution Date Plot
    df['Execution Date'] = df['Date-wise Summary'].apply(extract_date)
    valid_dates = df[df['Execution Date'].notna()]
    if not valid_dates.empty:
        fig_dates = px.scatter(valid_dates, x='Execution Date', y='Document Type',
                               title="Document Execution Timeline",
                               labels={'Execution Date': 'Date', 'Document Type': 'Classification'},
                               color='Overall Risk Level')
        fig_dates.update_layout(height=400)
        st.plotly_chart(fig_dates, use_container_width=True)
    else:
        st.warning("No valid execution dates found in the documents.")

    # Summary Statistics
    st.subheader("📊 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Documents", len(df))
    col2.metric("Document Classifications", len(doc_type_count))
    col3.metric("Documents with Dates", len(valid_dates))
    col4.metric("High Risk Documents", len(df[df['Overall Risk Level'] == 'High']))

    # Display top risky clauses
    st.subheader("⚠️ Top Risky Clauses")
    all_risky_clauses = [clause for doc in df['Highlighted Risky Clauses'] for clause in doc]
    if all_risky_clauses:
        risky_df = pd.DataFrame(all_risky_clauses, columns=['Clause', 'Risk Level'])
        st.dataframe(risky_df)
    else:
        st.info("No risky clauses identified.")


def display_detailed_results(results):
    for idx, result in enumerate(results, 1):
        with st.expander(f"📄 Document {idx}: {result['File Name']} - Risk Level: {result['Overall Risk Level']}"):
            st.markdown(f"**File Path:** `{result['File Path']}`")
            st.markdown("---")
            st.markdown(f"**Summary:** {result['Summary']}")
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Document Type:** {clean_document_type(result['Document Type'])}")
                st.markdown(f"**Term:** {result['Term']}")
                st.markdown(f"**Personal Info Captured:** {result['Personal Info Captured']}")
            with col2:
                st.markdown(f"**Document Category:** {result['Document Category']}")
                st.markdown(f"**Listed Company Info:** {result['Listed Company Info']}")
            st.markdown("---")
            st.markdown(f"**Next Action Items:** {result['Next Action Items']}")
            st.markdown(f"**Breach Conditions:** {result['Breach Conditions']}")
            st.markdown(f"**Obligations Summary:** {result['Obligations Summary']}")
            st.markdown(f"**Termination Rights:** {result['Termination Rights']}")
            st.markdown(f"**Termination Consequences:** {result['Termination Consequences']}")
            st.markdown(f"**Date-wise Summary:** {result['Date-wise Summary']}")

            st.markdown("---")
            st.markdown("**🚨 Risky Clauses:**")
            for clause, risk_level in result['Highlighted Risky Clauses']:
                st.markdown(f"- **{risk_level} Risk:** {clause}")


def set_custom_theme():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(to right, #f0f8ff, #e6f3ff);
    }
    .stSidebar {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
    .stButton>button {
        color: #ffffff;
        background-color: #4682B4;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #3a6d99;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
    .stPlotlyChart {
        background-color: #ffffff;
        border-radius: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        padding: 10px;
    }
    .streamlit-expanderHeader {
        background-color: #f0f8ff;
        border-radius: 5px;
    }
    /* Style for the input box */
    .stTextInput>div>div>input {
        background-color: #ffffff;
        color: #2c3e50;
        border: 1px solid #4682B4;
        border-radius: 5px;
        padding: 8px 12px;
    }
    .stTextInput>label {
        color: #2c3e50;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)


def initialize_session_state():
    if 'cumulative_documents' not in st.session_state:
        st.session_state.cumulative_documents = []
    if 'test_counter' not in st.session_state:
        st.session_state.test_counter = 0


def main_page():
    st.title("⚖️ Legal Document Analyzer Dashboard")

    # Sidebar for input
    with st.sidebar:
        st.header("📁 Document Input")
        folder_path = st.text_input("Enter the path to the folder containing legal documents:")
        analyze_button = st.button("🔍 Analyze Documents")

    # Main content area
    if analyze_button:
        if folder_path and os.path.isdir(folder_path):
            with st.spinner('Analyzing documents... This may take a few minutes.'):
                results = process_folder(folder_path)

                if results:
                    # Increment test counter
                    st.session_state.test_counter += 1
                    test_number = st.session_state.test_counter

                    # Update cumulative documents list
                    for result in results:
                        st.session_state.cumulative_documents.append({
                            'Test Number': test_number,
                            'File Name': result['File Name'],
                            'File Path': result['File Path'],
                            'Overall Risk Level': result['Overall Risk Level']
                        })

                    # Dashboard
                    st.header(f"📈 Analysis Dashboard - Test #{test_number}")
                    create_dashboard(results)

                    # Detailed Results
                    st.header(f"📄 Detailed Document Analysis - Test #{test_number}")
                    display_detailed_results(results)

                    # Download option
                    df = pd.DataFrame(results)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label=f"📥 Download Analysis for Test #{test_number} as CSV",
                        data=csv,
                        file_name=f"document_analysis_results_test_{test_number}.csv",
                        mime="text/csv",
                    )
                else:
                    st.warning("No supported documents found in the specified folder.")
        else:
            st.sidebar.warning("Please enter a valid folder path.")


def cumulative_list_page():
    st.title("📚 Cumulative Document List")

    if st.session_state.cumulative_documents:
        df = pd.DataFrame(st.session_state.cumulative_documents)
        st.dataframe(df)

        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Cumulative Document List as CSV",
            data=csv,
            file_name="cumulative_document_list.csv",
            mime="text/csv",
        )
    else:
        st.info("No documents have been analyzed yet.")


def main():
    st.set_page_config(page_title="Legal Document Analyzer", page_icon="⚖️", layout="wide")
    set_custom_theme()
    initialize_session_state()

    # Create a sidebar for navigation
    page = st.sidebar.selectbox("Choose a page", ["Analyzer", "Cumulative List"])

    if page == "Analyzer":
        main_page()
    elif page == "Cumulative List":
        cumulative_list_page()


if __name__ == "__main__":
    main()
