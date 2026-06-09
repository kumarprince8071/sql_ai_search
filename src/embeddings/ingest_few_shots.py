import os
import json
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

def ingest_new_few_shots(file_path: str, persist_directory: str = "C:\KUMAR PRINCE\SMR_USE_CASES\sql_agent\src\data\chroma-db-test"):
    print(f"Reading new examples from {file_path}...")
    
    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    blocks = raw_text.split('USER QUERY:')[1:]
    
    examples = []
    for i, block in enumerate(blocks):
        try:
            # Extract the User Query
            query_part, rest = block.split('RESOLVED FILTERS:', 1)
            # .strip().strip('"') removes spaces and the surrounding quotes from the string
            user_query = query_part.strip().strip('"')
            
            # Extract Filters and Output
            filters_part, output_part = rest.split('OUTPUT:', 1)
            filters_json_str = filters_part.strip()
            
            # Extract the SQL string from the Output JSON array
            output_json = json.loads(output_part.strip())
            sql_string = output_json[0]["sql"]
            
            examples.append({
                "id": f"sql_shot_v2_{i}",  # Tagged v2 for clean upserts
                "user_query": user_query,
                "filters": filters_json_str,
                "sql": sql_string
            })
        except Exception as e:
            print(f"Failed to parse block {i}. Error: {e}")

    print(f"Successfully parsed {len(examples)} examples. Initializing ChromaDB...")

    # 2. Initialize ChromaDB
    chroma_client = chromadb.PersistentClient(path=persist_directory)
    
    # IMPORTANT: Ensure this matches the embedding model your SQL Agent uses
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small" 
    )

    # Create or connect to the dedicated few-shot collection
    collection = chroma_client.get_or_create_collection(
        name="sql_few_shots",
        embedding_function=openai_ef
    )

    # 3. Embed into the Vector Database using UPSERT
    collection.upsert(
        documents=[ex["user_query"] for ex in examples], 
        metadatas=[{"filters": ex["filters"], "sql": ex["sql"]} for ex in examples], 
        ids=[ex["id"] for ex in examples]
    )

    print(f"Success! {len(examples)} new few-shot examples embedded into ChromaDB.")

if __name__ == "__main__":
    ingest_new_few_shots(r"C:\KUMAR PRINCE\SMR_USE_CASES\sql_agent\src\prompts\few_shot_examples.md")