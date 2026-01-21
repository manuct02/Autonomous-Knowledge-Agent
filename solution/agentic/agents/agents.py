from __future__ import annotations
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage
)
from langgraph.prebuilt import create_react_agent
from agentic.tools.tools import retrieve_knowledge, subscription_status, account_lookup, reservation_lookup
import os

# 1. Schemas

Intent= Literal["refund", "billing", "account", "technical", "reservation", "other"]
Urgency= Literal["low", "medium", "high"]
Route= Literal["billing_agent", "account_agent", "tech_agent", "reservation_agent", "escalation_agent"]

class TicketClassification(BaseModel):
    intent: Intent= Field(..., description="Main topic/intent of the ticket.")
    urgency: Urgency= Field(..., description="Urgency level for prioritization.")
    confidence: float= Field(..., ge= 0.0, le= 1.0, description="Classifier confidence 0..1.")
    rationale: str = Field(..., description="Short explanation of why this classification was chosen.")

class RoutingDecision(BaseModel):
    route: Route= Field(..., description="Which specialist should handle this ticket next.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Routing confidence 0..1.")
    rationale: str = Field(..., description="Why this route is best.")
    needs_more_info: bool = Field(
        default=False,
        description="True if the system must ask clarifying questions before acting.",
    )

llm= ChatOpenAI(model="gpt-4o-mini", temperature=0.0, base_url= os.getenv("OPENAI_BASE_URL"), api_key= os.getenv("OPENAI_API_KEY"))

ticket_classifier = llm.with_structured_output(TicketClassification)
route_decider = llm.with_structured_output(RoutingDecision)

def classify_ticket(ticket_text: str, metadata: Optional[Dict[str, Any]]= None)-> TicketClassification:
    """
    Structured classifier (Pydantic). Deterministic-ish and easy to test.
    """

    metadata= metadata or {}
    prompt = f"""
You are a ticket classifier for a customer support system (CultPass).
Return a structured classification.

Ticket:
{ticket_text}

Metadata (may be empty):
{metadata}

Guidelines:
- intent must be one of: refund, billing, account, technical, reservation, other
- urgency must be one of: low, medium, high
- confidence is 0..1
- rationale should be short and practical
""".strip()
    
    
    return ticket_classifier.invoke(prompt)

def decide_route(ticket_text: str, classification: TicketClassification) -> RoutingDecision:
    prompt = f"""
You are a routing supervisor in a multi-agent support system.

Classification:
{classification.model_dump()}

Ticket:
{ticket_text}

Routes:
- billing_agent
- account_agent
- tech_agent
- reservation_agent
- escalation_agent

Rules:
- If classification.confidence < 0.55 -> escalation_agent
- If classification.urgency is high and the ticket is unclear -> escalation_agent
Return a structured routing decision.
""".strip()

    return route_decider.invoke(prompt)


billing_agent= create_react_agent(
    name= "billing_agent",
    prompt= SystemMessage(
        content=("""
                 You are the Billing Specialist for CultPass support.

                 You must use tools to verify account/subscription context before making claims.

                 If you need email/user_id/charge date, ask for it clearly.

                 Provide a concise user-facing answer AND a structured "action_summary" at the end.


                 When you submit a refund request (if that tool exists), do NOT promise outcomes. Offer next steps.

                 """
        )
    ),
    model= llm,
    tools=[account_lookup, subscription_status, retrieve_knowledge ]
)

account_agent= create_react_agent(
    name= "account_agent",
    prompt= SystemMessage(
        content=(
        """You are the Account Specialist for CultPass support.
        Use tools to look up account status when possible.
        If the user is blocked/suspended, do not blame them. Escalate with a helpful summary if needed.
        Always ask for the account email if missing.
        """
        )

    ),
    model=llm,
    tools = [account_lookup, subscription_status, retrieve_knowledge]
)

tech_agent= create_react_agent(
    name= "tech_agent",
    prompt= SystemMessage(
        content=("""
You are the Technical Specialist for CultPass support.
First, consult knowledge articles for troubleshooting steps.
If the user reports a crash/bug, ask for device model, OS version, app version, and exact error text.
Escalate only if steps fail or the issue is reproducible.
""")
    ),
    model=llm,
    tools = [retrieve_knowledge]
)

escalation_agent= create_react_agent(
    name= "escalation_agent",
    prompt= SystemMessage(
        content=(
            """
You are the Escalation Specialist.
Your job is to prepare a handoff to a human agent.

Output:
1) A brief user-facing message: "I'm escalating..."
2) An escalation_payload JSON-like block containing:
   - summary
   - what_we_know
   - what_we_tried
   - missing_info
   - suggested_next_action
Be concise and operational.
"""

        )
    ),
    model=llm,
    tools = [retrieve_knowledge]

)

reservation_agent= create_react_agent(
    name= "reservation_agent",
    prompt= SystemMessage(
        content=(
            """
You are the Reservation Specialist for CultPass support.
Use tools to check recent reservations when user_id is available.
If user_id is unknown, ask for account email first and then proceed.
Use knowledge articles for QR/booking troubleshooting.
"""
        )
    ),
    model=llm,
    tools = [account_lookup, reservation_lookup, retrieve_knowledge]

)

agents= {"llm": llm, "billing_agent": billing_agent, "account_agent": account_agent, "tech_agent": tech_agent, "reservation_agent": reservation_agent, "escalation_agent": escalation_agent}