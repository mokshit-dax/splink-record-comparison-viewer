import streamlit as st
import json

def create_record_forms(initial_data, key_prefix):
    """Create clean, minimal input forms for record data"""

    # Basic fields in clean layout
    fields = [
        'first_name', 'surname', 'dob', 'birth_place', 
        'postcode_fake', 'occupation'
    ]
    
    # Field labels
    field_labels = {
        'first_name': 'First name',
        'surname': 'Surname', 
        'dob': 'Date of birth (YYYY-MM-DD)',
        'birth_place': 'Birth place',
        'postcode_fake': 'Postcode',
        'occupation': 'Occupation'
    }

    record = {}
    
    # Clean, minimal form layout
    for field in fields:
        value = st.text_input(
            field_labels[field],
            value=initial_data.get(field, '') or '',
            key=f"{key_prefix}_{field}",
            placeholder=f"Enter {field_labels[field].lower()}"
        )
        record[field] = value if value else None

    # Term Frequency adjustments (collapsed by default)
    tf_fields = [
        'tf_first_name_surname_concat', 'tf_surname', 'tf_first_name',
        'tf_birth_place', 'tf_occupation'
    ]
    
    default_tf_values = {
        'tf_first_name_surname_concat': 0.00018837,
        'tf_surname': 0.0003449,
        'tf_first_name': 0.00018837,
        'tf_birth_place': 0.00504,
        'tf_occupation': 0.038905
    }
    
    with st.expander("> Term frequency adjustments (optional)", expanded=False):
        for tf_field in tf_fields:
            # Initialize session state for this field if not exists
            if f"{key_prefix}_{tf_field}_value" not in st.session_state:
                st.session_state[f"{key_prefix}_{tf_field}_value"] = float(initial_data.get(tf_field, default_tf_values[tf_field]))
            
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.write(f"**{tf_field}**")
            
            with col2:
                value = st.number_input(
                    "",
                    value=st.session_state[f"{key_prefix}_{tf_field}_value"],
                    format="%.8f",
                    key=f"{key_prefix}_{tf_field}"
                )
                # Update the stored value when the widget changes
                if value != st.session_state[f"{key_prefix}_{tf_field}_value"]:
                    st.session_state[f"{key_prefix}_{tf_field}_value"] = value
                record[tf_field] = value
            
            with col3:
                if st.button("×2", key=f"{key_prefix}_{tf_field}_mult"):
                    new_value = st.session_state[f"{key_prefix}_{tf_field}_value"] * 2
                    st.session_state[f"{key_prefix}_{tf_field}_value"] = new_value
                    st.rerun()
            
            with col4:
                if st.button("÷2", key=f"{key_prefix}_{tf_field}_div"):
                    new_value = st.session_state[f"{key_prefix}_{tf_field}_value"] / 2
                    st.session_state[f"{key_prefix}_{tf_field}_value"] = new_value
                    st.rerun()

    # Add computed fields
    record['unique_id'] = f"{key_prefix}_id"
    fn = record.get('first_name') or ''
    sn = record.get('surname') or ''
    record['first_name_surname_concat'] = f"{fn} {sn}".strip() if (fn or sn) else None

    return record