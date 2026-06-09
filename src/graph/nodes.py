import asyncio
import pandas as pd
from src.core.state import AgentState
from src.utils.logger import logger
from src.core.exceptions import EntityAmbiguousError
from src.utils.constants import EXECUTIVE_DASHBOARD_QUERIES

class GraphNodes:
    """Wraps agent and tool executions into LangGraph-compatible node functions."""

    def __init__(self, query_rewriter, intent_agent, sql_agent, synthesizer, vector_tool, pandas_tool, db_client, guardrail_agent):
        self.query_rewriter = query_rewriter
        self.intent_agent = intent_agent
        self.sql_agent = sql_agent
        self.synthesizer = synthesizer
        self.vector_tool = vector_tool
        self.pandas_tool = pandas_tool
        self.db_client = db_client
        self.guardrail_agent = guardrail_agent

    async def rewrite_node(self, state: AgentState):
        query = await self.query_rewriter(state["current_query"], state.get("messages", []))
        return {"current_query": query}

    async def intent_node(self, state: AgentState):
        return await self.intent_agent(state)

    async def vector_node(self, state: AgentState):
        logger.info("Vector Node: Validating entities across all data slices...")
        try:
            processed_intents = []
            for slice_data in state.get("intents", []):
                raw_filters = slice_data.get("filters", {})
                logger.info(f"Intent Agent extracted these filters: {raw_filters}")
                if raw_filters:
                    validated = await self.vector_tool.validate_filters(raw_filters, state.get("route"))
                    slice_data["validated_schema"] = validated
                else:
                    slice_data["validated_schema"] = {}
                processed_intents.append(slice_data)

            return {"intents": processed_intents}

        except EntityAmbiguousError as e:
            logger.warning(f"Ambiguity detected: {e.message}")
            return {
                "final_response": "I found multiple matches for your search. Could you please specify which one you mean?",
                "route": "ambiguous",
                "response_type": "clarification",
                "clarification_options": e.options[:5],
                "intents": []
            }

    async def sql_node(self, state: AgentState):
        return await self.sql_agent(state)
    
    async def executive_overview_node(self, state: AgentState):
        logger.info("Executive Overview Node: Injecting default dashboard queries.")
        return {
            "sql_queries": EXECUTIVE_DASHBOARD_QUERIES,
            "is_default_dashboard": True,
            "route": "executive_overview",
            "category": "database_query",
        }
    
    async def execute_node(self, state: AgentState):
        logger.info("Execution Node: Running queries...")
        queries = state.get("sql_queries", [])
        raw_results = []

        # 1. Fetch data from SQLite concurrently
        tasks = [self.db_client.execute_query(q["sql"]) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"SQL Execution Error: {res}")
                continue            
            query_def = queries[i]
            pandas_code = query_def.get("pandas_code")
            if pandas_code and res:
                logger.info(f"Execution Node: Applying Pandas math to query '{query_def.get('name')}'...")
                import pandas as pd
                df = pd.DataFrame(res)
                processed_data = await self.pandas_tool.execute_custom_math(df, pandas_code)
                raw_results.extend(processed_data)
            else:
                raw_results.extend(res)

        return {"raw_db_results": raw_results, "pandas_results": []}

    async def guardrail_node(self, state: AgentState):
        user_query = state.get("current_query", "")
        safety_check = await self.guardrail_agent(user_query)

        if not safety_check.is_safe:
            logger.warning(f"Guardrail triggered! Blocked query. Reason: {safety_check.reason}")
            return {
                "category": "security_block",
                "response_type": "blocked",
                "final_response": "I cannot process this request as it violates our security and safety guidelines."
            }

        logger.info("Guardrail Node: Query passed safety checks.")
        return {}

    async def synthesize_node(self, state: AgentState):
        response_type = state.get("response_type")

        if response_type in ("blocked", "clarification"):
            return {}

        category = state.get("category", "database_query")
        
        if category in ("greeting", "vague_or_off_topic"):
            logger.info(f"Synthesize Node: Fast-tracking conversational response for '{category}'")
            return {
                "final_response": state.get("direct_response") or "Hello! How can I help you with the data today?",
                "response_type": "text",
                "dashboard_payload": None
            }

        logger.info("Synthesize Node: Synthesizing database results...")
        result = await self.synthesizer(state)

        payload = result.get("dashboard_payload")
        result["response_type"] = "dashboard" if payload and payload.get("is_dashboard") else "text"
        return result