# UDA-Hub: Agente de Decisión Universal para Soporte al Cliente

## 📋 Índice

- [Resumen Ejecutivo](#resumen-ejecutivo)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Decisiones de Diseño](#decisiones-de-diseño)
- [Instalación y Setup](#instalación-y-setup)
- [Uso](#uso)
- [Testing](#testing)
- [Extensibilidad](#extensibilidad)

---

## 🎯 Resumen Ejecutivo

**UDA-Hub** es un sistema multi-agéntico avanzado diseñado para automatizar el soporte al cliente de manera inteligente. A diferencia de chatbots tradicionales basados en FAQs, UDA-Hub:

- ✅ **Entiende el contexto** completo del ticket (texto + metadatos)
- ✅ **Decide dinámicamente** qué agente especializado debe intervenir
- ✅ **Recupera conocimiento** relevante mediante RAG cuando es necesario
- ✅ **Ejecuta acciones** en sistemas externos (lookups, refunds, etc.)
- ✅ **Escala inteligentemente** cuando la confianza es baja o falta información
- ✅ **Mantiene memoria** de conversaciones y preferencias del usuario

### Características Clave

| Característica | Descripción |
|----------------|-------------|
| **Multi-agente** | Arquitectura con agentes especializados (billing, account, tech, reservation, escalation) |
| **Routing inteligente** | Clasificación y enrutamiento basado en confianza y contexto |
| **RAG integrado** | Retrieval de knowledge base con scoring de relevancia |
| **Structured outputs** | Validación con Pydantic para respuestas consistentes |
| **Memoria persistente** | Short-term (sesión) y long-term (preferencias) |
| **Herramientas externas** | Integración con DBs externas para lookups y acciones |

---

## 🏗️ Arquitectura del Sistema

### Diagrama de Flujo

```
┌──────────────┐
│  USER TICKET │
│ (text + meta)│
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  CLASSIFIER      │ ◄── Pydantic Validation
│  - Intent        │
│  - Urgency       │
│  - Confidence    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  ROUTER          │ ◄── Decision Logic
│  - Select Agent  │
│  - Check Conf.   │
└──────┬───────────┘
       │
       ▼
┌─────────────────────────────────────┐
│     SPECIALIZED AGENTS              │
├─────────────┬───────────┬───────────┤
│  BILLING    │  ACCOUNT  │   TECH    │
│  RESERVATION│ ESCALATION│           │
└─────┬───────┴───────┬───┴───────┬───┘
      │               │           │
      ▼               ▼           ▼
┌──────────┐   ┌──────────┐  ┌──────────┐
│  TOOLS   │   │   RAG    │  │  MEMORY  │
│ - lookup │   │ retrieve │  │ - thread │
│ - refund │   │ articles │  │ - history│
└──────────┘   └──────────┘  └──────────┘
      │               │           │
      └───────┬───────┴───────────┘
              │
              ▼
       ┌──────────────┐
       │ FINAL RESP.  │
       │ or ESCALATION│
       └──────────────┘
```

### Componentes Principales

#### 1. **Classifier Agent**
- Analiza el ticket entrante
- Extrae: `intent`, `urgency`, `confidence`, `rationale`
- Validación estricta con Pydantic
- **Output estructurado**: `TicketClassification`

#### 2. **Router Agent**
- Decide el agente especializado apropiado
- Reglas de routing basadas en confianza
- Escala automáticamente si `confidence < 0.55`
- **Output estructurado**: `RoutingDecision`

#### 3. **Specialized Agents**

| Agente | Responsabilidad | Tools |
|--------|----------------|-------|
| `billing_agent` | Facturación, reembolsos, cargos duplicados | `account_lookup`, `subscription_status`, `retrieve_knowledge` |
| `account_agent` | Gestión de cuenta, bloqueos, verificación | `account_lookup`, `subscription_status`, `retrieve_knowledge` |
| `tech_agent` | Problemas técnicos, bugs, crashes | `retrieve_knowledge` |
| `reservation_agent` | Reservas, QR codes, confirmaciones | `account_lookup`, `reservation_lookup`, `retrieve_knowledge` |
| `escalation_agent` | Preparación de handoff a humanos | `retrieve_knowledge` |

#### 4. **Tools**
- `account_lookup`: Buscar usuario por email/user_id
- `subscription_status`: Verificar estado de suscripción
- `reservation_lookup`: Listar reservas del usuario
- `retrieve_knowledge`: RAG sobre knowledge base

#### 5. **Knowledge Base (RAG)**
- Artículos en formato JSONL
- Scoring basado en token overlap (MVP)
- Top-k retrieval con threshold de relevancia
- Fácilmente reemplazable por embeddings

---

## 🧠 Decisiones de Diseño

### ¿Por qué LangGraph?

- **Flujo explícito**: Visibilidad clara del routing entre nodos
- **Memoria nativa**: Soporte built-in para checkpointing
- **Debugging**: Fácil traceabilidad de decisiones
- **Escalabilidad**: Agregar nuevos agentes es trivial

### ¿Por qué Pydantic para Structured Outputs?

- **Type safety**: Garantiza outputs consistentes
- **Validación automática**: Constraints (ge, le) previenen datos inválidos
- **Testing**: Facilita pruebas unitarias
- **Documentación**: Schemas autodocumentados

### Manejo de Memoria

#### Short-term (Sesión)
- Implementado con `MemorySaver` de LangGraph
- `thread_id` identifica conversaciones
- Persiste estado durante ejecución del workflow

#### Long-term (Preferencias/Historial)
- Búsqueda semántica sobre tickets previos (futuro)
- Almacenamiento en base de datos
- Lookup de resoluciones pasadas

### Error Handling

- **Tools nunca fallan**: Retornan `{"ok": false, "error": "..."}`
- **Escalation como fallback**: Si algo sale mal → escalation_agent
- **Validación temprana**: Pydantic atrapa errores antes de ejecutar

---

## 🚀 Instalación y Setup

### Prerrequisitos

```bash
Python 3.11+
SQLite3
OpenAI API Key (o compatible)
```

### Instalación

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd autonomous_knowledge_agent

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu OPENAI_API_KEY
```

### Configuración de Base de Datos

```bash
# 1. Setup DB externa (CultPass)
jupyter notebook solution/01_external_db_setup.ipynb
# Ejecutar todas las celdas

# 2. Setup DB interna (UDA-Hub)
jupyter notebook solution/02_core_db_setup.ipynb
# Ejecutar todas las celdas
```

**Importante**: Expandir `cultpass_articles.jsonl` a mínimo 14 artículos antes de ejecutar el notebook 2.

---

## 💻 Uso

### Ejecución Básica

```bash
python solution/03_agentic_app.py
```

### Ejemplo de Uso Programático

```python
from agentic.workflow import agent_graph, run_system

# Procesar un ticket
result = run_system(
    ticket_text="I've been charged twice for my subscription",
    graph=agent_graph,
    thread_id="user-123"
)

# Acceder a resultados
print(result["classification"])  # Intent, urgency, confidence
print(result["routing"])         # Agente seleccionado
print(result["final_response"])  # Respuesta al usuario
print(result["logs"])            # Traza de ejecución
```

### Chat Interactivo

```python
from utils import chat_interface
from agentic.workflow import agent_graph

chat_interface(agent_graph, ticket_id="demo-session-1")
```

### Casos de Uso de Ejemplo

#### 1. Billing Issue
```
Input: "I was charged $29.99 but I cancelled my plan last week"
→ Classifier: intent=refund, urgency=medium
→ Router: billing_agent
→ Tools: subscription_status → verifica cancelación
→ Output: "I see you cancelled on [date]. Let me initiate a refund..."
```

#### 2. Technical Issue
```
Input: "The app crashes when I try to reserve an event"
→ Classifier: intent=technical, urgency=high
→ Router: tech_agent
→ RAG: recupera "App Crashes or Freezes During Booking"
→ Output: "Please update to the latest version and..."
```

#### 3. Low Confidence → Escalation
```
Input: "Something is wrong with my account"
→ Classifier: confidence=0.42
→ Router: escalation_agent (low confidence)
→ Output: "I'm escalating this to a specialist. Summary: ..."
```

---

## 🧪 Testing

### Validación de Schemas

```python
# Test: Confidence debe estar entre 0-1
from agentic.agents.agents import TicketClassification

try:
    TicketClassification(
        intent="billing",
        urgency="high",
        confidence=1.5,  # ❌ Inválido
        rationale="test"
    )
except ValidationError as e:
    print("✅ Validation caught out-of-bounds confidence")
```

### Test de Routing

```python
# Test: Low confidence → escalation
classification = classify_ticket("unclear issue")
assert classification.confidence < 0.6
decision = decide_route("unclear issue", classification)
assert decision.route == "escalation_agent"
```

### Test de Tools

```python
# Test: account_lookup con email inválido
result = account_lookup("not-an-email")
assert result["ok"] == False
assert result["error"] == "invalid_email"
```

---

## 🔧 Extensibilidad

### Agregar un Nuevo Agente

1. **Definir en `agents.py`**:
```python
payment_agent = create_react_agent(
    name="payment_agent",
    prompt=SystemMessage(content="You handle payment issues..."),
    model=llm,
    tools=[payment_tool]
)
```

2. **Actualizar Router**:
```python
Route = Literal[..., "payment_agent"]
```

3. **Agregar nodo en `workflow.py`**:
```python
workflow.add_node("payment_specialist", payment_node)
workflow.add_conditional_edges("route", ..., {"payment_agent": "payment_specialist"})
```

### Agregar una Nueva Tool

```python
@tool
def cancel_subscription(user_id: str) -> Dict[str, Any]:
    """Cancel user subscription"""
    # Implementación
    return {"ok": True, "cancelled_at": datetime.now()}
```

### Mejorar RAG con Embeddings

```python
# Reemplazar _simple_text_score con:
from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings()

# Vectorizar artículos
vectors = embeddings.embed_documents([a["content"] for a in articles])

# Query con similarity search
query_vector = embeddings.embed_query(query)
scores = cosine_similarity(query_vector, vectors)
```

---

## 📊 Métricas de Éxito

- **Tasa de resolución automática**: % de tickets resueltos sin escalación
- **Confianza promedio**: Avg confidence score del classifier
- **Tiempo de respuesta**: Latencia end-to-end
- **Precisión de routing**: % de veces que se eligió el agente correcto

---

## 🤝 Contribuciones

Para contribuir:

1. Fork el repositorio
2. Crear una rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrir un Pull Request

---

## 📄 Licencia

Este proyecto es parte del LangChain Nanodegree y está sujeto a las políticas académicas de Udacity.

---

## 🙋 FAQ

**P: ¿Cómo se manejan errores en las tools?**  
R: Las tools nunca lanzan excepciones. Retornan `{"ok": false, "error": "..."}` y el agente decide cómo proceder.

**P: ¿Se puede usar otro LLM en vez de OpenAI?**  
R: Sí, solo cambiar `ChatOpenAI` por otro proveedor compatible con LangChain.

**P: ¿Cómo se escala el sistema para múltiples clientes?**  
R: Usar `account_id` en todos los queries de DB y agregar multi-tenancy en el routing.

**P: ¿Qué pasa si un ticket requiere múltiples agentes?**  
R: Actualmente el sistema es single-pass. Para multi-step, agregar un supervisor que orqueste múltiples invocaciones.

---

## 📚 Referencias

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Pydantic Validation](https://docs.pydantic.dev/latest/)
- [LangChain Tools](https://python.langchain.com/docs/modules/agents/tools/)
- Arquitectura detallada: `agentic/design/architecture.md`
- Documentación de agentes: `agentic/agents/README.md`
- Documentación de tools: `agentic/tools/README.md`
