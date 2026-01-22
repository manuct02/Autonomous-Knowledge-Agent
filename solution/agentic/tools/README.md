# Tools

This document describes the tools available to agents in the **UDA-Hub** system.

Tools encapsulate business operations and database access, allowing agents to act without directly interacting with internal data models.

---

## Tool Design Principles

All tools in the system follow these rules:

- Tools abstract database and business logic
- Agents decide **when** to use a tool
- Tools never make autonomous decisions
- All outputs are structured and predictable
- Errors are handled safely and explicitly

---

## `lookup_account`

**Responsibility**

Retrieve basic account information for a user.

**Typical Usage**
- Verify user existence
- Check whether an account is blocked
- Validate user identity before sensitive operations

**Inputs**
- `email` (string, optional)
- `user_id` (string, optional)

At least one input must be provided.

**Output**
```json
{
  "found": true,
  "user_id": "abc123",
  "email": "user@example.com",
  "is_blocked": false
}
```

If no account is found:
```json
{"found": false}
```

**Used by**:
- `account_agent`
- `billing_account`

## `get_subscription_status`

**Responsibility**

Retrieve the current subscription status for a user

**Typical Usage**
- Determine whether a subscription is active
- Check plan tier before refunds or reservations
- Support billing-related decisions

**Inputs**
- `user_id` (string)

**Output**
```json
{
  "status": "active",
  "tier": "premium",
  "monthly_cost": 29.99
}

```

If the user has no subscriptions:
```json
{"status": "none"}
```

**Used by**:
- `billing_agent`
- `reservation_agent`

## `process_refund`

**Responsibility**

Initiate a refund request for a user.

**Typical Usage**
- Duplicate charges

- Approved billing disputes

**Inputs**
- `user_id` (string)
- `amount` (int)
- `reason` (string)

**Output**
```json
{
  "refund_id": "ref_789xyz",
  "status": "initiated"
}

```

**Notes**:

- This tool represents a safe abstraction over refund logic

- It does not directly interact with payment gateways

**Used by**:
- `billing_agent`

## `lookup_reservations`

**Responsibility**

Retrieve reservation data associated with a user.

**Typical Usage**
- Reservation confirmation issues

- Booking troubleshooting

- Reservation-related inquiries

**Inputs**
- `user_id` (string, optional)



**Output**
```json
{
  "reservations": []
}
```


**Used by**:
- `reservation_agent`

## `Error Handling`

Tools never raise uncaught exceptions.

Errors are returned as structured responses:

```json
{ "error": "user_not_found" }
```

This ensures predictable behavior and safe agent execution.
