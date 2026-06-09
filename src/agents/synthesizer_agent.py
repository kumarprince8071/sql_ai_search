import json
from src.base.base_llm import BaseLLM
from src.prompts.prompt_registry import SYNTHESIZER_SYSTEM_PROMPT
from src.schemas.pydantic_models import DashboardResponse  # Import the new schema
from src.utils.logger import logger
from src.utils.latency_tracker import measure_latency

class SynthesizerAgent:
    """Transforms raw JSON data results into human-readable answers and UI dashboards."""

    def __init__(self, llm_client: BaseLLM):
        self.llm = llm_client


    @measure_latency
    async def __call__(self, state: dict) -> dict:
        logger.info("Synthesizer Agent: Formatting final response and dashboard...")
        
        current_query = state.get("current_query", "")
        raw_db_results = state.get("raw_db_results", [])
        
        if not raw_db_results:
            return {
                "response_type": "text",
                "final_response": "I successfully ran the query, but no records were found for those filters."
            }

        # 2. Data Sampling: Grab the first 20 records
        sampled_data = raw_db_results[:20]
        total_rows = len(raw_db_results)
        
        # 3. Format the User Prompt with the JSON sample
        user_prompt = (
            f"USER QUERY: {current_query}\n\n"
            f"TOTAL RECORDS FOUND: {total_rows}\n"
            f"DATA SAMPLE (Top {len(sampled_data)} rows):\n"
            f"{json.dumps(sampled_data, indent=2)}\n\n"
            f"Based on this data sample, configure the UI layout. Extract KPIs, "
            f"determine if a chart is needed based on the rules, and write your insights."
        )
        
        try:
            # 4. Execute the LLM call with strict Pydantic enforcement
            response: DashboardResponse = await self.llm.generate_structured(
                system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                schema_class=DashboardResponse
            )
            
            # 5. Format the output to update the LangGraph state
            is_dash = response.is_dashboard
            
            return {
                "response_type": "dashboard" if is_dash else "text",
                "final_response": response.text_response,
                # Dump the Pydantic model into a dict so the API can safely parse it
                "dashboard_payload": response.model_dump() if is_dash else None
            }

        except Exception as e:
            logger.error(f"Synthesizer Error: Failed to generate structured response: {e}", exc_info=True)
            return {
                "response_type": "text",
                "final_response": "I fetched the data successfully, but encountered an error while formatting the dashboard."
            }
