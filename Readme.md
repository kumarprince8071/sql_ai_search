project_root/
│
├── data/                           # Local data storage 
│   ├── Harmonia_DB.sqlite          # Your Star Schema DB
│   └── chroma_db/                  # Persistent Vector DB directory (if used locally)
│
├── src/
│   │
│   ├── base/                       #  Abstract Base Classes (The Contracts)
│   │   ├── __init__.py
│   │   ├── base_llm.py             # Interface for all LLMs
│   │   ├── base_rdbms.py           # Interface for all SQL databases
│   │   └── base_vector_db.py       # Interface for all Vector stores
│   │
│   ├── clients/                    #  Concrete Adapters (The Technology)
│   │   ├── llms/
│   │   │   ├── __init__.py
│   │   │   └── openai_client.py    # Implements base_llm.py
│   │   ├── rdbms/
│   │   │   ├── __init__.py
│   │   │   └── sqlite_client.py    # Implements base_rdbms.py
│   │   └── vector/
│   │       ├── __init__.py
│   │       └── azure_search_client.py # Implements base_vector_db.py
│   │
│   ├── schemas/                    #  Centralized Pydantic Models
│   │   ├── __init__.py
│   │   └── pydantic_models.py      # IntentContract, SQLContract, QueryObject, etc.
│   │
│   ├── prompts/                    #  Centralized Prompt Registry
│   │   ├── __init__.py
│   │   └── prompt_registry.py      # Holds all system prompts as variables
│   │
│   ├── agents/                     # Pure Reasoning Layer (No hardcoded tech)
│   │   ├── __init__.py
│   │   ├── query_rewriter_agent.py
│   │   ├── intent_agent.py
│   │   ├── sql_agent.py
│   │   └── synthesizer_agent.py
│   │
│   ├── tools/                      # Independent compute/analysis tools
│   │   ├── __init__.py
│   │   ├── vector_search_tool.py   # Refactored to accept BaseVectorDB injected
│   │   └── pandas_analyzer_tool.py
│   │
│   ├── graph/                      # LangGraph Orchestration Layer
│   │   ├── __init__.py
│   │   ├── workflow.py             # Defines the HybridSQLOrchestrator class
│   │   └── nodes.py                # Wrapper functions for LangGraph state
│   │
│   ├── core/                       # Core system logic and state management
│   │   ├── __init__.py
│   │   ├── state.py                # Defines AgentState TypedDict
│   │   ├── exceptions.py           # Custom Python error classes
│   │   └── memory_manager.py       # Manages token/conversation windows
│   │
│   └── utils/                      # Helper Utilities
│       ├── __init__.py
│       ├── config.py               # Environment variable loading
│       └── logger.py               # Standardized logging setup
│
├── .env                            # API keys and DB paths
├── requirements.txt                # Python dependencies
└── main.py                         # App Config & Dependency Injection Entry Point
