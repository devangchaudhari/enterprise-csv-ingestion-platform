from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import text, inspect
from backend.app.core.database import engine, SessionLocal
from backend.app.models.schema_models import SnowflakeConfig

class SnowflakeEngine:
    @staticmethod
    def get_config() -> Optional[SnowflakeConfig]:
        db = SessionLocal()
        try:
            cfg = db.query(SnowflakeConfig).filter(SnowflakeConfig.is_active == True).first()
            return cfg
        finally:
            db.close()

    @staticmethod
    def is_cloud_connected() -> Tuple[bool, str]:
        cfg = SnowflakeEngine.get_config()
        if not cfg or not cfg.account or not cfg.user or not cfg.password:
            return False, "Local Warehouse Mode (PostgreSQL/SQLite Engine)"
        
        # Test connection
        try:
            import snowflake.connector
            conn = snowflake.connector.connect(
                user=cfg.user,
                password=cfg.password,
                account=cfg.account,
                warehouse=cfg.warehouse,
                database=cfg.database,
                schema=cfg.schema_name,
                login_timeout=5
            )
            conn.close()
            return True, f"Snowflake Cloud Connected ({cfg.database}.{cfg.schema_name})"
        except Exception as e:
            return False, f"Local Warehouse Mode (Snowflake fallback: {str(e)[:100]})"

    @staticmethod
    def ensure_table(table_name: str, columns_config: List[Dict[str, Any]], primary_key_col: str):
        """
        Creates target table with business columns + CREATED_DATE + MODIFIED_DATE.
        """
        table_name = table_name.strip().upper()
        type_map = {
            "String": "VARCHAR(255)",
            "Integer": "BIGINT",
            "Float": "NUMERIC(18, 4)",
            "Date": "DATE",
            "Boolean": "BOOLEAN"
        }

        col_defs = []
        for col in columns_config:
            c_name = col["name"].strip()
            c_type = type_map.get(col.get("type", "String"), "VARCHAR(255)")
            if c_name == primary_key_col:
                col_defs.append(f'"{c_name}" {c_type} PRIMARY KEY')
            else:
                col_defs.append(f'"{c_name}" {c_type}')

        # Add automatic audit columns
        col_defs.append('"CREATED_DATE" TIMESTAMP')
        col_defs.append('"MODIFIED_DATE" TIMESTAMP')

        ddl = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n  ' + ",\n  ".join(col_defs) + "\n)"

        is_cloud, _ = SnowflakeEngine.is_cloud_connected()
        if is_cloud:
            cfg = SnowflakeEngine.get_config()
            import snowflake.connector
            conn = snowflake.connector.connect(
                user=cfg.user, password=cfg.password, account=cfg.account,
                warehouse=cfg.warehouse, database=cfg.database, schema=cfg.schema_name
            )
            cursor = conn.cursor()
            cursor.execute(ddl)
            cursor.close()
            conn.close()
        else:
            with engine.connect() as conn:
                conn.execute(text(ddl))
                conn.commit()

    @staticmethod
    def upsert_records(
        table_name: str, 
        records: List[Dict[str, Any]], 
        columns_config: List[Dict[str, Any]], 
        primary_key_col: str
    ) -> Tuple[int, int, str]:
        """
        Executes MERGE upsert logic:
        - If PK exists: update business columns and set MODIFIED_DATE = CURRENT_TIMESTAMP (preserves CREATED_DATE)
        - If PK does not exist: insert business columns and set CREATED_DATE and MODIFIED_DATE to CURRENT_TIMESTAMP
        Returns: (inserted_count, updated_count, engine_used)
        """
        table_name = table_name.strip().upper()
        SnowflakeEngine.ensure_table(table_name, columns_config, primary_key_col)

        is_cloud, mode_label = SnowflakeEngine.is_cloud_connected()
        now_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        col_names = [c["name"].strip() for c in columns_config]
        update_cols = [c for c in col_names if c != primary_key_col]

        inserted_count = 0
        updated_count = 0

        with engine.connect() as conn:
            for rec in records:
                pk_val = rec[primary_key_col]
                # Check if existing
                check_sql = text(f'SELECT "CREATED_DATE" FROM "{table_name}" WHERE "{primary_key_col}" = :pk')
                res = conn.execute(check_sql, {"pk": pk_val}).fetchone()

                if res:
                    # Update
                    if update_cols:
                        set_clauses = [f'"{col}" = :{col}' for col in update_cols]
                        set_clauses.append('"MODIFIED_DATE" = :mod_date')
                        upd_sql = text(f'UPDATE "{table_name}" SET {", ".join(set_clauses)} WHERE "{primary_key_col}" = :pk')
                        params = {col: rec[col] for col in update_cols}
                        params["pk"] = pk_val
                        params["mod_date"] = now_ts
                        conn.execute(upd_sql, params)
                    else:
                        conn.execute(text(f'UPDATE "{table_name}" SET "MODIFIED_DATE" = :mod_date WHERE "{primary_key_col}" = :pk'), {"pk": pk_val, "mod_date": now_ts})
                    updated_count += 1
                else:
                    # Insert
                    all_cols = col_names + ["CREATED_DATE", "MODIFIED_DATE"]
                    col_str = ", ".join([f'"{c}"' for c in all_cols])
                    val_str = ", ".join([f':{c}' for c in all_cols])
                    ins_sql = text(f'INSERT INTO "{table_name}" ({col_str}) VALUES ({val_str})')
                    params = {c: rec[c] for c in col_names}
                    params["CREATED_DATE"] = now_ts
                    params["MODIFIED_DATE"] = now_ts
                    conn.execute(ins_sql, params)
                    inserted_count += 1

            conn.commit()

        # If Cloud Snowflake is enabled, sync to Snowflake as well
        if is_cloud:
            try:
                cfg = SnowflakeEngine.get_config()
                import snowflake.connector
                conn = snowflake.connector.connect(
                    user=cfg.user, password=cfg.password, account=cfg.account,
                    warehouse=cfg.warehouse, database=cfg.database, schema=cfg.schema_name
                )
                cursor = conn.cursor()
                for rec in records:
                    pk_val = rec[primary_key_col]
                    cursor.execute(f'SELECT "CREATED_DATE" FROM "{table_name}" WHERE "{primary_key_col}" = %s', (pk_val,))
                    sn_res = cursor.fetchone()
                    if sn_res:
                        set_parts = [f'"{col}" = %s' for col in update_cols]
                        set_parts.append('"MODIFIED_DATE" = CURRENT_TIMESTAMP()')
                        upd_q = f'UPDATE "{table_name}" SET {", ".join(set_parts)} WHERE "{primary_key_col}" = %s'
                        cursor.execute(upd_q, tuple([rec[c] for c in update_cols] + [pk_val]))
                    else:
                        all_c = col_names + ["CREATED_DATE", "MODIFIED_DATE"]
                        col_clause = ", ".join([f'"{c}"' for c in all_c])
                        val_clause = ", ".join(["%s"] * len(col_names)) + ", CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()"
                        ins_q = f'INSERT INTO "{table_name}" ({col_clause}) VALUES ({val_clause})'
                        cursor.execute(ins_q, tuple([rec[c] for c in col_names]))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception:
                pass

        return inserted_count, updated_count, mode_label

    @staticmethod
    def list_tables() -> List[Dict[str, Any]]:
        inspector = inspect(engine)
        all_tables = inspector.get_table_names()
        # Exclude system metadata tables
        system_tables = {"folders", "uploaded_files", "ingestion_jobs", "job_executions", "snowflake_config", "alembic_version"}
        user_tables = [t for t in all_tables if t.lower() not in system_tables]

        results = []
        with engine.connect() as conn:
            for t in sorted(user_tables):
                try:
                    count = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
                except Exception:
                    count = 0
                results.append({"name": t, "row_count": count})
        return results

    @staticmethod
    def get_table_schema(table_name: str) -> List[Dict[str, str]]:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_cols = pk_constraint.get("constrained_columns", [])

        schema = []
        for c in columns:
            schema.append({
                "name": c["name"],
                "type": str(c["type"]),
                "is_primary_key": c["name"] in pk_cols,
                "is_audit_column": c["name"] in ["CREATED_DATE", "MODIFIED_DATE"]
            })
        return schema

    @staticmethod
    def get_table_data(
        table_name: str,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_dir: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        with engine.connect() as conn:
            # Total count
            total_count = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar() or 0

            query_str = f'SELECT * FROM "{table_name}"'
            params = {}

            if search:
                # Search across all columns
                schema = SnowflakeEngine.get_table_schema(table_name)
                conditions = []
                for idx, col in enumerate(schema):
                    p_name = f"search_{idx}"
                    conditions.append(f'CAST("{col["name"]}" AS TEXT) LIKE :{p_name}')
                    params[p_name] = f"%{search}%"
                if conditions:
                    query_str += " WHERE " + " OR ".join(conditions)

            if sort_by:
                query_str += f' ORDER BY "{sort_by}" {sort_dir.upper()}'
            else:
                # Default sort by MODIFIED_DATE desc if present
                query_str += ' ORDER BY "MODIFIED_DATE" DESC'

            query_str += f' LIMIT {limit} OFFSET {offset}'

            rows = conn.execute(text(query_str), params).fetchall()
            schema = SnowflakeEngine.get_table_schema(table_name)
            col_names = [c["name"] for c in schema]

            data = []
            for r in rows:
                data.append(dict(zip(col_names, r)))

            return {
                "table_name": table_name,
                "total_records": total_count,
                "returned_records": len(data),
                "columns": schema,
                "records": data
            }
