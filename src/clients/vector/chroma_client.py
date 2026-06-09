import chromadb
from langchain_openai import OpenAIEmbeddings
from src.utils.logger import logger
import asyncio

class ChromaSearchClient:
    """Handles semantic querying against the local ChromaDB vector space."""
    
    def __init__(self, db_dir: str, collection_name: str, api_key: str):
        logger.info(f"Connecting to ChromaDB at {db_dir}...")
        self.chroma_client = chromadb.PersistentClient(path=db_dir)
        self.collection = self.chroma_client.get_collection(name=collection_name)
        self.embedder = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)

    async def fetch_few_shot_examples(self, query_text: str, top_k: int = 2) -> str:
        """Fetches the top relevant SQL examples from the sql_few_shots collection."""
        try:
            # Dynamically grab the few-shot collection using the existing persistent client
            collection = self.chroma_client.get_collection("sql_few_shots")
            query_vector = await self.embedder.aembed_query(query_text)
            def do_query():
                return collection.query(
                    query_embeddings=[query_vector],
                    n_results=top_k
                )
            
            raw_results = await asyncio.to_thread(do_query)
            
            if not raw_results.get('documents') or not raw_results['documents'][0]:
                return ""
                
            prompt_injection = "### SIMILAR PREVIOUS EXAMPLES FOR REFERENCE ###\n"
            for i in range(len(raw_results['documents'][0])):
                prompt_injection += f"USER QUERY: {raw_results['documents'][0][i]}\n"
                prompt_injection += f"RESOLVED FILTERS: {raw_results['metadatas'][0][i]['filters']}\n"
                prompt_injection += f"CORRECT SQL: {raw_results['metadatas'][0][i]['sql']}\n\n"
                
            return prompt_injection
            
        except Exception as e:
            logger.warning(f"VectorClient: Could not fetch few-shot examples. Error: {e}")
            return ""


    async def search(self, query_text: str, target_table: str = None, top_k: int = 20) -> list[dict]:
        """ Using Vector search on key:value provided in the filter from intent agent"""
        
        query_vector = await self.embedder.aembed_query(query_text)
        where_filter = {"TableName": target_table} if target_table else None    

        def do_query():
            return self.collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where_filter
            )
        raw_results = await asyncio.to_thread(do_query)
        
        if not raw_results or not raw_results.get("ids") or not raw_results["ids"][0]:
            return []

        standardized_results = []
        distances = raw_results.get("distances", [[0]*top_k])[0]
        docs = raw_results.get("documents", [[""]*top_k])[0]
        metas = raw_results.get("metadatas", [[{}]*top_k])[0]
        chroma_system_keys = {"content", "content_vector", "table_name", "DocId"}

        for i in range(len(raw_results["ids"][0])):
            distance = distances[i] if distances is not None else 1.0
            semantic_score = max(1.0 - distance, 0.0)
            
            pure_meta = {k: v for k, v in metas[i].items() if k not in chroma_system_keys}
            
            standardized_results.append({
                "id": raw_results["ids"][0][i],
                "score": semantic_score,
                "content": docs[i],
                "metadata": pure_meta
            })

        standardized_results.sort(key=lambda x: x["score"], reverse=True)
        return standardized_results