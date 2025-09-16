import duckdb
import json
import pandas as pd
import numpy as np

class DuckDBHandler:
    def __init__(self):
        self.conn = duckdb.connect()
    
    def compare_records(self, left_record, right_record):
        """Run Splink comparison between two records"""
        try:
            # Load SQL query
            with open('data/query.sql', 'r') as f:
                sql_query = f.read()
            
            # Create temporary tables
            left_df = pd.DataFrame([left_record])
            right_df = pd.DataFrame([right_record])
            
            # Register dataframes with correct Splink table names
            self.conn.register('__splink__compare_two_records_left', left_df)
            self.conn.register('__splink__compare_two_records_right', right_df)
            
            # Run the comparison query using a cursor object
            cursor = self.conn.execute(sql_query)
            row = cursor.fetchone()

            if row is not None:
                # Get column names reliably from the cursor
                if cursor.description is None:
                    raise Exception('No cursor description available after executing query')
                columns = [col[0] for col in cursor.description]
                # Build a dictionary mapping column names to values
                df = pd.DataFrame([row], columns=columns)
                if df is not None and not df.empty:
                    # Convert the first row to a plain Python dict with native Python scalars
                    series = df.iloc[0]
                    def to_py(v):
                        if isinstance(v, (np.generic,)):
                            return v.item()
                        return v
                    result_dict = {k: to_py(v) for k, v in series.to_dict().items()}
                    return result_dict
                else:
                    return None
            else:
                return None
            
        except Exception as e:
            # Re-raise the exception to be handled by the calling code
            raise Exception(f"Error running comparison: {str(e)}")
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()