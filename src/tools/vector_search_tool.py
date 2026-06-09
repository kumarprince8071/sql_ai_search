import math
import re
import asyncio
from typing import Any, Tuple
from difflib import SequenceMatcher
from src.base.base_vector_db import BaseVectorDB
from src.base.base_rdbms import BaseRDBMS
from src.utils.logger import logger
from src.utils.schema_loader import SchemaManager
from src.core.exceptions import EntityAmbiguousError
from src.utils.latency_tracker import measure_latency

def normalize_key(key: str) -> str:
    """Normalizes the key from the filters value """

    return re.sub(r"[^a-z0-9]", "", key.lower())

def label_to_camel_case(label: str) -> str:
    """ converts the labels to camel case """

    return "".join(word.capitalize() for word in label.split("_"))

class VectorSearchTool:
    """Translates natural language entity names into exact database column matches using ChromaDB."""

    def __init__(self, vector_client: BaseVectorDB, rdbms_client: BaseRDBMS, schema_manager: SchemaManager):
        self.vector_client = vector_client
        self.rdbms = rdbms_client
        self.schema_manager = schema_manager
        self.MIN_SIMILARITY_SCORE = 0.35
        self.AMBIGUITY_MARGIN = 0.02
        self.MIN_LABEL_FIELD_SIMILARITY = 0.6


    def extract_business_fields(self, doc: dict) -> dict:
        """Extracts valid column names and values, dropping empty data."""

        return {k: v for k, v in doc.items() if v is not None and str(v).strip() != ""}

    def calculate_cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """calculates the cosine similarity """

        dot_product = sum(p * q for p, q in zip(vec1, vec2))
        norm_a = math.sqrt(sum(p * p for p in vec1))
        norm_b = math.sqrt(sum(q * q for q in vec2))
        if not norm_a or not norm_b: return 0.0
        return dot_product / (norm_a * norm_b)

    async def resolve_column_semantically(self, entity_label: str, metadata: dict) -> str | None:
        """uses the cosine similarity to match the column names """

        business_fields = self.extract_business_fields(metadata)
        available_columns = list(business_fields.keys())
        if not available_columns: return None            
        try:
            label_vector = await self.vector_client.embedder.aembed_query(entity_label)            
            column_vectors = await self.vector_client.embedder.aembed_documents(available_columns)
            
            best_column = None
            max_similarity = -1.0          
            for col_name, col_vector in zip(available_columns, column_vectors):
                similarity = self.calculate_cosine_similarity(label_vector, col_vector)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_column = col_name            
                    
            if best_column:
                return best_column
                
        except Exception as e:
            logger.error(f"Vector-based dynamic column resolution failed: {e}", exc_info=True)
        return None

    def match_field_by_label(self, entity_label: str, metadata: dict) -> tuple[str | None, str | None, float]:
        """match the key based on the semantic json schema """

        _, deterministic_col, _ = self.schema_manager.find_column_by_alias(entity_label)
        if deterministic_col:
            for k, v in metadata.items():
                if k.lower() == deterministic_col.lower():
                    return k, v, 1.000  
            return deterministic_col, None, 0.0
        
        business_fields = self.extract_business_fields(metadata)
        if not business_fields: return None, None, 0.0
            
        normalized_label = normalize_key(entity_label)
        best_field, best_value, best_score  = None, None, 0.0
        
        for field_name, field_value in business_fields.items():
            normalized_field = normalize_key(field_name)
            score = SequenceMatcher(None, normalized_label, normalized_field).ratio()
            if score > best_score:
                best_score, best_field, best_value = score, field_name, field_value
                
        return best_field, best_value, best_score

    def is_numerical_condition(self, raw_value: str) -> bool:
        """finds if the value is numerical"""

        val_str = str(raw_value).strip()
        return any(val_str.startswith(op) for op in [">=", "<=", ">", "<", "="]) or val_str.isdigit()

    def parse_numerical_sql(self, entity_label: str, raw_value: str, column_name: str, table_name: str) -> str:
        """Instantly translates the LLM's normalized math string into a SQL fragment."""

        value_str = str(raw_value).strip()
        table_prefix = f"{table_name}." if table_name else ""
        match = re.match(r"^(>=|<=|>|<|=)?\s*([\d.]+)", value_str)
        if match:
            operator = match.group(1) or "="
            number = match.group(2)
            return f"{table_prefix}{column_name} {operator} {number}"            
        safe_val = value_str.replace("'", "''")
        return f"{table_prefix}{column_name} = '{safe_val}'"
    
    @measure_latency
    async def process_single_filter(self, entity_label: str, raw_value: Any, route: str) -> Tuple[str, str]:
        """ this method process the values provided in the filter parallelly against vector db and SQL based on the route"""

        raw_value_str = str(raw_value).strip()
        def generate_fallback():
            logger.warning(f"'{raw_value_str}' bypassed vector validation. Falling back to SQL mapping.")
            safe_val = str(raw_value_str).replace("'", "''")
            if any(kw in entity_label.lower() for kw in ["date", "time", "year", "month", "day"]):
                return f"{entity_label} = '{safe_val}'"
            if route == "aggregation":
                return f"{entity_label} LIKE '%{safe_val}%'"
            return f"{entity_label} = '{safe_val}'"

        try:

            is_date_col = any(kw in entity_label.lower() for kw in ["date", "time", "year", "month", "day"])
            is_json_dict = raw_value_str.startswith("{") and "}" in raw_value_str
            is_date_format = bool(re.search(r"\d{4}-\d{2}-\d{2}", raw_value_str))
            
            if is_date_col or is_json_dict or is_date_format:
                logger.info(f"[VectorSearch] Bypassing Vector DB for Date/JSON filter: {raw_value_str}")
                dt_table, dt_col, _ = self.schema_manager.find_column_by_alias(entity_label)                
                column_name = dt_col if dt_col else label_to_camel_case(entity_label)
                table_prefix = f"{dt_table}." if dt_table else ""                
                safe_val = raw_value_str.replace("'", "''")
                return entity_label, f"{table_prefix}{column_name} = '{safe_val}'"
            
            # 1. Numeric Bypass & Contextual Anchoring
            if isinstance(raw_value, (int, float)) or self.is_numerical_condition(raw_value_str):
                dt_table, dt_col, _ = self.schema_manager.find_column_by_alias(entity_label)                
                column_name = dt_col if dt_col else label_to_camel_case(entity_label)       
                target_table = dt_table if dt_table else None      
                return entity_label, self.parse_numerical_sql(entity_label, raw_value_str, column_name, target_table)
            
            dt_table, dt_col, _ = self.schema_manager.find_column_by_alias(entity_label)
            target_table = dt_table if dt_table else None
            search_query = f"{dt_col}: {raw_value_str}" if dt_col else raw_value_str
            print("search_query",search_query)
            # Vector Search
            standardized_results = await self.vector_client.search(
                query_text=search_query,
                target_table=target_table, 
                top_k=5
            )          
            if not standardized_results:
                return entity_label, generate_fallback()
                
            top_hit = standardized_results[0]
            
            # if top_hit["score"] < self.MIN_SIMILARITY_SCORE: 
            #     return entity_label, generate_fallback() 
            word_count = len(raw_value_str.split())
            dynamic_threshold = self.MIN_SIMILARITY_SCORE
            
            if word_count <= 2:
                dynamic_threshold = dynamic_threshold * 0.85 
                logger.info(f"Short query detected. Relaxed threshold to {dynamic_threshold:.2f}")

            if top_hit["score"] < dynamic_threshold: 
                logger.warning(f"Vector search score {top_hit['score']:.2f} failed threshold {dynamic_threshold:.2f}. Triggering fallback.")
                return entity_label, generate_fallback()
                
            matched_field, stored_value, label_score = self.match_field_by_label(entity_label, top_hit["metadata"])
            
            if not target_table:
                table, _, _ = self.schema_manager.find_column_by_alias(column_name)
                target_table = table if table else "UNKNOWN_TABLE"
                
            column_name = matched_field
            if label_score < self.MIN_LABEL_FIELD_SIMILARITY:
                value_match_found = False
                
                # 1. Check if the value is inside the matched column in METADATA
                if column_name and column_name in top_hit["metadata"]:
                    priority_val = top_hit["metadata"].get(column_name, "")
                    stored_value = priority_val
                    value_match_found = True

                if column_name and not value_match_found:
                    match = re.search(rf"{column_name}:\s*([^,]+)", top_hit.get("content", ""), re.IGNORECASE)
                    if match:
                        extracted_val = match.group(1).strip()
                        
                        is_substring = str(raw_value_str).lower() in extracted_val.lower()
                        
                        word_exists_in_doc = bool(re.search(rf"\b{re.escape(str(raw_value_str))}\b", top_hit.get("content", ""), re.IGNORECASE))
                        
                        if is_substring or word_exists_in_doc:
                            stored_value = extracted_val
                            value_match_found = True

                # 3. Check if the value exists in ANY other metadata column (as a backup)
                if not value_match_found:
                    for k, v in top_hit["metadata"].items():
                        if str(raw_value_str).lower() in str(v).lower():
                            column_name = k
                            stored_value = v
                            value_match_found = True
                            break

                # 4. Stop Semantic Hijacking
                if not value_match_found:
                    if column_name:
                        stored_value = raw_value_str
                    else:
                        dynamic_col = await self.resolve_column_semantically(entity_label, top_hit["metadata"])                
                        if dynamic_col:
                            column_name = dynamic_col
                            stored_value = raw_value_str 
                        else:
                            column_name = label_to_camel_case(entity_label)
                            stored_value = raw_value_str
            # 3. AMBIGUITY CHECK

            if route != "aggregation" and len(standardized_results) > 1: 
                distinct_matches = []
                seen_values = set()
                exact_match_found = False
                
                for res in standardized_results:
                    if (top_hit["score"] - res["score"]) <= self.AMBIGUITY_MARGIN:
                        _, val, _ = self.match_field_by_label(entity_label, res["metadata"])
                        
                        if val is not None:
                            val_lower = str(val).lower()
                            
                            # 3. EXACT MATCH SHORT-CIRCUIT: If the user typed exactly what is in the DB, it's not ambiguous.
                            if val_lower == str(raw_value_str).lower():
                                stored_value, exact_match_found = val, True
                                break
                            
                            if val_lower not in seen_values:
                                seen_values.add(val_lower)
                                display_str = str(val)
                                if res["id"]: display_str += f" (ID: {res['id']})"
                                distinct_matches.append(display_str)
                    else:
                        break  
                        
                if not exact_match_found and len(distinct_matches) > 1:
                    raise EntityAmbiguousError(f"Multiple distinct matches found.", options=distinct_matches[:5])
                    
            final_value = stored_value if stored_value is not None else raw_value_str            
            safe_value = str(final_value).replace("'","''")
            
            if route == "aggregation":
                if "id" in column_name.lower(): sql_fragment = f"{target_table}.{column_name} = '{safe_value}'"
                else: sql_fragment = f"{target_table}.{column_name} LIKE '%{safe_value}%'"
            else:
                sql_fragment = f"{target_table}.{column_name} LIKE '{safe_value}'"                
                
            return entity_label, sql_fragment

        except EntityAmbiguousError:
            raise
        except Exception as e:
            logger.error(f"Error processing filter '{entity_label}': {e}", exc_info=True)
            return entity_label, generate_fallback()

    async def validate_filters(self, raw_filters: dict, route: str = None) -> dict:
        """method to validate the values in list of values against vector db"""
        
        if not raw_filters: return {}
        logger.info(f"[VectorSearch] Validating {len(raw_filters)} filters concurrently")
        
        async def process_key(label: str, value: Any) -> Tuple[str, str]:
            if isinstance(value, list):
                sub_tasks = [self.process_single_filter(label, item, route) for item in value]
                sub_results = await asyncio.gather(*sub_tasks, return_exceptions=False)
                fragments = [res[1] for res in sub_results]
                return label, f"({' OR '.join(fragments)})"
            else:
                return await self.process_single_filter(label, value, route)
                
        tasks = [process_key(entity_label, raw_value) for entity_label, raw_value in raw_filters.items()]        
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return {label: sql_fragment for label, sql_fragment in results}
    
