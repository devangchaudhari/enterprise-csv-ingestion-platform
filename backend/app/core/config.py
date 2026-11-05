import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "OmniRetail Enterprise Data Integration & Workflow Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "enterprise-super-secret-jwt-key-2026-secure-random-32bytes!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./enterprise_data_platform.db"
    )

    # Data Warehouse configuration
    WAREHOUSE_TYPE: str = os.getenv("WAREHOUSE_TYPE", "local")  # 'local', 'postgres', or 'snowflake'
    SNOWFLAKE_ACCOUNT: Optional[str] = os.getenv("SNOWFLAKE_ACCOUNT", None)
    SNOWFLAKE_USER: Optional[str] = os.getenv("SNOWFLAKE_USER", None)
    SNOWFLAKE_PASSWORD: Optional[str] = os.getenv("SNOWFLAKE_PASSWORD", None)
    SNOWFLAKE_DATABASE: Optional[str] = os.getenv("SNOWFLAKE_DATABASE", "RETAIL_DW")
    SNOWFLAKE_SCHEMA: Optional[str] = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
    SNOWFLAKE_WAREHOUSE: Optional[str] = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")

    # Redis & Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # SFTP Server configuration
    SFTP_HOST: str = os.getenv("SFTP_HOST", "127.0.0.1")
    SFTP_PORT: int = int(os.getenv("SFTP_PORT", "2222"))
    SFTP_USER: str = os.getenv("SFTP_USER", "retail_partner")
    SFTP_PASSWORD: str = os.getenv("SFTP_PASSWORD", "PartnerSecure2026!")
    SFTP_ROOT_DIR: str = os.getenv("SFTP_ROOT_DIR", "./data/samples/sftp_root")

    # Downstream Partner REST API
    DOWNSTREAM_API_URL: str = os.getenv(
        "DOWNSTREAM_API_URL", 
        "http://127.0.0.1:8000/api/v1/mock-retail/downstream-orders"
    )
    DOWNSTREAM_API_KEY: str = os.getenv("DOWNSTREAM_API_KEY", "partner-live-token-xyz-2026")

    # Azure Logic Apps integration
    AZURE_LOGIC_APP_URL: Optional[str] = os.getenv("AZURE_LOGIC_APP_URL", None)
    AZURE_TENANT_ID: Optional[str] = os.getenv("AZURE_TENANT_ID", None)
    AZURE_CLIENT_ID: Optional[str] = os.getenv("AZURE_CLIENT_ID", None)
    AZURE_CLIENT_SECRET: Optional[str] = os.getenv("AZURE_CLIENT_SECRET", None)

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
