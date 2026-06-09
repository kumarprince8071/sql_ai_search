import asyncio
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery, QueryType
from langchain_openai import OpenAIEmbeddings
from src.base.base_vector_db import BaseVectorDB
from src.utils.logger import logger
import base64


class AzureSearchClient(BaseVectorDB):
    """Concrete implementation for Azure AI Search."""

    def __init__(self, endpoint: str, key: str, index_name: str):
        self.endpoint = endpoint
        self.credential = AzureKeyCredential(key)
        self.index_name = index_name
        self.embedder = OpenAIEmbeddings(model="text-embedding-3-small")
        self.client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential
        )

    async def search(self, query_text: str, target_table: str = None, top_k: int = 20) -> list[dict]:
        """ Using Vector search on key:value provided in the filter from intent agent"""
        
        query_vector = await self.embedder.aembed_query(query_text)
        vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields="content_vector")
        odata_filter = f"TableName eq '{target_table}'" if target_table else None

        def do_search():
            return list(self.client.search(
                search_text=query_text,
                vector_queries=[vector_query],
                filter=odata_filter,
                top=top_k,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="smr-semantic" 
            ))

        raw_azure_results = await asyncio.to_thread(do_search)
        standardized_results = []
        azure_system_keys = {"content", "content_vector", "@search.score", "@search.reranker_score", "@search.highlights", "@search.captions", "table_name"}
        
        for doc in raw_azure_results:
            # 1. Normalize Score to 0.0 - 1.0 (Azure Reranker is usually out of 4.0)
            raw_score = doc.get("@search.reranker_score") or doc.get("@search.score") or 0.0
            normalized_score = min(float(raw_score) / 4.0, 1.0) 

            # 2. Decode Base64 ID safely
            raw_id = doc.get("id", "")
            clean_id = raw_id
            if isinstance(raw_id, str) and len(raw_id) % 4 == 0:
                try:
                    decoded = base64.b64decode(raw_id).decode("utf-8")
                    if any(char.isdigit() for char in decoded): clean_id = decoded
                except Exception: pass
                
            pure_meta = {k: v for k, v in doc.items() if k not in azure_system_keys}
            
            standardized_results.append({
                "id": clean_id,
                "score": normalized_score,
                "content": doc.get("content", ""),
                "metadata": pure_meta
            })
            
        standardized_results.sort(key=lambda x: x["score"], reverse=True)
        return standardized_results