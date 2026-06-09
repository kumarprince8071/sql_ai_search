import os
import sqlite3
import asyncio
from typing import List, Dict
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField,
    SearchFieldDataType, VectorSearch, HnswAlgorithmConfiguration,
    VectorSearchProfile, SemanticConfiguration, SemanticPrioritizedFields,
    SemanticField, SemanticSearch
)
from langchain_openai import OpenAIEmbeddings

# ==========================================
# 1. CONFIGURATION
# ==========================================
SQLITE_DB_PATH = "harmonia.db"  # Change this to your actual database path
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "https://<your-search-service>.search.windows.net")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "<your-admin-key>")
INDEX_NAME = "employee-records-index"  # NEW INDEX NAME for the actual data
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "<your-openai-key>")

# ==========================================
# 2. AZURE INDEX SETUP (For Employee Records)
# ==========================================
def setup_employee_index():
    print(f"Configuring Azure Search Index: '{INDEX_NAME}'...")
    credential = AzureKeyCredential(AZURE_SEARCH_KEY)
    index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)

    # Define fields tailored for Employee Data
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="GlobalUserId", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="FullName", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String), # Holds the Key-Value string
        SearchField(
            name="content_vector", 
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True, 
            vector_search_dimensions=1536,
            vector_search_profile_name="myHnswProfile"
        )
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
        profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")]
    )

    semantic_config = SemanticConfiguration(
        name="default-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="FullName"),
            content_fields=[SemanticField(field_name="content")]
        )
    )
    semantic_search = SemanticSearch(configurations=[semantic_config])

    index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search, semantic_search=semantic_search)
    index_client.create_or_update_index(index)
    print("Employee Index successfully configured.\n")

# ==========================================
# 3. DATA EXTRACTION & FORMATTING
# ==========================================
def get_formatted_employee_records() -> List[Dict]:
    print("Extracting records from SQLite Database...")
    records = []
    
    # Connect to the database
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row  # Allows us to access columns by name
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM employee_master")
    rows = cursor.fetchall()
    
    noise_values = {"n/a", "not available", "", "none", "null"}
    
    for row in rows:
        row_dict = dict(row)
        kv_pairs = []
        
        # Iterate through every column in the row
        for col_name, value in row_dict.items():
            # 1. Skip integers and floats
            if isinstance(value, (int, float)):
                continue
                
            # 2. Skip Nulls and Empty Values
            if value is None:
                continue
                
            # 3. Skip "N/A" and "Not Available" noise
            str_val = str(value).strip()
            if str_val.lower() in noise_values:
                continue
                
            # Append to our Key-Value list
            kv_pairs.append(f"{col_name}: {str_val}")
            
        # Join all valid pairs into a single string
        key_value_string = ", ".join(kv_pairs)
        
        records.append({
            "GlobalUserId": str(row_dict.get("GlobalUserId", "UNKNOWN")),
            "FullName": str(row_dict.get("FullName", "UNKNOWN")),
            "content": key_value_string
        })
        
    conn.close()
    print(f"Successfully processed {len(records)} employee records.")
    return records

# ==========================================
# 4. ASYNC EMBEDDING & UPLOAD
# ==========================================
async def embed_and_upload_employees():
    records = get_formatted_employee_records()
    
    print(f"Initializing Embedder and Search Client...")
    embedder = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_API_KEY)
    search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=AzureKeyCredential(AZURE_SEARCH_KEY))

    documents_to_upload: List[Dict] = []
    
    # We will upload in batches to avoid Azure size limits
    BATCH_SIZE = 100 
    
    for i, record in enumerate(records):
        content_text = record["content"]
        
        # Skip if the row was entirely empty/N/A
        if not content_text:
            continue
            
        # Generate embedding vector
        content_vector = await embedder.aembed_query(content_text)
        
        # Create the Azure Document
        doc = {
            "id": str(i), 
            "GlobalUserId": record["GlobalUserId"],
            "FullName": record["FullName"],
            "content": content_text,
            "content_vector": content_vector
        }
        documents_to_upload.append(doc)
        
        # Batch Upload Logic
        if len(documents_to_upload) >= BATCH_SIZE:
            print(f"Uploading batch of {BATCH_SIZE} records...")
            search_client.upload_documents(documents=documents_to_upload)
            documents_to_upload.clear()  # Reset batch

    # Upload any remaining documents
    if documents_to_upload:
        print(f"Uploading final batch of {len(documents_to_upload)} records...")
        search_client.upload_documents(documents=documents_to_upload)

    print("\nData successfully embedded and uploaded to Azure!")

if __name__ == "__main__":
    # 1. Ensure the index exists with the right schema
    setup_employee_index()
    
    # 2. Extract, embed, and upload the SQL data
    asyncio.run(embed_and_upload_employees())