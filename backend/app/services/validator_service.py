import csv
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd

class ValidatorService:
    @staticmethod
    def validate_csv(file_path: str, columns_config: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
        """
        Validates CSV against configured dynamic schema:
        1. Checks exact matching columns (no missing required columns, no unexpected extra columns).
        2. Validates Primary Key column presence and non-null values.
        3. Validates data types for each cell.
        Returns: (parsed_records, primary_key_col) or raises ValueError
        """
        # Read header first
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            try:
                headers = [h.strip() for h in next(reader)]
            except StopIteration:
                raise ValueError("CSV file is empty")

        expected_cols = [c["name"].strip() for c in columns_config]
        pk_cols = [c["name"].strip() for c in columns_config if c.get("is_primary_key")]
        if not pk_cols:
            raise ValueError("Job configuration error: No Primary Key column configured")
        primary_key_col = pk_cols[0]

        # 1. Check for missing columns
        missing_cols = set(expected_cols) - set(headers)
        if missing_cols:
            raise ValueError(f"Schema validation failed: Missing required column(s): {', '.join(sorted(missing_cols))}")

        # 2. Check for unexpected columns
        unexpected_cols = set(headers) - set(expected_cols)
        if unexpected_cols:
            raise ValueError(f"Schema validation failed: Unexpected column(s) found in CSV: {', '.join(sorted(unexpected_cols))}. Expected columns: {', '.join(expected_cols)}")

        # 3. Read data with Pandas
        df = pd.read_csv(file_path, dtype=str)
        # Clean string whitespace
        df.columns = df.columns.str.strip()

        col_type_map = {c["name"].strip(): c.get("type", "String") for c in columns_config}
        col_req_map = {c["name"].strip(): c.get("is_required", True) for c in columns_config}

        records = []
        seen_pks = set()

        for idx, row in df.iterrows():
            row_num = idx + 2  # 1-based, header is line 1
            record = {}

            # Primary key check
            pk_val = row.get(primary_key_col)
            if pd.isna(pk_val) or str(pk_val).strip() == "":
                raise ValueError(f"Row {row_num}: Primary Key '{primary_key_col}' cannot be null or empty")
            
            clean_pk = str(pk_val).strip()
            if clean_pk in seen_pks:
                raise ValueError(f"Row {row_num}: Duplicate Primary Key '{clean_pk}' found in uploaded CSV file")
            seen_pks.add(clean_pk)

            for col in expected_cols:
                raw_val = row.get(col)
                is_req = col_req_map.get(col, True)
                col_type = col_type_map.get(col, "String")

                if pd.isna(raw_val) or str(raw_val).strip() == "":
                    if is_req:
                        raise ValueError(f"Row {row_num}: Required column '{col}' cannot be empty")
                    record[col] = None
                    continue

                val_str = str(raw_val).strip()

                # Validate data type
                if col_type == "Integer":
                    try:
                        record[col] = int(val_str)
                    except ValueError:
                        raise ValueError(f"Row {row_num}: Invalid Integer value for column '{col}': '{val_str}'")
                elif col_type == "Float":
                    try:
                        record[col] = float(val_str.replace("$", "").replace(",", ""))
                    except ValueError:
                        raise ValueError(f"Row {row_num}: Invalid Float / Numeric value for column '{col}': '{val_str}'")
                elif col_type == "Date":
                    try:
                        # Attempt to parse date
                        parsed_dt = pd.to_datetime(val_str)
                        record[col] = parsed_dt.strftime("%Y-%m-%d")
                    except Exception:
                        raise ValueError(f"Row {row_num}: Invalid Date format for column '{col}': '{val_str}' (Expected YYYY-MM-DD)")
                elif col_type == "Boolean":
                    lower_val = val_str.lower()
                    if lower_val in ["true", "1", "t", "yes"]:
                        record[col] = True
                    elif lower_val in ["false", "0", "f", "no"]:
                        record[col] = False
                    else:
                        raise ValueError(f"Row {row_num}: Invalid Boolean value for column '{col}': '{val_str}' (Expected True/False)")
                else:
                    record[col] = val_str

            records.append(record)

        return records, primary_key_col
