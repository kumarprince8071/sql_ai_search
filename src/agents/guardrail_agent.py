from src.base.base_llm import BaseLLM
from src.schemas.pydantic_models import GuardrailSchema
from src.prompts.prompt_registry import GUARDRAIL_SYSTEM_PROMPT
from src.utils.logger import logger

class GuardrailAgent:
    """Evaluates user queries for prompt injection, toxicity, and malicious intent."""

    def __init__(self, llm_client: BaseLLM):
        self.llm = llm_client

    async def __call__(self, user_query: str) -> GuardrailSchema:
        logger.info("[GuardrailAgent] Scanning query for security threats")
        
        try:
            # We enforce structured output using the base LLM client
            result = await self.llm.generate_structured(
                system_prompt=GUARDRAIL_SYSTEM_PROMPT,
                user_prompt=user_query,
                schema_class=GuardrailSchema
            )
            return result
        except Exception as e:
            logger.error(f"[GuardrailAgent] Error during safety check: {e}")
            # Fail-safe: If the guardrail crashes, block the query to be safe.
            return GuardrailSchema(is_safe=False, reason="Internal security scan failed.")