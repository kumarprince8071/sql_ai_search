from datetime import datetime
from src.base.base_llm import BaseLLM
from src.base.base_rdbms import BaseRDBMS
from src.schemas.pydantic_models import IntentValidation
from src.prompts.prompt_registry import INTENT_SYSTEM_PROMPT
from src.core.memory_manager import MemoryManager
from src.utils.logger import logger
from src.utils.schema_loader import SchemaManager
from src.utils.latency_tracker import measure_latency

class IntentAgent:
    """Analyzes user intent and produces a structured routing contract."""

    def __init__(self, llm_client: BaseLLM,schema_manager:SchemaManager):
        self.llm = llm_client
        self.schema_manager = schema_manager  
    @measure_latency
    async def __call__(self, state):
        logger.info("Intent Agent: Analyzing query intent")
        try:
            semantic_schema = self.schema_manager.get_intent_context()
        except Exception as e:
            logger.error(f"Intent Agent Schema Fetch Error: {str(e)}", exc_info=True)
            semantic_schema = "Schema not available."
        trimmed_history = MemoryManager.trim_history(state.get("messages", []))
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_prompt = INTENT_SYSTEM_PROMPT.format(current_time=current_time, semantic_schema=semantic_schema)

        try:
            response: IntentValidation = await self.llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=state["current_query"],
                schema_class=IntentValidation,
                # history=trimmed_history
            )

            logger.info(f"Intent Agent: Route determined -> {response.route}")
            category_val = response.category.value if hasattr(response.category, "value") else response.category
            
            return {
                "category": category_val,
                "direct_response": response.direct_response,
                "route": response.route,
                "requires_pandas": response.requires_pandas,
                "top_n": response.top_n,
                "intents": [slice_data.model_dump() for slice_data in response.intents] 
            }

        except Exception as e:
            logger.error(f"Intent Agent Error: {str(e)}", exc_info=True)
            return {"route": "vague", "final_response": "I'm sorry, I couldn't process that request."}