# State Management en UDA-Hub

## Índice

1. [Visión General](#visión-general)
2. [TicketState: El Estado del Sistema](#ticketstate-el-estado-del-sistema)
3. [Flujo de Datos](#flujo-de-datos)
4. [Memoria a Corto Plazo (Sesión)](#memoria-a-corto-plazo-sesión)
5. [Memoria a Largo Plazo (Historial)](#memoria-a-largo-plazo-historial)
6. [Checkpointing y Persistencia](#checkpointing-y-persistencia)
7. [Ejemplos Prácticos](#ejemplos-prácticos)

---

## Visión General

El **state management** en UDA-Hub está diseñado para:

- ✅ Mantener contexto durante toda la ejecución del workflow
- ✅ Acumular información de cada nodo (classifier → router → specialist)
- ✅ Persistir conversaciones entre invocaciones
- ✅ Proporcionar trazabilidad completa de decisiones

### Principios de Diseño

1. **Inmutabilidad parcial**: Cada nodo retorna un nuevo diccionario que se mergea con el estado existente
2. **Type-safe**: `TypedDict` con Pydantic para validación
3. **Logging automático**: Cada nodo agrega su ejecución a `logs`
4. **Fail-safe**: Valores por defecto para evitar `KeyError`

---

## TicketState: El Estado del Sistema

### Definición

```python
from typing import TypedDict, Dict, List, Any

class TicketState(TypedDict, total=False):
    """
    Estado compartido entre todos los nodos del workflow.
    
    total=False permite campos opcionales.
    """
    ticket_text: str                    # Input original del usuario
    metadata: Dict[str, Any]            # Metadata del ticket (canal, timestamps, etc.)
    classification: Dict[str, Any]      # Output del classifier_node
    routing: Dict[str, Any]             # Output del route_node
    final_response: str                 # Respuesta final al usuario
    logs: List[Dict[str, Any]]          # Traza de ejecución
```

### Campos en Detalle

| Campo | Tipo | Origen | Propósito |
|-------|------|--------|-----------|
| `ticket_text` | `str` | Input inicial | Texto del ticket del usuario |
| `metadata` | `Dict` | Input inicial | Canal, urgencia, customer_id, etc. |
| `classification` | `Dict` | `classify_node` | Intent, urgency, confidence, rationale |
| `routing` | `Dict` | `route_node` | Agente seleccionado + decisión de routing |
| `final_response` | `str` | `specialist_node` | Respuesta generada por el agente |
| `logs` | `List[Dict]` | Todos los nodos | Historial de ejecución para debugging |

---

## Flujo de Datos

### Ciclo de Vida del Estado

```
┌────────────────────────────────────────────────────────────┐
│ INITIAL STATE                                              │
│ {                                                          │
│   "ticket_text": "I can't log in",                        │
│   "metadata": {"channel": "email"},                       │
│   "logs": []                                              │
│ }                                                          │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ AFTER CLASSIFY_NODE                                        │
│ {                                                          │
│   "ticket_text": "I can't log in",                        │
│   "metadata": {...},                                       │
│   "classification": {                                      │
│     "intent": "technical",                                │
│     "urgency": "medium",                                  │
│     "confidence": 0.87,                                   │
│     "rationale": "Login issue detected"                   │
│   },                                                       │
│   "logs": [                                               │
│     {"node": "classify", "classification": {...}}         │
│   ]                                                        │
│ }                                                          │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ AFTER ROUTE_NODE                                           │
│ {                                                          │
│   ...(previous state),                                     │
│   "routing": {                                             │
│     "route": "tech_agent",                                │
│     "confidence": 0.92,                                   │
│     "rationale": "Technical issue, high confidence",      │
│     "needs_more_info": false                              │
│   },                                                       │
│   "logs": [                                               │
│     {"node": "classify", ...},                            │
│     {"node": "route", "routing": {...}}                   │
│   ]                                                        │
│ }                                                          │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│ AFTER SPECIALIST_NODE (FINAL)                              │
│ {                                                          │
│   ...(all previous state),                                 │
│   "final_response": "Try tapping 'Forgot Password'...",   │
│   "logs": [                                               │
│     {"node": "classify", ...},                            │
│     {"node": "route", ...},                               │
│     {"node": "tech_specialist"}                           │
│   ]                                                        │
│ }                                                          │
└────────────────────────────────────────────────────────────┘
```

### Actualización del Estado en Nodos

Cada nodo sigue este patrón:

```python
def example_node(state: TicketState) -> TicketState:
    # 1. Leer estado actual con defaults seguros
    ticket_text = state.get("ticket_text", "") or ""
    logs = state.get("logs", []) or []
    
    # 2. Realizar procesamiento
    result = do_something(ticket_text)
    
    # 3. Agregar log
    logs.append({"node": "example", "result": result})
    
    # 4. Retornar estado actualizado (merge)
    return {
        **state,  # Preservar todo lo anterior
        "new_field": result,
        "logs": logs
    }
```

**Nota importante**: LangGraph hace un **merge automático**, así que solo necesitas retornar los campos que cambiaron.

---

## Memoria a Corto Plazo (Sesión)

### Implementación con MemorySaver

```python
from langgraph.checkpoint.memory import MemorySaver

# Compilar el workflow con checkpointing
agent_graph = workflow.compile(checkpointer=MemorySaver())
```

### Thread ID: Identificador de Conversación

Cada conversación tiene un `thread_id` único:

```python
result = agent_graph.invoke(
    input={"ticket_text": "...", "metadata": {...}},
    config={
        "configurable": {
            "thread_id": "user-123-session-456"  # ← Identifica la conversación
        }
    }
)
```

### Cómo Funciona

1. **Primera invocación**: LangGraph crea un nuevo checkpoint con `thread_id`
2. **Invocaciones subsecuentes**: LangGraph carga el último checkpoint del mismo `thread_id`
3. **Cada nodo ejecutado**: Se guarda un nuevo checkpoint
4. **Persistencia**: En memoria (RAM) con `MemorySaver`, o en DB con otros checkpointers

### Ejemplo: Conversación Multi-turn

```python
# Turno 1
result1 = agent_graph.invoke(
    input={"ticket_text": "I have a billing issue"},
    config={"configurable": {"thread_id": "conv-1"}}
)

# Turno 2 (mismo thread_id)
result2 = agent_graph.invoke(
    input={"ticket_text": "I was charged $50 twice"},
    config={"configurable": {"thread_id": "conv-1"}}  # ← Mismo thread
)

# El agente tiene acceso al historial completo de "conv-1"
```

### Limitaciones de MemorySaver

- ⚠️ **Solo en memoria**: Se pierde al reiniciar el proceso
- ⚠️ **No escalable**: No compartida entre workers/servers
- ✅ **Para producción**: Usar `SqliteSaver`, `PostgresSaver`, o `RedisSaver`

---

## Memoria a Largo Plazo (Historial)

### Estrategia: Búsqueda Semántica

Para recordar interacciones pasadas del cliente:

```python
# 1. Almacenar tickets resueltos en DB con embeddings
def store_resolved_ticket(ticket_id: str, resolution: str):
    embedding = embeddings.embed_query(resolution)
    db.insert({
        "ticket_id": ticket_id,
        "resolution": resolution,
        "embedding": embedding,
        "resolved_at": datetime.now()
    })

# 2. Buscar tickets similares previos
def find_similar_tickets(query: str, user_id: str):
    query_embedding = embeddings.embed_query(query)
    similar = db.search(
        embedding=query_embedding,
        filters={"user_id": user_id},
        limit=3
    )
    return similar
```

### Integración en el Workflow

```python
def specialist_node(state: TicketState) -> TicketState:
    ticket_text = state.get("ticket_text", "")
    metadata = state.get("metadata", {})
    user_id = metadata.get("user_id")
    
    # Buscar resoluciones previas
    similar_tickets = find_similar_tickets(ticket_text, user_id)
    
    # Agregar contexto histórico al prompt
    context = "\n".join([t["resolution"] for t in similar_tickets])
    prompt = f"Previous resolutions:\n{context}\n\nCurrent ticket: {ticket_text}"
    
    # Ejecutar agente con contexto histórico
    response = agent.invoke(prompt)
    
    return {**state, "final_response": response}
```

### Preferencias del Usuario

```python
# Almacenar preferencias
user_preferences = {
    "user_123": {
        "preferred_language": "es",
        "communication_style": "formal",
        "frequent_issues": ["billing", "reservation"]
    }
}

# Usar en routing
def route_node(state: TicketState) -> TicketState:
    user_id = state["metadata"]["user_id"]
    prefs = user_preferences.get(user_id, {})
    
    # Si el usuario tiene problemas frecuentes de billing, sesgar hacia billing_agent
    if "billing" in prefs.get("frequent_issues", []):
        # Ajustar confidence scores
        pass
```

---

## Checkpointing y Persistencia

### Anatomía de un Checkpoint

Un checkpoint contiene:

```python
{
    "thread_id": "conv-123",
    "checkpoint_id": "cp-456",
    "state": {
        "ticket_text": "...",
        "classification": {...},
        "routing": {...},
        "logs": [...]
    },
    "metadata": {
        "created_at": "2024-01-15T10:30:00Z",
        "node": "route_node"
    }
}
```

### Persistencia en SQLite (Producción)

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Persistir checkpoints en archivo
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
agent_graph = workflow.compile(checkpointer=checkpointer)

# Ahora los checkpoints sobreviven reinicios
```

### Recuperación de Estado

```python
# Obtener el último checkpoint de una conversación
checkpoints = checkpointer.list({"configurable": {"thread_id": "conv-1"}})
last_checkpoint = checkpoints[0]

print(last_checkpoint["state"]["classification"])
```

### Resetear una Conversación

```python
# Crear un nuevo thread_id para empezar desde cero
new_thread_id = f"user-{user_id}-{datetime.now().timestamp()}"

result = agent_graph.invoke(
    input={"ticket_text": "..."},
    config={"configurable": {"thread_id": new_thread_id}}
)
```

---

## Ejemplos Prácticos

### Ejemplo 1: Debugging con Logs

```python
result = run_system(
    ticket_text="My app keeps crashing",
    graph=agent_graph,
    thread_id="debug-session"
)

# Inspeccionar logs
for log in result["logs"]:
    print(f"[{log['node']}] {log}")

# Output:
# [classify] {'classification': {'intent': 'technical', 'confidence': 0.89}}
# [route] {'routing': {'route': 'tech_agent', 'confidence': 0.92}}
# [specialist] {'node': 'tech_specialist'}
```

### Ejemplo 2: Conversación Multi-turn con Contexto

```python
thread = "user-alice-session-1"

# Turno 1
r1 = agent_graph.invoke(
    {"ticket_text": "I need help with my account"},
    config={"configurable": {"thread_id": thread}}
)

# Turno 2 (el agente recuerda el contexto)
r2 = agent_graph.invoke(
    {"ticket_text": "Can you check my subscription status?"},
    config={"configurable": {"thread_id": thread}}
)

# El agente ya sabe que es un problema de cuenta del turno 1
```

### Ejemplo 3: Resumir Sesión Completa

```python
def summarize_session(thread_id: str) -> str:
    """Genera un resumen de toda la conversación"""
    checkpoints = checkpointer.list({"configurable": {"thread_id": thread_id}})
    
    messages = []
    for cp in checkpoints:
        state = cp["state"]
        if "final_response" in state:
            messages.append(state["final_response"])
    
    return "\n---\n".join(messages)

summary = summarize_session("user-123-session-1")
print(summary)
```

---

## Mejores Prácticas

### ✅ DO

- Usar `state.get("key", default)` para evitar `KeyError`
- Agregar logs detallados en cada nodo
- Usar `thread_id` descriptivos (e.g., `user-{id}-{timestamp}`)
- Validar estructura del estado con type hints
- Implementar cleanup de checkpoints antiguos

### ❌ DON'T

- Mutar el estado directamente (siempre retornar nuevo dict)
- Almacenar objetos no serializables en el estado (e.g., conexiones DB)
- Olvidar manejar casos donde el estado está vacío
- Usar el mismo `thread_id` para múltiples usuarios
- Ignorar los logs (son críticos para debugging)

---

## Referencias

- [LangGraph State Management](https://langchain-ai.github.io/langgraph/concepts/#state)
- [Checkpointing](https://langchain-ai.github.io/langgraph/concepts/#checkpointing)
- [MemorySaver](https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.memory.MemorySaver)
- Implementación en `agentic/workflow.py`
