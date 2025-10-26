# Standard library imports
import ast
import json
from typing import Dict, List, Any, Optional, Union

# Third-party imports
import mlflow
import pandas as pd
import streamlit as st
from splink import DuckDBAPI, Linker

# Local imports
from components.record_forms import create_record_forms
from components.visualization import display_results
from utils.duckdb_handler import DuckDBHandler
from utils.splink_utils import prediction_row_to_waterfall_format

# Constants
DEFAULT_MODEL_URI = "models:/main.generic_match.nebraska_match/14"
EMPTY_STRING_PLACEHOLDER = ""

# Hardcoded values for specific model URI
HARDCODED_RECORD_VALUES = {
    'left': {
        "salt_key": 1,
        "unique_id": 1,
        "mapped_contact_id": 1,
        "infogroup_id": 1,
        "id": 1,
        "first_lower": "walter",
        "last_lower": "white",
        "nicknames": "['walt']",
        "phone_list": "['1012412351']",
        "email_cleaned": "walterwhite@gmail.com",
        "business_name_list": "['dax']",
        "in_business": "yes",
        "address_standardized_street_no": 121,
        "address_standardized_street": "lincolnrd",
        "address_standardized_pre_directional": "N",
        "address_standardized_post_directional": "E",
        "address_standardized_occupancy_type": "rent",
        "address_standardized_occupancy_identifier": 221,
        "address_standardized_place": "pune",
        "state_cleaned": "maharashtra",
        "address_standardized_state": "maharashtra",
        "address_standardized_zip_code": 411030,
        "address_standardized": "121lincolnpunemaharashtra"
    },
    'right': {
        "salt_key": 2,
        "unique_id": 2,
        "mapped_contact_id": 2,
        "infogroup_id": 2,
        "id": 2,
        "first_lower": "walter",
        "last_lower": "white",
        "nicknames": "['walt']",
        "phone_list": "['1012412351']",
        "email_cleaned": "walterwhite@gmail.com",
        "business_name_list": "['dax']",
        "in_business": "yes",
        "address_standardized_street_no": 121,
        "address_standardized_street": "lincolnrd",
        "address_standardized_pre_directional": "N",
        "address_standardized_post_directional": "E",
        "address_standardized_occupancy_type": "rent",
        "address_standardized_occupancy_identifier": 221,
        "address_standardized_place": "pune",
        "state_cleaned": "maharashtra",
        "address_standardized_state": "maharashtra",
        "address_standardized_zip_code": 411030,
        "address_standardized": "121lincolnpunemaharashtra"
    }
}

# Session state keys
SESSION_KEYS = {
    'LINKER_JSON': 'linker_json',
    'MLFLOW_LINKER': 'mlflow_linker',
    'LEFT_RECORD': 'left_record',
    'RIGHT_RECORD': 'right_record',
    'LAST_RESULT': 'last_result',
    'LAST_LEFT_RECORD': 'last_left_record',
    'LAST_RIGHT_RECORD': 'last_right_record',
    'MODEL_URI': 'model_uri'
}

# Page configuration
st.set_page_config(
    page_title="MatchAI Record Comparison",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
CUSTOM_CSS = """
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
"""

# Apply custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def convert_to_json(data: Any) -> Any:
    """
    Recursively convert data to JSON-serializable format.
    
    Args:
        data: Any data type to convert
        
    Returns:
        JSON-serializable version of the data
    """
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


def fix_list_types(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure empty lists are properly typed as string lists for DuckDB compatibility.
    
    Args:
        record: Dictionary containing record data
        
    Returns:
        Dictionary with fixed list types for DuckDB compatibility
    """
    fixed_record = record.copy()
    for key, value in fixed_record.items():
        if key.endswith('_list') and isinstance(value, list):
            if len(value) == 0:
                # For empty lists, use a list with an empty string to ensure VARCHAR[] type
                # This prevents DuckDB type inference issues
                fixed_record[key] = [EMPTY_STRING_PLACEHOLDER]
            else:
                # Ensure all items in the list are strings
                fixed_record[key] = [str(item) for item in value if item is not None]
    return fixed_record


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure 'additional_columns_to_retain' is converted from a string
    representation of a list into an actual Python list.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Normalized configuration dictionary
        
    Raises:
        ValueError: If additional_columns_to_retain has invalid format
    """
    if isinstance(config.get("additional_columns_to_retain"), str):
        try:
            config["additional_columns_to_retain"] = ast.literal_eval(config["additional_columns_to_retain"])
        except (ValueError, SyntaxError):
            raise ValueError("Invalid format for 'additional_columns_to_retain'")
    return config


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def calculate_predictions(left_record: Dict[str, Any], right_record: Dict[str, Any], linker_json: Dict[str, Any]) -> Any:
    """
    Calculate Splink predictions for two records.
    
    Args:
        left_record: First record to compare
        right_record: Second record to compare
        linker_json: Splink linker configuration
        
    Returns:
        Splink prediction dataframe
        
    Raises:
        Exception: If prediction calculation fails
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

        left_record_fixed['nicknames'] = ['']
        right_record_fixed['nicknames'] = ['']

        # Run prediction
        return linker.inference.compare_two_records(left_record_fixed, right_record_fixed)
        
    except Exception as e:
        st.error(f"Error during prediction calculation: {str(e)}")
        raise

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main() -> None:
    """
    Main application function that orchestrates the Streamlit interface.
    """
    mlflow.set_tracking_uri("databricks")
    mlflow.set_registry_uri("databricks-uc")
    _render_header()
    _render_model_configuration()
    _render_record_comparison_interface()


def _render_header() -> None:
    """Render the application header section."""
    st.markdown("""
    <div class="main-header">
        <h1>MatchAI Record Comparison</h1>
        <p>Compare two records using a trained MatchAI Model</p>
    </div>
    """, unsafe_allow_html=True)


def _render_model_configuration() -> None:
    """Render the model configuration section."""
    with st.container():
        st.markdown("### Model Configuration")
        model_uri = st.text_input('Enter the model URI', value=DEFAULT_MODEL_URI)
        fetch_model_button = st.button("Fetch Model", key="fetch_model_button")
        
        _initialize_session_state()
        
        if fetch_model_button:
            _load_model(model_uri)


def _initialize_session_state() -> None:
    """Initialize session state variables for model data."""
    if SESSION_KEYS['LINKER_JSON'] not in st.session_state:
        st.session_state[SESSION_KEYS['LINKER_JSON']] = None
    if SESSION_KEYS['MLFLOW_LINKER'] not in st.session_state:
        st.session_state[SESSION_KEYS['MLFLOW_LINKER']] = None


def _load_model(model_uri: str) -> None:
    """
    Load MLflow model and update session state.
    
    Args:
        model_uri: URI of the MLflow model to load
    """
    try:
        st.session_state[SESSION_KEYS['MLFLOW_LINKER']] = mlflow.pyfunc.load_model(model_uri)
        st.session_state[SESSION_KEYS['LINKER_JSON']] = convert_to_json(
            st.session_state[SESSION_KEYS['MLFLOW_LINKER']].unwrap_python_model().model_json.copy()
        )
        st.session_state[SESSION_KEYS['MODEL_URI']] = model_uri
        st.success("Model loaded successfully!")
    except Exception as e:
        st.error(f"Failed to load model: {str(e)}")


def _render_record_comparison_interface() -> None:
    """Render the record comparison interface if model is loaded."""
    if st.session_state[SESSION_KEYS['LINKER_JSON']] is not None:
        _render_record_input_forms()
        _render_calculation_section()
        _render_results_display()
    else:
        st.info("Please fetch the model first to access the record comparison interface.")


def _render_record_input_forms() -> None:
    """Render the record input forms section."""
    additional_columns_to_retain = normalize_config(st.session_state[SESSION_KEYS['LINKER_JSON']])['additional_columns_to_retain']
    
    # Check if we should use hardcoded values
    current_model_uri = st.session_state.get(SESSION_KEYS['MODEL_URI'], '')
    use_hardcoded = current_model_uri == DEFAULT_MODEL_URI
    
    if use_hardcoded:
        left_initial_data = HARDCODED_RECORD_VALUES['left']
        right_initial_data = HARDCODED_RECORD_VALUES['right']
    else:
        left_initial_data = {}
        right_initial_data = {}
    
    # Display model info in a nice card
    st.markdown(f"""
    <div class="metric-card">
        <strong>Record Schema:</strong> {', '.join(additional_columns_to_retain)}
    </div>
    """, unsafe_allow_html=True)
        
    # Record input section
    st.markdown("### Record Input")
    st.markdown("Enter the details for both records you want to compare:")
    
    # Create two-column layout for forms
    left_column, right_column = st.columns(2, gap="large")
    
    with left_column:
        st.markdown('<div class="record-section">', unsafe_allow_html=True)
        st.markdown("#### Record A")
        st.session_state[SESSION_KEYS['LEFT_RECORD']] = create_record_forms(
            left_initial_data, 
            key_prefix="left",
            additional_columns_to_retain=additional_columns_to_retain
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with right_column:
        st.markdown('<div class="record-section">', unsafe_allow_html=True)
        st.markdown("#### Record B")
        st.session_state[SESSION_KEYS['RIGHT_RECORD']] = create_record_forms(
            right_initial_data, 
            key_prefix="right",
            additional_columns_to_retain=additional_columns_to_retain
        )
        st.markdown('</div>', unsafe_allow_html=True)


def _render_calculation_section() -> None:
    """Render the calculation button section."""
    st.markdown('<div class="calculate-section">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        calculate_button = st.button("Calculate Match Score", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if calculate_button:
        _run_comparison()


def _run_comparison() -> None:
    """Run the record comparison and handle results."""
    left_record = st.session_state.get(SESSION_KEYS['LEFT_RECORD'])
    right_record = st.session_state.get(SESSION_KEYS['RIGHT_RECORD'])
    
    if left_record and right_record:
        with st.spinner("Analyzing records and calculating match score..."):
            try:
                prediction_result = calculate_predictions(
                    left_record, 
                    right_record, 
                    st.session_state[SESSION_KEYS['LINKER_JSON']]
                )
                
                if prediction_result.as_record_dict()[0]:
                    # Store result in session state for display
                    st.session_state[SESSION_KEYS['LAST_RESULT']] = prediction_result.as_record_dict()[0]
                    st.session_state[SESSION_KEYS['LAST_LEFT_RECORD']] = left_record
                    st.session_state[SESSION_KEYS['LAST_RIGHT_RECORD']] = right_record
                    st.success("Comparison completed successfully!")
                else:
                    st.error("No comparison results returned")
            except Exception as e:
                st.error(f"Failed to run comparison: {str(e)}")


def _render_results_display() -> None:
    """Render the results display section if results are available."""
    required_keys = [SESSION_KEYS['LAST_RESULT'], SESSION_KEYS['LAST_LEFT_RECORD'], SESSION_KEYS['LAST_RIGHT_RECORD']]
    if all(key in st.session_state for key in required_keys):
        additional_columns_to_retain = normalize_config(st.session_state[SESSION_KEYS['LINKER_JSON']])['additional_columns_to_retain']
        st.markdown("---")
        st.markdown("### Comparison Results")
        display_results(
            st.session_state[SESSION_KEYS['LAST_RESULT']], 
            st.session_state[SESSION_KEYS['LAST_LEFT_RECORD']], 
            st.session_state[SESSION_KEYS['LAST_RIGHT_RECORD']],
            additional_columns_to_retain
        )


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()