import streamlit as st
import altair as alt
import pandas as pd
import json
from utils.splink_utils import prediction_row_to_waterfall_format, bayes_factor_to_prob, generate_diff_html

def display_results(result, left_record, right_record):
    """Display comparison results with waterfall chart and table"""
    
    # Extract match weight and probability
    match_weight = result.get('match_weight', 0)
    bayes_factor = 2 ** match_weight
    match_probability = bayes_factor_to_prob(bayes_factor)
    error_probability = 1 - match_probability
    
    # Display formatted title with highlighted metrics
    # Center the title
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown(f"""## Match weight <span style="color: #2196F3; font-weight: bold;">{match_weight:.4f}</span> corresponding to match probability <span style="color: #4CAF50; font-weight: bold;">{match_probability:.2%}</span>""", unsafe_allow_html=True)
    
    # Create waterfall chart
    waterfall_data = prediction_row_to_waterfall_format(result)
    waterfall_df = pd.DataFrame(waterfall_data)
    
    # Create the waterfall chart using Altair and center it
    chart = create_waterfall_chart(waterfall_df, match_weight, match_probability)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.altair_chart(chart, use_container_width=False)
    
    
    # JSON export
    with st.expander("📄 Export Records as JSON"):
        records_json = json.dumps({
            'record_left': left_record,
            'record_right': right_record
        }, indent=2)
        st.code(records_json, language='json')
        
        if st.button("📋 Copy to Clipboard"):
            st.code("Use Ctrl+C to copy the JSON above")

    # Comparison table (Left, Right, Diff)
    st.subheader("📋 Record Comparison")
    fields = ['first_name', 'surname', 'dob', 'birth_place', 'postcode_fake', 'occupation']

    # Build HTML table with minimal styling and diff highlighting
    header_cells = ''.join([f'<th style="padding:8px 12px; border-bottom:1px solid #e6e6e6; text-align:left;">{col}</th>' for col in fields])

    def safe_str(value):
        return '' if value is None else str(value)

    left_cells = ''.join([
        f'<td style="padding:8px 12px; border-bottom:1px solid #f2f2f2;">{safe_str(left_record.get(col, ""))}</td>'
        for col in fields
    ])
    right_cells = ''.join([
        f'<td style="padding:8px 12px; border-bottom:1px solid #f2f2f2;">{safe_str(right_record.get(col, ""))}</td>'
        for col in fields
    ])
    diff_cells = ''.join([
        f'<td style="padding:8px 12px; border-bottom:1px solid #f2f2f2;">{generate_diff_html(safe_str(left_record.get(col, "")), safe_str(right_record.get(col, "")))}</td>'
        for col in fields
    ])

    table_html = f'''
    <div style="overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji'; font-size:14px;">
        <tr>
          <th style="padding:8px 12px; border-bottom:2px solid #ddd; text-align:left; width:140px;"> </th>
          {header_cells}
        </tr>
        <tr>
          <td style="padding:8px 12px; border-bottom:1px solid #f2f2f2; font-weight:600; color:#555;">Left Record</td>
          {left_cells}
        </tr>
        <tr>
          <td style="padding:8px 12px; border-bottom:1px solid #f2f2f2; font-weight:600; color:#555;">Right Record</td>
          {right_cells}
        </tr>
        <tr>
          <td style="padding:8px 12px; border-bottom:1px solid #f2f2f2; font-weight:600; color:#555;">Diff</td>
          {diff_cells}
        </tr>
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
                labelFontSize=12,
                labelOverlap=True,
                labelPadding=4,
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
        fontSize=12,
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
                labelExpr="format(1 / (1 + pow(2, -1*datum.value)), '.2r')",
                grid=False,
                tickCount=8,
                labelOverlap=True,
                offset=24,
                titlePadding=30
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
                grid=True,
                tickCount=8,
                labelOverlap=True,
                labelPadding=4,
                offset=0,
                titlePadding=30
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
        width=1000,
        height=450,
        title=alt.TitleParams(
            text=['Match weights waterfall chart', 'How each comparison contributes to the final match score'],
            fontSize=16,
            anchor='start',
            offset=10
        )
    )
    
    return chart