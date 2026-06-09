from src.base.base_llm import BaseLLM
from src.prompts.prompt_registry import QUERY_REWRITER_PROMPT
from src.core.memory_manager import MemoryManager
from src.utils.logger import logger
from src.utils.latency_tracker import measure_latency

class QueryRewriterAgent:
    """Refinement engine that transforms ambiguous user inputs into fully contextual queries."""

    def __init__(self, llm_client: BaseLLM):
        self.llm = llm_client

    @measure_latency
    async def __call__(self, current_query: str, history: list) -> str:
        logger.info("Query Rewriter: Rewriting Query Provided From User")
        trimmed_history = MemoryManager.trim_history(history)
        try:
            response_text = await self.llm.generate_text(
                system_prompt=QUERY_REWRITER_PROMPT,
                user_prompt=f"Current Query: {current_query}",
                history=trimmed_history
            )
            rewritten_query = response_text.strip()
            logger.info(f"Query Rewriter:Enhanced Rewritten Query -> '{rewritten_query}'")
            return rewritten_query

        except Exception as e:
            logger.error(f"Query Rewriter Error: {e}. Falling back to raw query.")
            return current_query