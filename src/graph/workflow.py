from langgraph.graph import StateGraph, END
from src.core.state import AgentState
from src.graph.nodes import GraphNodes
from src.utils.logger import logger
from src.utils.constants import EXECUTIVE_DASHBOARD_QUERIES

class SQLOrchestrator:
    def __init__(self, nodes: GraphNodes):
        self.nodes = nodes
        self.graph = self.build_graph()

    def build_graph(self):
        workflow = StateGraph(AgentState)
        
        # 1. Define all valid nodes (Interceptor removed)
        workflow.add_node("guardrail", self.nodes.guardrail_node)     
        workflow.add_node("rewrite", self.nodes.rewrite_node)
        workflow.add_node("intent", self.nodes.intent_node)
        workflow.add_node("vector", self.nodes.vector_node)
        workflow.add_node("sql", self.nodes.sql_node)
        workflow.add_node("execute", self.nodes.execute_node)
        workflow.add_node("synthesize", self.nodes.synthesize_node)
        workflow.add_node("executive_overview", self.nodes.executive_overview_node)
        # 2. Set the Guardrail Agent as the TRUE Entry Point
        workflow.set_entry_point("guardrail")
        
        # 3. Guardrail Routing: If unsafe -> Synthesize (Bypass), If safe -> Rewrite
        def route_guardrail(state: AgentState):
            if state.get("category") == "security_block":
                return "fast_track"
            return "proceed_to_rewrite"
            
        workflow.add_conditional_edges(
            "guardrail", route_guardrail,
            {
                "fast_track": "synthesize",         
                "proceed_to_rewrite": "rewrite"    
            }
        )
        
        workflow.add_edge("rewrite", "intent")
        
        # 5. Intent Routing: Handles Greetings, Off-topic, or Database Queries
        def route_intent(state: AgentState):
            category = state.get("category", "database_query")
            if category in ["greeting", "vague_or_off_topic","security_block"]:
                return "fast_track"
            elif state.get("route") == "vague":
                return "vague"
            
            elif state.get("route") == "executive_overview":
                return "executive_overview"
            has_filters = any(slice_data.get("filters") for slice_data in state.get("intents", []))
            if has_filters:
                return "has_filters"
            return "no_filters"
            
        workflow.add_conditional_edges(
            "intent", route_intent,
            {
                "fast_track": "synthesize",
                "vague": "synthesize",
                "executive_overview": "executive_overview",
                "has_filters": "vector",
                "no_filters": "sql"
            }
        )

        # 6. Vector Routing 
        def route_vector(state: AgentState):
            if state.get("route") == "ambiguous":
                return "ambiguous_end" 
            return "sql"                
            
        workflow.add_conditional_edges(
            "vector", route_vector,
            {"ambiguous_end": END, "sql": "sql"}
        )
        
        # 7. Final Execution and Output Generation
        workflow.add_edge("executive_overview", "execute")
        workflow.add_edge("sql", "execute")
        workflow.add_edge("execute", "synthesize")
        workflow.add_edge("synthesize", END)

        return workflow.compile()
        
    async def invoke(self, state: dict):
        return await self.graph.ainvoke(state)