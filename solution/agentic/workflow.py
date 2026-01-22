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
import sqlite3


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


from langchain_core.messages import HumanMessage, AIMessage

def _run_agent(state: TicketState, agent_name: str) -> TicketState:
    ticket_text = state.get("ticket_text", "")
    metadata = state.get("metadata", {}) or {}

    agent = agents.get(agent_name)
    if agent is None:
        raise RuntimeError(f"Agent not found: {agent_name}")

    result = agent.invoke(
        {"messages": [HumanMessage(content=ticket_text)], "metadata": metadata}
    )

    final_text = ""
    for m in reversed(result.get("messages", [])):
        if isinstance(m, AIMessage) and m.content:
            final_text = m.content
            break

    if not final_text:
        final_text = "No se pudo generar una respuesta automática."

    logs = state.get("logs", []) or []
    logs.append({"node": agent_name})

    return {
        **state,
        "final_response": final_text,
        "logs": logs,
    }

def billing_node(state: TicketState) -> TicketState:
    return _run_agent(state, "billing_agent")

def account_node(state: TicketState) -> TicketState:
    return _run_agent(state, "account_agent")

def tech_node(state: TicketState) -> TicketState:
    return _run_agent(state, "tech_agent")

def reservation_node(state: TicketState) -> TicketState:
    return _run_agent(state, "reservation_agent")

def escalation_node(state: TicketState) -> TicketState:
    return _run_agent(state, "escalation_agent")


def create_workflow():

    workflow= StateGraph(TicketState)

    workflow.add_node("classify", classify_node)
    workflow.add_node("route", route_node)
    workflow.add_node("billing_specialist", billing_node)
    workflow.add_node("account_specialist", account_node)
    workflow.add_node("tech_specialist", tech_node)
    workflow.add_node("reservation_specialist", reservation_node)
    workflow.add_node("escalation_specialist", escalation_node)

    workflow.add_edge(START, "classify")
    workflow.add_edge("classify", "route")
    workflow.add_conditional_edges(
        "route",
        route_to_specialist,
        {
            "billing_agent": "billing_specialist",
            "account_agent": "account_specialist",
            "tech_agent": "tech_specialist",
            "reservation_agent": "reservation_specialist",
            "escalation_agent": "escalation_specialist",
        },
    )

    workflow.add_edge("billing_specialist", END)
    workflow.add_edge("account_specialist", END)
    workflow.add_edge("tech_specialist", END)
    workflow.add_edge("reservation_specialist", END)
    workflow.add_edge("escalation_specialist", END)


    return workflow

agent_workflow= create_workflow()


agent_graph= agent_workflow.compile(checkpointer=MemorySaver())
agent_workflow_png= agent_graph.get_graph().draw_mermaid_png()

from langgraph.graph.state import CompiledStateGraph

def run_system(
        ticket_text: str,
        graph: CompiledStateGraph,
        thread_id: str,
):
    result= graph.invoke(
        input={"ticket_text": ticket_text, "metadata": {"channel": "email"}},
        config={
            "configurable":{
                "thread_id": thread_id,
                
            }
        }
    )
    return result

result= run_system(
    ticket_text="I lost my password and cannot access my account. Please help me reset it.",
    graph= agent_graph,
    thread_id= "1"
)

print("\n" + "="*70)
print("🎫 TICKET PROCESSED")
print("="*70)

print("\n📝 CLASIFICATION:")
classification = result.get("classification", {})
print(f"  • Intent: {classification.get('intent', 'N/A')}")
print(f"  • Urgencia: {classification.get('urgency', 'N/A')}")
print(f"  • Confianza: {classification.get('confidence', 0):.2f}")
print(f"  • Razón: {classification.get('rationale', 'N/A')}")

print("\n🔀 ROUTING:")
routing = result.get("routing", {})
print(f"  • Ruta: {routing.get('route', 'N/A')}")
print(f"  • Confianza: {routing.get('confidence', 0):.2f}")
print(f"  • Razón: {routing.get('rationale', 'N/A')}")

print("\n💬 FINAL RESPONSE:")
print("-" * 70)
print(result.get("final_response", "No response was generated"))
print("-" * 70)

print("\n📋 EXECUTION LOGS:")
for i, log in enumerate(result.get("logs", []), 1):
    print(f"  {i}. {log}")

print("\n" + "="*70)