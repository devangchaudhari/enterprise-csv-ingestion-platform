from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from backend.app.services.snowflake_engine import SnowflakeEngine

router = APIRouter(prefix="/database", tags=["Database"])

@router.get("/status")
def get_database_status():
    is_cloud, message = SnowflakeEngine.is_cloud_connected()
    return {
        "is_cloud": is_cloud,
        "is_cloud_connected": is_cloud,
        "mode_label": message,
        "engine_type": "Snowflake Cloud" if is_cloud else "Local Warehouse Mode (PostgreSQL/SQLite Engine)"
    }

@router.get("/tables")
def list_tables():
    raw_tables = SnowflakeEngine.list_tables()
    is_cloud, mode_label = SnowflakeEngine.is_cloud_connected()
    # Sort with EMPLOYEE at the top if present
    sorted_tables = sorted(
        raw_tables, 
        key=lambda t: (0 if t["name"] == "EMPLOYEE" else 1, t["name"])
    )
    return {
        "tables": [t["name"] for t in sorted_tables],
        "table_details": sorted_tables,
        "engine_mode": "Snowflake Cloud" if is_cloud else "Local Warehouse Mode"
    }

@router.get("/tables/{name}/schema")
def get_table_schema(name: str):
    schema = SnowflakeEngine.get_table_schema(name)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Table '{name}' not found")
    is_cloud, mode_label = SnowflakeEngine.is_cloud_connected()
    return {
        "table_name": name,
        "columns": schema,
        "engine_mode": "Snowflake Cloud" if is_cloud else mode_label
    }

@router.get("/tables/{name}/data")
def get_table_data(
    name: str,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: Optional[str] = None,
    sort_order: Optional[str] = None,
    page: Optional[int] = Query(None),
    page_size: Optional[int] = Query(None),
    limit: Optional[int] = Query(50),
    offset: Optional[int] = Query(0)
):
    direction = sort_order or sort_dir or "desc"
    eff_limit = page_size if page_size is not None else (limit or 50)
    eff_offset = ((page - 1) * eff_limit) if (page is not None and page > 0) else (offset or 0)

    try:
        res = SnowflakeEngine.get_table_data(
            table_name=name,
            search=search,
            sort_by=sort_by,
            sort_dir=direction,
            limit=eff_limit,
            offset=eff_offset
        )
        is_cloud, mode_label = SnowflakeEngine.is_cloud_connected()
        res["engine_mode"] = "Snowflake Cloud" if is_cloud else mode_label
        res["page"] = page or 1
        res["page_size"] = eff_limit
        if res.get("columns") and isinstance(res["columns"][0], dict):
            res["schema"] = res["columns"]
            res["columns"] = [c["name"] for c in res["columns"]]
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch data from table '{name}': {str(e)}")
