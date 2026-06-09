import asyncpg
from typing import List, Dict, Any
from src.base.base_rdbms import BaseRDBMS
from src.utils.logger import logger

class PostgresClient(BaseRDBMS):
    """Concrete implementation for PostgreSQL using asyncpg."""

    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.pool = None

    async def _get_pool(self):
        """Initializes the connection pool dynamically."""

        if not self.pool:
            logger.info("Initializing PostgreSQL connection pool...")
            self.pool = await asyncpg.create_pool(dsn=self.connection_url)
        return self.pool

    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Executes a SQL query and returns results as a list of dictionaries."""
        
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                records = await conn.fetch(query, *args)
                return [dict(record) for record in records]
        except Exception as e:
            logger.error(f"PostgreSQL Query Execution Failed: {e}\nQuery: {query}")
            return []

    async def get_schema_cache(self) -> Dict[str, str]:
        """
        PostgreSQL specific dialect for fetching all tables and columns.
        Returns a map of {column_name: table_name}
        """
        logger.info("Building PostgreSQL dynamic schema cache...")
        cache = {}
        
        query = """
            SELECT table_name, column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public';
        """
        
        rows = await self.execute_query(query)
        for row in rows:
            table = row['table_name']
            col = row['column_name'].lower()
            cache[col] = table
            
        return cache