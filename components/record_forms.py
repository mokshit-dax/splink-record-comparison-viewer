import streamlit as st
import json
import ast

def detect_field_type(value):
    """Detect the type of a field value"""
    if value is None or value == '':
        return 'string'
    if isinstance(value, list):
        return 'list'
    if isinstance(value, (int, float)):
        return 'number'
    if isinstance(value, bool):
        return 'boolean'
    return 'string'

def format_value_for_input(value):
    """Format a value for display in text input"""
    if value is None or value == '':
        return ''
    if isinstance(value, list):
        return ', '.join(str(item) for item in value)
    return str(value)

def parse_input_value(input_str):
    """
    Dynamically parse input string to detect its type:
    - Lists: ["item1", "item2"] or comma-separated values
    - Numbers: integers or floats
    - Booleans: true/false
    - Strings: everything else
    """
    if not input_str or input_str.strip() == '':
        return ''
    
    input_str = input_str.strip()
    
    # Try to detect if it's a JSON list (e.g., ["test", "test2"])
    if input_str.startswith('[') and input_str.endswith(']'):
        try:
            parsed = ast.literal_eval(input_str)
            if isinstance(parsed, list):
                return parsed
        except (ValueError, SyntaxError):
            pass
    
    # Check if it contains commas (potential list)
    if ',' in input_str:
        # Parse as comma-separated list
        return [item.strip() for item in input_str.split(',') if item.strip()]
    
    # Try to parse as number (float or int)
    try:
        # Check if it's a float
        if '.' in input_str:
            return float(input_str)
        else:
            # Try integer first
            return int(input_str)
    except ValueError:
        pass
    
    # Try to parse as boolean
    if input_str.lower() in ('true', 'false'):
        return input_str.lower() == 'true'
    
    # Default to string
    return input_str

def create_record_forms(initial_data, key_prefix, additional_columns_to_retain):
    """Create clean, minimal input forms for record data"""

    # additional_columns_to_retain is required
    if not additional_columns_to_retain:
        raise ValueError("additional_columns_to_retain parameter is required")

    fields = additional_columns_to_retain
    record = {}
    
    # Add custom CSS for form styling
    st.markdown("""
    <style>
        .form-field {
            margin-bottom: 1rem;
        }
        
        .form-field label {
            font-weight: 600;
            color: #495057;
            margin-bottom: 0.5rem;
            display: block;
        }
        
        .form-field .stTextInput > div > div > input {
            border-radius: 8px;
            border: 2px solid #e9ecef;
            padding: 0.75rem;
            font-size: 14px;
            transition: border-color 0.2s ease;
        }
        
        .form-field .stTextInput > div > div > input:focus {
            border-color: #007bff;
            box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
        }
        
        .field-help {
            font-size: 0.85rem;
            color: #6c757d;
            margin-top: 0.25rem;
            font-style: italic;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Clean, minimal form layout
    for field in fields:
        with st.container():
            st.markdown('<div class="form-field">', unsafe_allow_html=True)
            
            # Get initial value and detect its type
            initial_value = initial_data.get(field, '')
            field_type = detect_field_type(initial_value)
            
            # Display field label
            field_display = field.replace("_", " ").title()
            st.markdown(f'<label for="{key_prefix}_{field}">**{field_display}**</label>', unsafe_allow_html=True)
            
            # Add help text based on detected type
            if field_type == 'list':
                st.markdown('<div class="field-help">List (comma-separated or ["item1", "item2"])</div>', unsafe_allow_html=True)
                placeholder = "e.g., item1, item2 or [\"item1\", \"item2\"]"
            elif field_type == 'number':
                st.markdown('<div class="field-help">Number</div>', unsafe_allow_html=True)
                placeholder = "e.g., 12.45"
            else:
                st.markdown('<div class="field-help">Text</div>', unsafe_allow_html=True)
                placeholder = f"Enter {field_display.lower()}"
            
            # Format value for display
            display_value = format_value_for_input(initial_value)
            
            # Create text input
            user_input = st.text_input(
                field,
                value=display_value,
                key=f"{key_prefix}_{field}",
                placeholder=placeholder,
                label_visibility="collapsed"
            )
            
            # Parse the input dynamically
            record[field] = parse_input_value(user_input)
            
            st.markdown('</div>', unsafe_allow_html=True)

    return record