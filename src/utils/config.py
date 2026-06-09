import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"

# 2. Force load the exact file and override the terminal
load_dotenv(dotenv_path=env_path, override=True)


class Config:

    """Centralized configuration manager."""
    
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/Harmonia_DB.sqlite")
    AZURE_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    AZURE_KEY = os.getenv("AZURE_SEARCH_KEY", "")
    AZURE_INDEX = os.getenv("AZURE_SEARCH_INDEX_NAME","")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")
    if not OPENAI_API_KEY:
        raise ValueError(
            f"\n\nCRITICAL ERROR: OPENAI_API_KEY is completely missing!"
            f"\n1. We looked for the .env file here: {env_path}"
            f"\n2. Please ensure the file is named exactly '.env' (not '.env.txt')."
            f"\n3. Ensure it contains: OPENAI_API_KEY=sk-...\n\n"
        )
    CHROMA_DB_PATH  = "C:\KUMAR PRINCE\SMR_USE_CASES\sql_agent\src\Vector_DB\chroma-db-test"
    POSTGRES_URL = os.getenv("POSTGRES_URL")
    COLLECTION_NAME = "employee-master-collection"
    VECTOR_DB_TYPE="chroma"   # Options: 'chroma' or 'azure'
    RDBMS_TYPE="sqlite"       # Options: 'sqlite' or 'postgres'