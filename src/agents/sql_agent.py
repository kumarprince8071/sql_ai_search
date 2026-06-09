from src.base.base_llm import BaseLLM
from src.base.base_rdbms import BaseRDBMS
from src.schemas.pydantic_models import SQLContract
from src.prompts.prompt_registry import SQL_SYSTEM_PROMPT
from src.utils.logger import logger
from src.utils.schema_loader import SchemaManager
from src.utils.latency_tracker import measure_latency
from src.base.base_vector_db import BaseVectorDB

class SQLAgent:
    """Generates precise SQL queries based on database schema, validated intent, and semantic hints."""

    def __init__(self, llm_client: BaseLLM, db_client: BaseRDBMS, schema_manager: SchemaManager,vector_client:BaseVectorDB):
        self.llm = llm_client
        self.db = db_client
        self.schema_manager = schema_manager  
        self.vector_client = vector_client

    @measure_latency
    async def __call__(self, state):
        logger.info("SQL Agent: Drafting SQL queries...")
        current_query = state.get("current_query", "")
        semantic_schema = self.schema_manager.get_sql_context()
        dynamic_examples = await self.vector_client.fetch_few_shot_examples(current_query)
        if dynamic_examples:
            logger.info("SQL Agent: Successfully injected dynamic few-shot examples.")
        intent_blocks = []
        for idx, slice_data in enumerate(state.get("intents", [])):
            filters = slice_data.get("validated_schema") or slice_data.get("filters") or {}
            if filters:
                # Extract ONLY the values (the pre-written SQL fragments)
                filter_str = "\n".join([f"- {v}" for v in filters.values()])
                instruction = "CRITICAL: You MUST use these exact VALIDATED SQL FRAGMENTS in your WHERE clause. Do NOT alter the strings or invent your own."
            else:
                filter_str = "None"
                instruction = ""
            
            block = (f"--- DATA SLICE {idx+1} ---\n"
                     f"METRIC: {slice_data.get('metric')}\n"
                     f"GROUP BY: {slice_data.get('group_by')}\n"
                     f"{instruction}\n"
                     f"VALIDATED FILTERS:\n{filter_str}")
            intent_blocks.append(block)

        system_prompt = SQL_SYSTEM_PROMPT.format(
            semantic_schema=semantic_schema
        )
        
        # The prompt forces the LLM to generate one query per slice
        user_prompt = (
            f"TASK: {state['current_query']}\n\n"
            f"{dynamic_examples}\n"
            f"The user request has been parsed into the following distinct data slices. "
            f"Generate one independent SQL query for EACH data slice below:\n\n"
            + "\n\n".join(intent_blocks)
        )
        try:
            response: SQLContract = await self.llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema_class=SQLContract
            )

            logger.info(f"SQL Agent: Generated {len(response.queries)} queries.")
            return {"sql_queries": [q.model_dump() for q in response.queries]}

        except Exception as e:
            logger.error(f"SQL Agent Error: {e}", exc_info=True)
            return {"final_response": "I encountered an error while generating the database query."}