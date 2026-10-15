"""LangGraph workflow with explicit SQL, RAG and hybrid branches."""
from typing import TypedDict, Any
from .assistant import answer_question, route_question

class AssistantState(TypedDict, total=False):
    question: str
    route: str
    result: dict[str, Any]

def _route_node(state: AssistantState):
    return {'route': route_question(state['question'])}

def _dispatch(state: AssistantState):
    # answer_question applies the selected deterministic tools and formats grounded output.
    return {'result': answer_question(state['question'])}

try:
    from langgraph.graph import StateGraph, START, END
    builder=StateGraph(AssistantState)
    builder.add_node('route',_route_node)
    builder.add_node('structured_sql',_dispatch)
    builder.add_node('policy_rag',_dispatch)
    builder.add_node('hybrid_or_clarify',_dispatch)
    builder.add_edge(START,'route')
    builder.add_conditional_edges('route', lambda state: (
        'structured_sql' if state.get('route') in {'claim_sql','policy_sql','customer_sql','hospital_sql','interaction_sql'}
        else 'hybrid_or_clarify' if state.get('route') in {'claim_analysis','hybrid_or_clarify'}
        else 'policy_rag'
    ), {'structured_sql':'structured_sql','policy_rag':'policy_rag','hybrid_or_clarify':'hybrid_or_clarify'})
    for node in ('structured_sql','policy_rag','hybrid_or_clarify'):
        builder.add_edge(node,END)
    _graph=builder.compile()
    LANGGRAPH_AVAILABLE=True
except ImportError:
    _graph=None
    LANGGRAPH_AVAILABLE=False

def run_assistant(question: str):
    if _graph:
        state=_graph.invoke({'question':question})
        return state['result']
    return answer_question(question)
