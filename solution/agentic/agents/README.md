# Agents

This document describes the agents that compose the **UDA-Hub** multi-agent system and their responsibilities.

Each agent is specialized in a specific support domain and operates within the LangGraph workflow based on routing decisions.

---

## Agent Overview

The system follows a **supervisor–specialist pattern**:

1. A classifier interprets the incoming ticket
2. A routing decision selects the appropriate agent
3. A specialized agent handles the request or escalates when needed

---

## `classifier_agent`

**Responsibility**

Analyze incoming customer tickets to determine:
- Intent (e.g. billing, technical issue, reservation)
- Urgency level
- Confidence score
- Classification rationale

**Key Behaviors**
- Processes raw ticket text and metadata
- Produces structured classification output
- Does not interact with tools or databases

**Outputs**
- Intent
- Urgency
- Confidence
- Rationale

---

## `routing_agent`

**Responsibility**

Decide which specialized agent should handle the ticket based on classification results.

**Key Behaviors**
- Consumes classification output
- Selects the most appropriate agent
- Falls back to escalation when confidence is low or intent is unclear

**Outputs**
- Selected route (agent name)
- Routing confidence
- Routing rationale

---

## `billing_agent`

**Responsibility**

Handle billing-related issues such as:
- Refund requests
- Duplicate charges
- Subscription cost questions

**Key Behaviors**
- Requests additional user information when required
- Uses billing and subscription tools
- Initiates refund workflows when applicable

**Tools Used**
- `lookup_account`
- `get_subscription_status`
- `process_refund`

---

## `account_agent`

**Responsibility**

Handle account-related issues such as:
- Account verification
- Blocked accounts
- Basic user profile inquiries

**Key Behaviors**
- Validates account existence
- Checks account status
- Provides account-related guidance

**Tools Used**
- `lookup_account`

---

## `reservation_agent`

**Responsibility**

Handle reservation and booking-related issues.

**Key Behaviors**
- Retrieves reservation information
- Assists with confirmation or troubleshooting
- Guides users through reservation-related questions

**Tools Used**
- `lookup_reservations`

---

## `tech_agent`

**Responsibility**

Handle technical issues such as:
- Application errors
- Service malfunctions
- Unexpected system behavior

**Key Behaviors**
- Provides technical guidance
- Suggests troubleshooting steps
- Escalates complex or unresolved issues

**Tools Used**
- None (knowledge-based responses)

---

## `escalation_agent`

**Responsibility**

Handle cases that cannot be resolved automatically.

**Key Behaviors**
- Acts as a safe fallback for low-confidence decisions
- Provides empathetic responses
- Escalates issues to human support when necessary

**Tools Used**
- None

---

## Summary

Each agent in the system:
- Has a clearly defined responsibility
- Operates only within its assigned domain
- Uses tools only when necessary
- Integrates seamlessly into the LangGraph workflow

This design enables scalable, explainable, and maintainable customer support automation.
