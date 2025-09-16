import math
from difflib import SequenceMatcher

def log2(x):
    return math.log2(x) if x > 0 else 0

def bayes_factor_to_prob(b):
    return b / (b + 1)

def prob_to_bayes_factor(p):
    return p / (1 - p)

def derive_prior_match_weight(match_data):
    """Derive the adjusted prior match weight using bayes factors"""
    product = 1
    for key, value in match_data.items():
        if key.startswith('bf_') and value is not None:
            product *= value
    
    log_product = log2(product)
    return match_data.get('match_weight', 0) - log_product

def prediction_row_to_waterfall_format(match_data):
    """Convert prediction row to waterfall chart format"""
    output_data = []
    bar_sort_order = 0
    
    prior_match_weight = derive_prior_match_weight(match_data)
    
    # Prior row
    output_data.append({
        'column_name': 'Prior',
        'label_for_charts': 'Starting match weight (prior)',
        'log2_bayes_factor': prior_match_weight,
        'bayes_factor': 2 ** prior_match_weight,
        'comparison_vector_value': None,
        'term_frequency_adjustment': None,
        'bar_sort_order': bar_sort_order
    })
    bar_sort_order += 1
    
    # Process each gamma value
    gamma_keys = [key for key in match_data.keys() if key.startswith('gamma_')]
    gamma_keys.sort()
    
    for key in gamma_keys:
        col_name = key[6:]  # Remove 'gamma_' prefix
        bf_key = f'bf_{col_name}'
        tf_adj_key = f'bf_tf_adj_{col_name}'
        
        bayes_factor_standard = match_data.get(bf_key, 1)
        bayes_factor_tf = match_data.get(tf_adj_key, 1)
        
        # Standard bayes factor
        output_data.append({
            'column_name': col_name,
            'label_for_charts': f'Gamma value for {col_name}',
            'log2_bayes_factor': log2(bayes_factor_standard),
            'bayes_factor': bayes_factor_standard,
            'comparison_vector_value': match_data[key],
            'term_frequency_adjustment': False,
            'bar_sort_order': bar_sort_order
        })
        bar_sort_order += 1
        
        # TF adjustment
        output_data.append({
            'column_name': f'tf adj on {col_name}',
            'label_for_charts': f'Gamma value for {col_name}',
            'log2_bayes_factor': log2(bayes_factor_tf),
            'bayes_factor': bayes_factor_tf,
            'comparison_vector_value': match_data[key],
            'term_frequency_adjustment': True,
            'bar_sort_order': bar_sort_order
        })
        bar_sort_order += 1
    
    # Final row
    final_score = match_data.get('match_weight', 0)
    output_data.append({
        'column_name': 'Final score',
        'label_for_charts': 'Final score',
        'log2_bayes_factor': final_score,
        'bayes_factor': 2 ** final_score,
        'comparison_vector_value': None,
        'term_frequency_adjustment': None,
        'bar_sort_order': bar_sort_order
    })
    
    return output_data

def generate_diff_html(left_val, right_val):
    """Generate HTML diff between two values"""
    if left_val == right_val:
        return str(left_val)
    
    # Simple diff using SequenceMatcher
    matcher = SequenceMatcher(None, str(left_val), str(right_val))
    diff_html = ""
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            diff_html += str(left_val)[i1:i2]
        elif tag == 'delete':
            diff_html += f'<span style="background-color: #ffcccc; text-decoration: line-through;">{str(left_val)[i1:i2]}</span>'
        elif tag == 'insert':
            diff_html += f'<span style="background-color: #ccffcc;">{str(right_val)[j1:j2]}</span>'
        elif tag == 'replace':
            diff_html += f'<span style="background-color: #ffcccc; text-decoration: line-through;">{str(left_val)[i1:i2]}</span>'
            diff_html += f'<span style="background-color: #ccffcc;">{str(right_val)[j1:j2]}</span>'
    
    return diff_html