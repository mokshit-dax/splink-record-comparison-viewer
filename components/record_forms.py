import streamlit as st
import json

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
            
            if field.endswith('_list'):
                # Handle array/list fields
                st.markdown(f'<label for="{key_prefix}_{field}">**{field.replace("_", " ").title()}**</label>', unsafe_allow_html=True)
                st.markdown('<div class="field-help">Enter comma-separated values</div>', unsafe_allow_html=True)
                
                value = st.text_input(
                    f"Enter {field} as comma-separated values",
                    value=initial_data.get(field, '') or '',
                    key=f"{key_prefix}_{field}",
                    placeholder=f"e.g., value1, value2, value3",
                    label_visibility="collapsed"
                )
                # Convert comma-separated string to list
                if value and value.strip():
                    record[field] = [item.strip() for item in value.split(',') if item.strip()]
                else:
                    record[field] = []
            else:
                # Handle regular string fields
                field_display = field.replace("_", " ").title()
                st.markdown(f'<label for="{key_prefix}_{field}">**{field_display}**</label>', unsafe_allow_html=True)
                
                value = st.text_input(
                    field,
                    value=initial_data.get(field, '') or '',
                    key=f"{key_prefix}_{field}",
                    placeholder=f"Enter {field_display.lower()}",
                    label_visibility="collapsed"
                )
                # Ensure all non-list fields are strings (not None for empty values)
                record[field] = str(value) if value else ""
            
            st.markdown('</div>', unsafe_allow_html=True)

    return record