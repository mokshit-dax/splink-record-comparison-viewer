import streamlit as st
import json
import pandas as pd
from components.record_forms import create_record_forms
from components.visualization import display_results
from utils.duckdb_handler import DuckDBHandler
from utils.splink_utils import prediction_row_to_waterfall_format

# Page config
st.set_page_config(
    page_title="Splink Record Comparison",
    page_icon="🔗",
    layout="wide"
)

def main():
    st.title("Splink Record Comparison Tool")
    st.markdown("Compare two records using a Splink data linking model")
    
    # Load example data
    with open('data/record_data.json', 'r') as f:
        record_data = json.load(f)
    
    # Initialize session state
    if 'record_index' not in st.session_state:
        st.session_state.record_index = 0

    # Navigation controls
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Previous", disabled=st.session_state.record_index == 0):
            st.session_state.record_index -= 1
            st.rerun()
    
    with col2:
        st.write(f"Record {st.session_state.record_index + 1} of {len(record_data)}")
    
    with col3:
        if st.button("Next ➡️", disabled=st.session_state.record_index >= len(record_data) - 1):
            st.session_state.record_index += 1
            st.rerun()
    
    # Get current record pair
    current_record = record_data[st.session_state.record_index]
    
    # Create two-column layout for forms
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 Record Left")
        left_record = create_record_forms(
            current_record['record_left'], 
            key_prefix="left"
        )
    
    with col2:
        st.subheader("📝 Record Right")
        right_record = create_record_forms(
            current_record['record_right'], 
            key_prefix="right"
        )
    
    # Add calculate button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        calculate_button = st.button("🔍 Calculate Match", type="primary", use_container_width=True)
    
    # Run comparison only when button is clicked
    if left_record and right_record and calculate_button:
        with st.spinner("Running Splink comparison..."):
            try:
                # Initialize DuckDB handler
                db_handler = DuckDBHandler()
                
                # Run the comparison
                result = db_handler.compare_records(left_record, right_record)
                
                if result:
                    # Store result in session state for display
                    st.session_state.last_result = result
                    st.session_state.last_left_record = left_record
                    st.session_state.last_right_record = right_record
                else:
                    st.error("No comparison results returned")
            except Exception as e:
                st.error(f"Failed to run comparison: {str(e)}")
    
    # Display results if available
    if 'last_result' in st.session_state and 'last_left_record' in st.session_state and 'last_right_record' in st.session_state:
        display_results(st.session_state.last_result, st.session_state.last_left_record, st.session_state.last_right_record)

if __name__ == "__main__":
    main()