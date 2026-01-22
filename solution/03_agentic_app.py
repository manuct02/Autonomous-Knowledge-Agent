"""
Entry point for the UDA-Hub agentic system.

Run with:
    python 03_agentic_app.py
"""

from agentic.workflow import agent_graph, run_system


def main():
    ticket_text = "I've been charged twice and I want a refund."

    result = run_system(
        ticket_text=ticket_text,
        graph=agent_graph,
        thread_id="demo-user-1",
    )

    print("\n" + "=" * 70)
    print("🎫 TICKET PROCESSED")
    print("=" * 70)

    print("\n📝 CLASSIFICATION:")
    classification = result.get("classification", {})
    print(f"  • Intent: {classification.get('intent')}")
    print(f"  • Urgency: {classification.get('urgency')}")
    print(f"  • Confidence: {classification.get('confidence')}")
    print(f"  • Rationale: {classification.get('rationale')}")

    print("\n🔀 ROUTING:")
    routing = result.get("routing", {})
    print(f"  • Route: {routing.get('route')}")
    print(f"  • Confidence: {routing.get('confidence')}")
    print(f"  • Rationale: {routing.get('rationale')}")

    print("\n💬 FINAL RESPONSE:")
    print("-" * 70)
    print(result.get("final_response"))
    print("-" * 70)

    print("\n📋 EXECUTION LOGS:")
    for i, log in enumerate(result.get("logs", []), 1):
        print(f"  {i}. {log}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
