from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict, total=False):
    current_query: str
    messages: List[Dict[str, str]]
    route: Optional[str]
    metric: Optional[str]
    group_by: Optional[str]
    raw_filters: Dict[str, Any]
    requires_pandas: bool
    top_n: Optional[int]
    validated_schema: Dict[str, str]
    sql_queries: List[Dict[str, str]]
    raw_db_results: List[Any]
    pandas_results: List[Any]
    final_response: Optional[str]
    direct_response: Optional[str]
    category: str
    intents: List[Dict[str, Any]]
    response_type: Optional[str]
    clarification_options: Optional[List[str]]
    dashboard_payload: Optional[Dict[str, Any]]
    user_id: Optional[str]
    module: Optional[str]
    language: Optional[str]