# import os
# import sqlite3
# import asyncio
# from typing import List, Dict
# import chromadb
# from langchain_openai import OpenAIEmbeddings
# from dotenv import load_dotenv
# import uuid

# load_dotenv()
# SQLITE_DB_PATH = "C:\KUMAR PRINCE\SMR_USE_CASES\hybrid_sql_rag_v4\data\Harmonia_DB.sqlite"  
# COLLECTION_NAME = "employee-master-collection" 
# CHROMA_DB_DIR = "./data/chroma-db-test"  
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# # def get_formatted_employee_records(table_name: str = "employee_master") -> List[Dict]:
# #     print(f"Extracting records from {table_name}...")
# #     records = []
    
# #     # Connect to the database
# #     conn = sqlite3.connect(SQLITE_DB_PATH)
# #     conn.row_factory = sqlite3.Row  
# #     cursor = conn.cursor()
    
# #     cursor.execute(f"SELECT * FROM {table_name}")
# #     rows = cursor.fetchall()
    
# #     noise_values = {"n/a", "not available", "", "none", "null"}
    
# #     date_columns = {
# #         "dateofbirth", 
# #         "employeejobstartdate", 
# #         "employeejobenddate", 
# #         "smg_hiredate", 
# #         "uploadeddate",
# #         "costcenter",
# #         "accountnumber",
# #         "payrollid"
# #     }
    
# #     for row in rows:
# #         row_dict = dict(row)
# #         kv_pairs = []
        
# #         # Iterate through every column in the row
# #         for col_name, value in row_dict.items():
# #             # 1. Skip integers and floats
# #             if isinstance(value, (int, float)):
# #                 continue
                
# #             # 2. Skip Date Fields
# #             if col_name.lower() in date_columns:
# #                 continue
                
# #             # 3. Skip Nulls and Empty Values
# #             if value is None:
# #                 continue
                
# #             # 4. Skip "N/A" and "Not Available" noise
# #             str_val = str(value).strip()
# #             if str_val.lower() in noise_values:
# #                 continue
                
# #             # Append to our Key-Value list
# #             kv_pairs.append(f"{col_name}: {str_val}")
            
# #         # Join all valid pairs into a single string
# #         key_value_string = ", ".join(kv_pairs)
        
# #         records.append({
# #             "GlobalUserId": str(row_dict.get("GlobalUserId", "UNKNOWN")),
# #             "FullName": str(row_dict.get("FullName", "UNKNOWN")),
# #             "TableName": table_name,
# #             "content": key_value_string
# #         })
        
# #     conn.close()
# #     print(f"Successfully processed {len(records)} employee records.")
# #     print("Records:",records[:20])
# #     return records

# def get_formatted_leave_records(table_name: str = "employee_leavetaken") -> List[Dict]:
#     print(f"Extracting records from {table_name}...")
#     records = []
    
#     conn = sqlite3.connect(SQLITE_DB_PATH)
#     conn.row_factory = sqlite3.Row  
#     cursor = conn.cursor()
    
#     cursor.execute(f"SELECT * FROM {table_name}")
#     rows = cursor.fetchall()
    
#     noise_values = {"n/a", "not available", "", "none", "null"}
    
#     for row in rows:
#         row_dict = dict(row)
#         kv_pairs = []
        
#         # We explicitly want these columns
#         target_columns = ["LeaveTypeName", "LeaveTypeCode", "LeaveReason", "Comments", "ApprovalStatus"]
        
#         for col_name in target_columns:
#             value = row_dict.get(col_name)
#             if value is None:
#                 continue
                
#             str_val = str(value).strip()
#             if str_val.lower() in noise_values:
#                 continue
                
#             kv_pairs.append(f"{col_name}: {str_val}")
            
#         key_value_string = ", ".join(kv_pairs)
        
#         # NOTE: You MUST have a GlobalUserId in this table to tie it to the employee!
#         user_id = str(row_dict.get("GlobalUserId", "UNKNOWN"))
        
#         # Prepend context so the AI knows what this data is
#         content_text = f"Leave Record for Employee {user_id} -> {key_value_string}"
        
#         records.append({
#             "GlobalUserId": user_id,
#             "TableName": table_name,
#             "content": content_text
#         })
        
#     conn.close()
#     print(f"Successfully processed {len(records)} leave records.")
#     return records


# # async def embed_and_upload_employees():
# #     records = get_formatted_employee_records()
    
# #     print("Initializing Embedder and ChromaDB Client...")
# #     embedder = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_API_KEY)
    
# #     # Initialize ChromaDB (Persistent storage to the specified directory)
# #     chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    
# #     collection = chroma_client.get_or_create_collection(
# #         name=COLLECTION_NAME,
# #         metadata={"hnsw:space": "cosine"} 
# #     )

# #     # Batching arrays for ChromaDB
# #     ids_batch = []
# #     documents_batch = []
# #     metadatas_batch = []
# #     embeddings_batch = []
    
# #     BATCH_SIZE = 200
# #     total_uploaded = 0
    
# #     print(f"Generating embeddings and uploading in batches of {BATCH_SIZE}...")
    
# #     for i, record in enumerate(records):
# #         content_text = record["content"]
        
# #         # Skip if the row was entirely empty/N/A
# #         if not content_text:
# #             continue
            
# #         # Generate embedding vector asynchronously
# #         content_vector = await embedder.aembed_query(content_text)
        
# #         # We use GlobalUserId as the unique document ID. If unavailable, use row index.
# #         doc_id = record["GlobalUserId"] if record["GlobalUserId"] != "UNKNOWN" else f"row_{i}"
        
# #         ids_batch.append(doc_id)
# #         documents_batch.append(content_text)
# #         metadatas_batch.append({
# #             "GlobalUserId": record["GlobalUserId"],
# #             "FullName": record["FullName"],
# #             "TableName": record["TableName"]
# #         })
# #         embeddings_batch.append(content_vector)
        
# #         # Batch Upload Logic
# #         if len(ids_batch) >= BATCH_SIZE:
# #             print(f" -> Upserting batch of {BATCH_SIZE} records...")
# #             # We use upsert() so running this script multiple times safely updates records instead of crashing
# #             collection.upsert(
# #                 ids=ids_batch,
# #                 embeddings=embeddings_batch,
# #                 metadatas=metadatas_batch,
# #                 documents=documents_batch
# #             )
# #             total_uploaded += len(ids_batch)
            
# #             # Reset batches
# #             ids_batch.clear()
# #             documents_batch.clear()
# #             metadatas_batch.clear()
# #             embeddings_batch.clear()

# #     # Upload any remaining documents in the final partial batch
# #     if ids_batch:
# #         print(f" -> Upserting final batch of {len(ids_batch)} records...")
# #         collection.upsert(
# #             ids=ids_batch,
# #             embeddings=embeddings_batch,
# #             metadatas=metadatas_batch,
# #             documents=documents_batch
# #         )
# #         total_uploaded += len(ids_batch)

# #     print(f"\nSuccess! Embedded and uploaded {total_uploaded} total records to ChromaDB collection: '{COLLECTION_NAME}'")

# async def embed_and_upload_records(records: List[Dict]):
#     print("Initializing Embedder and ChromaDB Client...")
#     embedder = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_API_KEY)
    
#     chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
#     collection = chroma_client.get_or_create_collection(
#         name=COLLECTION_NAME, 
#         metadata={"hnsw:space": "cosine"} 
#     )

#     BATCH_SIZE = 500
#     total_uploaded = 0
    
#     valid_records = [r for r in records if r["content"].strip()]
    
#     print(f"Generating embeddings concurrently in batches of {BATCH_SIZE}...")
    
#     for i in range(0, len(valid_records), BATCH_SIZE):
#         batch = valid_records[i:i + BATCH_SIZE]
        
#         print(f" -> Fetching {len(batch)} embeddings from OpenAI concurrently...")
#         tasks = [embedder.aembed_query(record["content"]) for record in batch]
#         embeddings_batch = await asyncio.gather(*tasks)
        
#         ids_batch = []
#         documents_batch = []
#         metadatas_batch = []
        
#         for record in batch:
#             unique_doc_id = f"{record['TableName']}_{record['GlobalUserId']}_{uuid.uuid4().hex[:8]}"
            
#             ids_batch.append(unique_doc_id)
#             documents_batch.append(record["content"])
#             metadatas_batch.append({
#                 "GlobalUserId": record["GlobalUserId"],
#                 "TableName": record["TableName"],
#             })
            
#         print(f" -> Upserting batch of {len(batch)} records to ChromaDB...")
#         collection.upsert(
#             ids=ids_batch,
#             embeddings=embeddings_batch,
#             metadatas=metadatas_batch,
#             documents=documents_batch
#         )
#         total_uploaded += len(batch)

#     print(f"\nSuccess! Embedded and uploaded {total_uploaded} records to '{COLLECTION_NAME}'")

# # if __name__ == "__main__":
# #     # Start the async extraction, embedding, and ingestion pipeline
# #     asyncio.run(embed_and_upload_employees())

# if __name__ == "__main__":
#     # 1. Get the leave records
#     leave_records = get_formatted_leave_records()
    
#     # 2. Append them to the existing collection
#     asyncio.run(embed_and_upload_records(leave_records))

import os
import sqlite3
import asyncio
from typing import List, Dict
import chromadb
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

SQLITE_DB_PATH = r"C:\KUMAR PRINCE\SMR_USE_CASES\hybrid_sql_rag_v4\data\Harmonia_DB.sqlite"  
COLLECTION_NAME = "employee-master-collection" 
CHROMA_DB_DIR = "./data/chroma-db-test"  
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_distinct_column_values(table_name: str, target_columns: List[str]) -> List[Dict]:
    print(f"Extracting DISTINCT records from {table_name}...")
    records = []
    
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    noise_values = {"n/a", "not available", "", "none", "null"}
    
    for col in target_columns:
        print(f" -> Querying distinct values for column: {col}")
        cursor.execute(f"SELECT DISTINCT {col} FROM {table_name}")
        rows = cursor.fetchall()
        
        for row in rows:
            val = row[0]
            
            # Filter out Nulls and Noise
            if val is None: 
                continue
                
            str_val = str(val).strip()
            if str_val.lower() in noise_values: 
                continue
                
            # Create the exact Key-Value string format
            kv_string = f"{col}: {str_val}"
            
            # Generate a safe, unique Composite ID 
            safe_val_id = str_val.replace(" ", "_").replace("/", "_")
            doc_id = f"{table_name}_{col}_{safe_val_id}"
            
            records.append({
                "DocId": doc_id,
                "TableName": table_name,
                "ColumnName": col,
                "OriginalValue": str_val,
                "content": kv_string
            })
            
    conn.close()
    print(f"Successfully processed {len(records)} distinct categorical records.\n")
    return records


async def embed_and_upload_distinct_values():
    TARGET_TABLE = "employee_inouttime"
    TARGET_COLUMNS = ["AttendanceType", "AttendanceStatus", "ApproverName"]
    
    records = get_distinct_column_values(TARGET_TABLE, TARGET_COLUMNS)
    
    if not records:
        print("No valid records found to upload.")
        return

    print("Initializing Embedder and ChromaDB Client...")
    embedder = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_API_KEY)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    
    # Opens your existing unified collection safely
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"} 
    )

    ids_batch, documents_batch, metadatas_batch, embeddings_batch = [], [], [], []
    BATCH_SIZE = 100 
    total_uploaded = 0
    
    print(f"Generating embeddings and uploading...")
    
    for record in records:
        content_text = record["content"]
        
        content_vector = await embedder.aembed_query(content_text)
        
        ids_batch.append(record["DocId"])
        documents_batch.append(content_text)
        
        # ==========================================
        # PURE METADATA IMPLEMENTATION
        # ==========================================
        pure_metadata = {
            "TableName": record["TableName"],
            "ColumnName": record["ColumnName"]
        }
        
        # Dynamically inject the exact column name and value 
        # Example: {"AttendanceStatus": "Present"}
        pure_metadata[record["ColumnName"]] = record["OriginalValue"]

        metadatas_batch.append(pure_metadata)
        embeddings_batch.append(content_vector)
        
        if len(ids_batch) >= BATCH_SIZE:
            collection.upsert(
                ids=ids_batch, embeddings=embeddings_batch, 
                metadatas=metadatas_batch, documents=documents_batch
            )
            total_uploaded += len(ids_batch)
            ids_batch.clear(); documents_batch.clear(); metadatas_batch.clear(); embeddings_batch.clear()

    if ids_batch:
        collection.upsert(
            ids=ids_batch, embeddings=embeddings_batch, 
            metadatas=metadatas_batch, documents=documents_batch
        )
        total_uploaded += len(ids_batch)

    print(f"Success! Appended {total_uploaded} distinct values to '{COLLECTION_NAME}'.")

if __name__ == "__main__":
    asyncio.run(embed_and_upload_distinct_values())