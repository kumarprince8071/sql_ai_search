from src.utils.config import Config
from src.utils.logger import logger
from src.base.base_vector_db import BaseVectorDB
from src.base.base_rdbms import BaseRDBMS
from src.clients.vector.chroma_client import ChromaSearchClient
from src.clients.vector.azure_search_client import AzureSearchClient
from src.clients.rdbms.sqlite_client import SQLiteClient
from src.clients.rdbms.postgres_client import PostgresClient 


class VectorDBProvider:
    """Instantiates the correct vector DB clients based on environment configurations."""

    @staticmethod
    def get_vector_client() -> BaseVectorDB:
        """ initialize the vector client"""

        if Config.VECTOR_DB_TYPE == "azure":
            logger.info("Factory: Initializing Azure AI Search Client...")
            return AzureSearchClient(
                endpoint=Config.AZURE_ENDPOINT,
                key=Config.AZURE_KEY,
                index_name=Config.AZURE_INDEX
            )
        elif Config.VECTOR_DB_TYPE == "chroma":
            logger.info("Factory: Initializing Local ChromaDB Client...")
            return ChromaSearchClient(
                db_dir=Config.CHROMA_DB_PATH,
                collection_name=Config.COLLECTION_NAME,
                api_key=Config.OPENAI_API_KEY
            )
        else:
            raise ValueError(f"Unsupported VECTOR_DB_TYPE: {Config.VECTOR_DB_TYPE}")
        
class RDBMSProvider:
    """Instantiates the correct database clients based on environment configurations."""

    @staticmethod
    def get_rdbms_client() -> BaseRDBMS:
        """initialize the database client"""
        
        if Config.RDBMS_TYPE == "postgres":
            logger.info("Factory: Initializing PostgreSQL Client...")
            return PostgresClient(connection_url=Config.POSTGRES_URL)
        elif Config.RDBMS_TYPE == "sqlite":
            logger.info("Factory: Initializing SQLite Client...")
            return SQLiteClient(db_path=Config.SQLITE_DB_PATH)
        else:
            raise ValueError(f"Unsupported RDBMS_TYPE: {Config.RDBMS_TYPE}")