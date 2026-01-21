# UDA-Hub (ADU) — Arquitectura del sistema multi-agente

## 1) Objetivo
UDA-Hub es un **Agente de Decisión Universal (ADU)** que procesa tickets de soporte (texto + metadata),
decide **qué agente/herramienta** debe actuar y produce una salida final:
- Respuesta al usuario (si se puede resolver)
- Acción en sistemas internos (si aplica)
- Escalado a humano con resumen (si no hay confianza o faltan datos)

---

## 2) Inputs y Outputs

### Inputs
- **Ticket**: `text` + `metadata` (canal, urgencia, historial, timestamps, customer_id, etc.)
- **Knowledge Base**: artículos (FAQ + tickets previos) → vía retrieval (RAG)
- **Tools internas**: lookup de cuenta, reembolsos, suscripción, etc.
- **Memoria**:
  - short-term: estado de la sesión/hilo
  - long-term: historial del cliente, preferencias, resoluciones previas

### Outputs
- **final_response**: texto para el usuario (o para el agente humano)
- **action_log**: decisiones tomadas (routing, tools usadas, scores)
- **escalation_payload** (si aplica): resumen + contexto + próximos pasos

---

## 3) Agentes del sistema (roles y responsabilidades)

### A1 — Supervisor / Orquestador
**Responsabilidad:** coordinar el flujo completo y tomar decisiones globales.
- Decide la ruta (KB vs Tool vs Escalado)
- Evalúa confianza / completitud
- Controla bucles (máx pasos)

**Entrada:** ticket + resultados parciales  
**Salida:** siguiente nodo del grafo + instrucciones a agentes

---

### A2 — Clasificador de Tickets
**Responsabilidad:** extraer intención y señales para routing.
- `intent` (billing/refund/account/technical/reservation/other)
- `urgency` (low/medium/high)
- `complexity` (low/medium/high)
- `confidence` (0–1)

**Salida:** `classification` estructurada

---

### A3 — Agente de Conocimiento (RAG)
**Responsabilidad:** buscar artículos relevantes y proponer respuesta.
- Ejecuta retrieval sobre Knowledge base
- Devuelve top_k artículos + respuesta sugerida
- Incluye `answer_confidence`

---

### A4 — Agente de Herramientas (Tool Executor)
**Responsabilidad:** ejecutar acciones o consultas en DB/sistemas.
- account lookup
- estado de suscripción
- refund request (si existe)
- reservas, etc.

Devuelve resultados estructurados + `tool_confidence`.

---

### A5 — Agente de Escalado / Resumen (opcional pero recomendado)
**Responsabilidad:** si no se puede resolver, preparar escalado a humano.
- Resumen del caso
- Qué se intentó
- Qué falta
- Próxima acción recomendada

---

## 4) Diagrama (Mermaid) — Flujo multi-agente

```mermaid
flowchart TD
  START([START]) --> C[Classifier Agent]
  C --> S[Supervisor Agent]

  S -->|Intent: simple + alta confianza| K[Knowledge/RAG Agent]
  S -->|Requiere acción o datos de cuenta| T[Tool Agent]
  S -->|Baja confianza / falta info| E[Escalation Agent]

  K --> S
  T --> S

  S -->|Resolved| END([END: Final Response])
  S -->|Escalate| END2([END: Escalation Payload])
