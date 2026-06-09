import sqlite3
import pandas as pd
import asyncio
from src.base.base_rdbms import BaseRDBMS
from src.core.exceptions import SQLValidationError
from src.utils.logger import logger


class SQLiteClient(BaseRDBMS):
    """Concrete implementation for SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _execute_sync(self, query: str) -> list[dict]:
        """Synchronous execution function to be run in a separate thread."""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            raise SQLValidationError(f"Database rejected the query: {str(e)}")

    async def execute_query(self, query: str) -> list[dict]:
        """Safely executes the query without blocking the main event loop."""

        return await asyncio.to_thread(self._execute_sync, query)

    async def get_dataframe(self, query: str) -> pd.DataFrame:
        """Converts query results into a Pandas DataFrame."""

        results = await self.execute_query(query)
        return pd.DataFrame(results)

    async def get_schema(self) -> str:
        """Fetches the DB schema dynamically."""

        query = "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        results = await self.execute_query(query)
        return "\n".join([row['sql'] for row in results if row['sql']])
    
    async def get_schema_cache(self) -> dict:
        """
        SQLite specific dialect for fetching all tables and columns.
        Returns a map of {column_name: table_name} required by the VectorSearchTool.
        """
        logger.info("Building SQLite dynamic schema cache...")
        cache = {}
        
        tables = await self.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        
        for t in tables:
            table_name = t['name']
            columns = await self.execute_query(f"PRAGMA table_info({table_name});")
            for col in columns:
                cache[col['name'].lower()] = table_name
                
        return cache