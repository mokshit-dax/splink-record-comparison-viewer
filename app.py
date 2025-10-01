import streamlit as st
import json
import pandas as pd
from components.record_forms import create_record_forms
from components.visualization import display_results
from utils.duckdb_handler import DuckDBHandler
from utils.splink_utils import prediction_row_to_waterfall_format
import mlflow
import ast
from splink import DuckDBAPI, Linker
 
# Page config
st.set_page_config(
    page_title="Splink Record Comparison",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    .record-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin-bottom: 1rem;
    }
    
    .record-section h3 {
        color: #495057;
        margin-bottom: 1rem;
        font-size: 1.3rem;
    }
    
    .calculate-section {
        text-align: center;
        padding: 2rem 0;
        background: #ffffff;
        border-radius: 10px;
        border: 2px dashed #dee2e6;
        margin: 2rem 0;
    }
    
    .status-success {
        color: #28a745;
        font-weight: 600;
    }
    
    .status-error {
        color: #dc3545;
        font-weight: 600;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

def convert_to_json(data):
  if isinstance(data, dict):
      return {k: convert_to_json(v) for k, v in data.items()}
  elif isinstance(data, list):
      return [convert_to_json(item) for item in data]
  elif isinstance(data, (str, int, float, bool)):
      return data
  elif data is None:
      return None
  else:
      try:
          return str(data)
      except Exception:
          return None

def fix_list_types(record):
    """
    Ensure empty lists are properly typed as string lists for DuckDB compatibility
    """
    fixed_record = record.copy()
    for key, value in fixed_record.items():
        if key.endswith('_list') and isinstance(value, list):
            if len(value) == 0:
                # For empty lists, use a list with an empty string to ensure VARCHAR[] type
                # This prevents DuckDB type inference issues
                fixed_record[key] = [""]
            else:
                # Ensure all items in the list are strings
                fixed_record[key] = [str(item) for item in value if item is not None]
    return fixed_record

def calculate_predictions(left_record, right_record, linker_json):
    """
    Returns a splink prediction dataframe
    """
    try:
        # Fix list types to ensure DuckDB compatibility
        left_record_fixed = fix_list_types(left_record)
        right_record_fixed = fix_list_types(right_record)
        
        # Convert records to dataframes
        left_df = pd.DataFrame([left_record_fixed])
        right_df = pd.DataFrame([right_record_fixed])
        
        # Initialize Splink linker
        linker = Linker(
            input_table_or_tables=[left_df, right_df],
            db_api=DuckDBAPI(),
            settings=linker_json,
        )

        # Run prediction
        return linker.inference.compare_two_records(left_record_fixed, right_record_fixed)
        
    except Exception as e:
        st.error(f"Error during prediction calculation: {str(e)}")
        raise

import ast

def normalize_config(config: dict) -> dict:
    """
    Ensures 'additional_columns_to_retain' is converted from a string
    representation of a list into an actual Python list.
    """
    if isinstance(config.get("additional_columns_to_retain"), str):
        try:
            config["additional_columns_to_retain"] = ast.literal_eval(config["additional_columns_to_retain"])
        except (ValueError, SyntaxError):
            raise ValueError("Invalid format for 'additional_columns_to_retain'")
    return config

def main():
    # Header section
    st.markdown("""
    <div class="main-header">
        <h1>🔗 Splink Record Comparison</h1>
        <p>Compare two records using advanced data linking algorithms</p>
    </div>
    """, unsafe_allow_html=True)

    # Model loading section
    with st.container():
        st.markdown("### 📊 Model Configuration")
        model_uri = st.text_input('Enter the model URI', value="models:/main.generic_match.nebraska_match/14")
        fetch_model = st.button("Fetch Model", key="fetch_model_button")
        
        # Initialize session state for model data
        if 'linker_json' not in st.session_state:
            st.session_state.linker_json = None
        if 'mlflow_linker' not in st.session_state:
            st.session_state.mlflow_linker = None
            
        if fetch_model:
            try:
                st.session_state.mlflow_linker = mlflow.pyfunc.load_model(model_uri)
                st.session_state.linker_json = convert_to_json(st.session_state.mlflow_linker.unwrap_python_model().model_json.copy())
                st.success("Model loaded successfully!")
            except Exception as e:
                st.error(f"Failed to load model: {str(e)}")
        
        if st.session_state.linker_json is not None:
            additional_columns_to_retain = normalize_config(st.session_state.linker_json)['additional_columns_to_retain']
            # Display model info in a nice card
            st.markdown(f"""
            <div class="metric-card">
                <strong>📋 Record Schema:</strong> {', '.join(additional_columns_to_retain)}
            </div>
            """, unsafe_allow_html=True)
            
            # Record input section
            st.markdown("### 📝 Record Input")
            st.markdown("Enter the details for both records you want to compare:")
            
            # Create two-column layout for forms
            col1, col2 = st.columns(2, gap="large")
            
            with col1:
                st.markdown('<div class="record-section">', unsafe_allow_html=True)
                st.markdown("#### 📝 Record A")
                left_record = create_record_forms(
                    {}, 
                    key_prefix="left",
                    additional_columns_to_retain=additional_columns_to_retain
                )
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="record-section">', unsafe_allow_html=True)
                st.markdown("#### 📝 Record B")
                right_record = create_record_forms(
                    {}, 
                    key_prefix="right",
                    additional_columns_to_retain=additional_columns_to_retain
                )
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Calculate button section
            st.markdown('<div class="calculate-section">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                calculate_button = st.button("🔍 Calculate Match Score", type="primary", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Run comparison only when button is clicked
            if left_record and right_record and calculate_button:
                with st.spinner("🔄 Analyzing records and calculating match score..."):
                    try:
                        # left_record['nicknames'] = ['']
                        # right_record['nicknames'] = ['']
                        result = calculate_predictions(left_record, right_record, st.session_state.linker_json)
                        
                        if result.as_record_dict()[0]:
                            # Store result in session state for display
                            st.write(f"Predicted result: {result.as_record_dict()[0]}")
                            st.session_state.last_result = result.as_record_dict()[0]
                            st.session_state.last_left_record = left_record
                            st.session_state.last_right_record = right_record
                            st.success("✅ Comparison completed successfully!")
                        else:
                            st.error("❌ No comparison results returned")
                    except Exception as e:
                        st.error(f"❌ Failed to run comparison: {str(e)}")

            # Display results if available
            if 'last_result' in st.session_state and 'last_left_record' in st.session_state and 'last_right_record' in st.session_state:
                st.markdown("---")
                st.markdown("### 📈 Comparison Results")
                display_results(st.session_state.last_result, st.session_state.last_left_record, st.session_state.last_right_record)
        else:
            st.info("Please fetch the model first to access the record comparison interface.")

if __name__ == "__main__":
    main()