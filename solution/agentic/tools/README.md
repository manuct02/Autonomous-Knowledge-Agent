# Tools

This document describes the support tools used by agents in the **UDA-Hub** system.  
Tools abstract database access and expose safe business operations to agents.

---

## Design Principles

- Agents never access the database directly
- Each tool performs a single business action
- Tools return structured, predictable outputs
- Errors are handled safely and explicitly

---

## `lookup_account`

**Purpose**  
Retrieve basic account information for a user.

**Inputs**

| Field   | Type   |
|--------|--------|
| email  | string |
| user_id| string |

> At least one input must be provided.

**Output**
```json
{
  "found": true,
  "user_id": "abc123",
  "email": "user@example.com",
  "is_blocked": false
}
```
If not found:
```json
{ "found": false }
```
