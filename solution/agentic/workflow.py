from __future__ import annotations

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
)
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
)
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver



from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agentic.agents.agents import (
    agents,
    classify_ticket,
    decide_route,
)

# 1. State

class TicketState(TypedDict, total= False):
    ticket_text: str
    metadata: Dict[str, Any]
    classification: Dict[str, Any]
    routing: Dict[str, Any]
    final_response: str
    logs: List[Dict[str, Any]]

# 2. Nodos

def classify_node(state: TicketState)-> TicketState:
    ticket_text= state.get("ticket_text", "") or ""
    metadata= state.get("metadata", {}) or {}

    cls= classify_ticket(ticket_text= ticket_text, metadata=metadata)
    logs= state.get("logs", []) or []
    logs.append({"node": "classify", "classification": cls.model_dump()})

    return {**state, "classification": cls.model_dump(), "logs": logs}

def route_node(state: TicketState)-> TicketState:
    ticket_text= state.get("ticket_text", "") or ""
    cls_dict = state.get("classification", {}) or {}

    from agentic.agents.agents import TicketClassification

    cls_obj= TicketClassification(**cls_dict)
    decision = decide_route(ticket_text=ticket_text, classification=cls_obj)

    logs= state.get("logs", []) or []
    logs.append({"node": "route", "routing": decision.model_dump()})

    return {**state, "routing": decision.model_dump(), "logs": logs}

def specialist_node(state: TicketState)-> TicketState:
    """
    executes the react_agent chosen in routing.route

    """
    ticket_text = state.get("ticket_text", "") or ""
    metadata = state.get("metadata", {}) or {}
    routing = state.get("routing", {}) or {}

    route= routing.get("route", "escalation_agent")

    agent= agents.get(route)
    if agent is None:
        # fallback seguro
        agent= agents.get("escalation_agent")
        route= "escalation_agent"
    
    from langchain_core.messages import HumanMessage, AIMessage
    result= agent.invoke({"messages": [HumanMessage(content=ticket_text)], "metadata": metadata})

    final_text = ""
    for m in reversed(result.get("messages", [])):
        if isinstance(m, AIMessage) and m.content:
            final_text = m.content
            break

    if not final_text:
        final_text = "No se pudo generar una respuesta automática. El caso será escalado."
    
    logs = state.get("logs", []) or []
    logs.append({"node": "specialist", "route": route})

    return {**state, "final_response": final_text, "logs": logs}

def route_to_specialist(state: TicketState)-> str:
    routing= state.get("routing", {}) or {}
    return  routing.get("route", "escalation_agent")




def create_workflow():

    workflow= StateGraph(TicketState)

    workflow.add_node("classify", classify_node)
    workflow.add_node("route", route_node)
    workflow.add_node("specialist", specialist_node)

    workflow.add_edge(START, "classify")
    workflow.add_edge("classify", "route")
    workflow.add_conditional_edges(
        "route",
        route_to_specialist,
        {
            # todas van al mismo nodo "specialist"
            "billing_agent": "specialist",
            "account_agent": "specialist",
            "tech_agent": "specialist",
            "reservation_agent": "specialist",
            "escalation_agent": "specialist",
        },
    )
    workflow.add_edge("specialist", END)

    return workflow

agent_workflow= create_workflow()

agent_graph= agent_workflow.compile(checkpointer=MemorySaver())
agent_workflow_png= agent_graph.get_graph().draw_mermaid_png()

with open("agent_workflow.png", "wb") as f:
    f.write(agent_workflow_png)