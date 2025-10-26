import streamlit as st
import altair as alt
import pandas as pd
import json
from utils.splink_utils import prediction_row_to_waterfall_format, bayes_factor_to_prob, generate_diff_html

def display_results(result, left_record, right_record, additional_columns_to_retain):
    """Display comparison results with waterfall chart and table"""
    
    # Create waterfall chart first to get the recalculated final score (without TF adjustments)
    waterfall_data = prediction_row_to_waterfall_format(result)
    waterfall_df = pd.DataFrame(waterfall_data)
    
    # Extract the recalculated final score from waterfall data (without TF adjustments)
    final_score_row = waterfall_df[waterfall_df['column_name'] == 'Final score'].iloc[0]
    match_weight = final_score_row['log2_bayes_factor']
    bayes_factor = final_score_row['bayes_factor']
    match_probability = bayes_factor_to_prob(bayes_factor)
    error_probability = 1 - match_probability
    
    # Display results header with metrics
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 15px; margin-bottom: 2rem; text-align: center;">
        <h2 style="color: white; margin: 0 0 1rem 0; font-size: 2rem;">Match Analysis Results</h2>
        <div style="display: flex; justify-content: center; gap: 3rem; flex-wrap: wrap;">
            <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px; min-width: 200px;">
                <div style="color: #FFD700; font-size: 1.8rem; font-weight: bold;">Match Weight</div>
                <div style="color: white; font-size: 2.5rem; font-weight: bold;">{:.4f}</div>
            </div>
            <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px; min-width: 200px;">
                <div style="color: #90EE90; font-size: 1.8rem; font-weight: bold;">Match Probability</div>
                <div style="color: white; font-size: 2.5rem; font-weight: bold;">{:.2%}</div>
            </div>
        </div>
    </div>
    """.format(match_weight, match_probability), unsafe_allow_html=True)
    
    # Create the waterfall chart using Altair with full width
    chart = create_waterfall_chart(waterfall_df, match_weight, match_probability)
    st.altair_chart(chart, use_container_width=True)
    
    
    # JSON export
    with st.expander("📄 Export Records as JSON", expanded=False):
        records_json = json.dumps({
            'record_left': left_record,
            'record_right': right_record,
            'match_analysis': {
                'match_weight': match_weight,
                'match_probability': match_probability,
                'bayes_factor': bayes_factor
            }
        }, indent=2)
        st.code(records_json, language='json')
        
        if st.button("Copy to Clipboard", key="copy_json"):
            st.code("Use Ctrl+C to copy the JSON above")

    # Comparison table (Left, Right, Diff)
    st.markdown("### Detailed Record Comparison")
    st.markdown("Compare individual fields between the two records:")
    
    fields = additional_columns_to_retain

    # Build HTML table with minimal styling and diff highlighting
    header_cells = ''.join([f'<th style="padding:8px 12px; border-bottom:1px solid #e6e6e6; text-align:left; font-size:16px; font-weight:600;">{col}</th>' for col in fields])

    def safe_str(value):
        if value is None:
            return ''
        if isinstance(value, list):
            return ', '.join(str(v) for v in value if v)
        return str(value)

    # Helper function to get field values from records
    def get_field_value(record, field_name):
        """Get field value from record, handling both old and new formats"""
        # Try new format first (field_name_l/r)
        left_key = f"{field_name}_l"
        right_key = f"{field_name}_r"
        
        if left_key in record:
            return record[left_key]
        elif right_key in record:
            return record[right_key]
        elif field_name in record:
            return record[field_name]
        else:
            return ""

    left_cells = ''.join([
        f'<td style="padding:8px 12px; border-bottom:1px solid #f2f2f2; font-size:16px;">{safe_str(get_field_value(left_record, col))}</td>'
        for col in fields
    ])
    right_cells = ''.join([
        f'<td style="padding:8px 12px; border-bottom:1px solid #f2f2f2; font-size:16px;">{safe_str(get_field_value(right_record, col))}</td>'
        for col in fields
    ])
    diff_cells = ''.join([
        f'<td style="padding:8px 12px; border-bottom:1px solid #f2f2f2; font-size:16px;">{generate_diff_html(safe_str(get_field_value(left_record, col)), safe_str(get_field_value(right_record, col)))}</td>'
        for col in fields
    ])

    table_html = f'''
    <div style="overflow-x:auto; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 1rem 0;">
      <table style="width:100%; border-collapse:collapse; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji'; font-size:16px;">
        <thead>
          <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <th style="padding:15px 12px; text-align:left; width:140px; color: white; font-weight: 600; font-size:16px; border-radius: 10px 0 0 0;">Field</th>
            {header_cells}
          </tr>
        </thead>
        <tbody>
          <tr style="background: #f8f9fa;">
            <td style="padding:12px; font-weight:600; color:#495057; border-bottom:1px solid #dee2e6; font-size:16px;"> Record A</td>
            {left_cells}
          </tr>
          <tr style="background: #f8f9fa;">
            <td style="padding:12px; font-weight:600; color:#495057; border-bottom:1px solid #dee2e6; font-size:16px;"> Record B</td>
            {right_cells}
          </tr>
          <tr style="background: #fff3cd; border-top: 2px solid #ffc107;">
            <td style="padding:12px; font-weight:600; color:#856404; border-bottom:1px solid #dee2e6; font-size:16px;"> Difference</td>
            {diff_cells}
          </tr>
        </tbody>
      </table>
    </div>
    '''

    st.markdown(table_html, unsafe_allow_html=True)

def create_waterfall_chart(df, match_weight, match_probability):
    """Create waterfall chart using Altair with improved styling"""
    
    # Remove zero-height contributions (keep Prior and Final score always)
    tolerance = 1e-9
    df = df[(df['column_name'].isin(['Prior', 'Final score'])) | (df['log2_bayes_factor'].abs() > tolerance)].copy()
    df = df.sort_values('bar_sort_order').reset_index(drop=True)
    df['bar_sort_order'] = range(len(df))

    # Calculate cumulative sums for waterfall effect
    df['cumulative'] = df['log2_bayes_factor'].cumsum()
    df['previous_cumulative'] = df['cumulative'].shift(1).fillna(0)
    
    # Add probability scale (right y-axis equivalent)
    df['probability'] = df['cumulative'].apply(lambda x: 2**x / (2**x + 1))
    df['prev_probability'] = df['previous_cumulative'].apply(lambda x: 2**x / (2**x + 1))

    # Compute a shared y-domain to keep dual axes aligned
    y_min = float(min(0, df['previous_cumulative'].min(), df['cumulative'].min()))
    y_max = float(max(0, df['previous_cumulative'].max(), df['cumulative'].max()))

    # Create base chart
    base = alt.Chart(df)

    # Main bars (waterfall)
    bars = base.mark_bar(
        stroke='black',
        strokeWidth=0.8
    ).encode(
        x=alt.X(
            'column_name:N',
            sort=alt.SortField(field='bar_sort_order'),
            title='Column',
            axis=alt.Axis(
                labelAngle=0,
                labelFontSize=16,
                labelOverlap=False,
                labelPadding=0,
                labelLimit=160,
                labelExpr="datum.value"
            ),
            scale=alt.Scale(paddingInner=0, paddingOuter=0)
        ),
        y=alt.Y(
            'previous_cumulative:Q',
            axis=None,
            scale=alt.Scale(nice=False, domain=[y_min, y_max])
        ),
        y2=alt.Y2('cumulative:Q'),
        color=alt.condition(
            alt.datum.log2_bayes_factor < 0,
            alt.value('#f44336'),  # Red for negative
            alt.value('#4caf50')   # Green for positive
        ),
        opacity=alt.condition(
            (alt.datum.column_name == 'Prior') | (alt.datum.column_name == 'Final score'),
            alt.value(0.85),
            alt.value(0.75)
        ),
        tooltip=[
            alt.Tooltip('column_name:N', title='Comparison column'),
            alt.Tooltip('label_for_charts:N', title='Label'),
            alt.Tooltip('comparison_vector_value:N', title='Comparison vector value'),
            alt.Tooltip('bayes_factor:Q', title='Bayes factor = m/u', format='.4f'),
            alt.Tooltip('log2_bayes_factor:Q', title='Match weight = log2(m/u)', format='.4f'),
            alt.Tooltip('probability:Q', title='Cumulative match probability', format='.4f')
        ]
    )

    # Add text labels on bars (white, centered)
    df['bar_middle'] = (df['previous_cumulative'] + df['cumulative']) / 2
    text_labels = base.mark_text(
        align='center',
        baseline='middle',
        fontSize=24,
        fontWeight='bold',
        color='white'
    ).encode(
        x=alt.X('column_name:N', sort=alt.SortField(field='bar_sort_order')),
        y=alt.Y('bar_middle:Q', axis=None, scale=alt.Scale(nice=False, domain=[y_min, y_max])),
        text=alt.condition(
            abs(alt.datum.log2_bayes_factor) > 0.2,
            alt.Text('log2_bayes_factor:Q', format='.2f'),
            alt.value('')
        )
    )

    # Zero line baseline
    zero_line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(
        color='black',
        strokeWidth=2
    ).encode(
        y=alt.Y('y:Q', axis=None, scale=alt.Scale(domain=[y_min, y_max]))
    )

    # Right-side probability axis using an invisible layer with independent y-scale
    prob_axis = base.mark_rule(opacity=0).encode(
        y=alt.Y(
            'cumulative:Q',
            axis=alt.Axis(
                orient='right',
                title='Probability',
                titleFontSize=16,
                labelFontSize=20,
                labelExpr="format(1 / (1 + pow(2, -1*datum.value)), '.2f')",
                grid=False,
                tickCount=8,
                labelOverlap=False,
                offset=0,
                titlePadding=0
            ),
            scale=alt.Scale(nice=False, domain=[y_min, y_max])
        )
    )

    # Dedicated left axis as an invisible layer to avoid duplicates
    left_axis = base.mark_rule(opacity=0).encode(
        y=alt.Y(
            'cumulative:Q',
            axis=alt.Axis(
                orient='left',
                title='Match Weight',
                titleFontSize=16,
                labelFontSize=20,
                grid=True,
                tickCount=8,
                labelOverlap=False,
                labelPadding=0,
                offset=0,
                titlePadding=0
            ),
            scale=alt.Scale(nice=False, domain=[y_min, y_max])
        )
    )

    # Compose chart
    chart = alt.layer(
        zero_line, bars, text_labels, left_axis, prob_axis
    ).resolve_scale(
        y='independent'
    ).properties(
        width=1200,
        height=500,
        title=alt.TitleParams(
            text=['Match weights waterfall chart', 'How each comparison contributes to the final match score'],
            fontSize=24,
            anchor='start',
            offset=0
        )
    )
    
    return chart