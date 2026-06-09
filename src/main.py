import asyncio
from src.utils.config import Config
from src.clients.llms.openai_client import OpenAIClient
from src.agents.query_rewriter_agent import QueryRewriterAgent
from src.agents.intent_agent import IntentAgent
from src.agents.sql_agent import SQLAgent
from src.agents.synthesizer_agent import SynthesizerAgent
from src.tools.vector_search_tool import VectorSearchTool
from src.tools.pandas_analyzer_tool import PandasAnalyzerTool
from src.graph.nodes import GraphNodes
from src.graph.workflow import SQLOrchestrator
from src.utils.schema_loader import SchemaManager
from src.utils.route_client import VectorDBProvider,RDBMSProvider
from src.agents.guardrail_agent import GuardrailAgent

async def main():
    
    # Initializing  Dependencies
    llm_client = OpenAIClient(model_name=Config.LLM_MODEL)
    schema_manager = SchemaManager()
    vector_client = VectorDBProvider.get_vector_client()
    db_client = RDBMSProvider.get_rdbms_client()
    guardrail_agent = GuardrailAgent(llm_client)
    query_rewriter = QueryRewriterAgent(llm_client)
    intent_agent = IntentAgent(llm_client, schema_manager)
    sql_agent = SQLAgent(llm_client, db_client,schema_manager)
    synthesizer = SynthesizerAgent(llm_client)
    vector_tool = VectorSearchTool(vector_client, db_client,schema_manager)
    pandas_tool = PandasAnalyzerTool()

    nodes = GraphNodes(
        query_rewriter, intent_agent, sql_agent,
        synthesizer, vector_tool, pandas_tool, db_client,guardrail_agent
    )

    app = SQLOrchestrator(nodes)
    app.graph.get_graph().draw_mermaid_png(output_file_path = "mermaid.png")
    print("\nSQL Agent Online - Please Ask Your Query : ")
    print("Type 'exit' to quit.\n" + "=" * 50)

    history = []
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit']:
            break
        state = {"current_query": user_input, "messages": history}
        result = await app.invoke(state)
        extracted_filters = []
        for intent in result.get("intents", []):
            # Print the validated filters if available, otherwise raw filters
            filters_to_show = intent.get("validated_schema") or intent.get("filters")
            if filters_to_show:
                extracted_filters.append(filters_to_show)
                
        print(f"Extracted Filters : {extracted_filters}")
        queries = result.get('sql_queries', [])
        if queries:
            for i, q in enumerate(queries):
                print(f"Generated SQL {i+1}  : {q['sql']}")
        else:
            print("Generated SQL     : None")
        print("="*50 + "\n")
        final_answer = result.get('final_response', 'System Error: No response generated.')
        print(f"\nAssistant: {final_answer}")
        print(f"\nDEBUG: Full result keys: {result.keys()}")
        dashboard_data = result.get('dashboard_payload')
        if dashboard_data:
            print("\n" + "="*20 + " UI DASHBOARD PAYLOAD " + "="*20)
            import json
            print(json.dumps(dashboard_data, indent=2))
            print("="*62)
        else:
            print("\nDEBUG: No dashboard_payload found in result.")
            
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": final_answer})


if __name__ == "__main__":
    asyncio.run(main())