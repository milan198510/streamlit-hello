import streamlit as st
import pandas as pd
import io
from difflib import SequenceMatcher

def similarity_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()

def find_best_match(description, candidates, threshold=0.6):
    """Find the best match for a description among candidates."""
    best_match = None
    best_score = 0
    for candidate in candidates:
        score = similarity_ratio(description.lower(), candidate.lower())
        if score > best_score and score >= threshold:
            best_score = score
            best_match = candidate
    return best_match, best_score

def create_mapping(site1_data, site2_data, site1_col, site2_col):
    """Create a mapping between product descriptions."""
    mappings = []
    site2_descriptions = site2_data[site2_col].tolist()

    for _, row in site1_data.iterrows():
        site1_desc = row[site1_col]
        best_match, score = find_best_match(site1_desc, site2_descriptions)
        mappings.append({
            'site1_description': site1_desc,
            'site2_description': best_match,
            'similarity_score': score
        })

    return pd.DataFrame(mappings)

st.title("Product Description Mapping Tool")

# File upload
site1_file = st.file_uploader("Upload CSV file for Site 1", type="csv")
site2_file = st.file_uploader("Upload CSV file for Site 2", type="csv")

if site1_file and site2_file:
    site1_data = pd.read_csv(site1_file)
    site2_data = pd.read_csv(site2_file)

    # Column selection
    st.subheader("Select columns for mapping")
    site1_col = st.selectbox("Select description column for Site 1", site1_data.columns)
    site2_col = st.selectbox("Select description column for Site 2", site2_data.columns)

    if st.button("Map Products"):
        with st.spinner("Mapping products..."):
            result_df = create_mapping(site1_data, site2_data, site1_col, site2_col)

        st.success("Mapping complete!")
        st.subheader("Mapping Results")
        st.dataframe(result_df)

        # Download button for results
        csv = result_df.to_csv(index=False)
        st.download_button(
            label="Download mapping results as CSV",
            data=csv,
            file_name="product_mapping_results.csv",
            mime="text/csv"
        )
else:
    st.info("Please upload both CSV files to proceed.")

st.sidebar.header("Instructions")
st.sidebar.info(
    "1. Upload CSV files for both sites.\n"
    "2. Select the columns containing product descriptions.\n"
    "3. Click 'Map Products' to generate the mapping.\n"
    "4. Review the results and download if needed."
)
