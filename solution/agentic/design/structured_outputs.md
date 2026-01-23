# Structured Outputs y Schemas en UDA-Hub

## Índice

1. [¿Por qué Structured Outputs?](#por-qué-structured-outputs)
2. [Pydantic: Validación Type-Safe](#pydantic-validación-type-safe)
3. [Schemas del Sistema](#schemas-del-sistema)
4. [Validación y Constraints](#validación-y-constraints)
5. [Integración con LangChain](#integración-con-langchain)
6. [Error Handling](#error-handling)
7. [Testing de Schemas](#testing-de-schemas)
8. [Mejores Prácticas](#mejores-prácticas)

---

## ¿Por qué Structured Outputs?

### Problemas con Outputs de Texto Libre

```python
# ❌ Problemas con texto libre
response = llm.invoke("Classify this ticket: I can't log in")
# Output: "This looks like a technical issue with medium urgency..."

# Problemas:
# 1. ¿Cómo extraer "technical" de forma confiable?
# 2. ¿Qué pasa si dice "medio" en vez de "medium"?
# 3. ¿Cómo validar que urgency es válida?
# 4. ¿Cómo usar esto en lógica programática?
```

### Solución: Structured Outputs

```python
# ✅ Con structured outputs
classification = ticket_classifier.invoke("I can't log in")

# Output garantizado:
# TicketClassification(
#     intent="technical",
#     urgency="medium",
#     confidence=0.87,
#     rationale="Login issue detected"
# )

# Beneficios:
# 1. Type-safe: IDE autocomplete, type checking
# 2. Validación automática: confidence entre 0-1
# 3. Documentación: Schemas autodocumentados
# 4. Testing: Fácil crear mocks y fixtures
```

---

## Pydantic: Validación Type-Safe

### BaseModel Básico

```python
from pydantic import BaseModel, Field

class TicketClassification(BaseModel):
    """
    Clasificación estructurada de un ticket de soporte.
    
    Este schema garantiza que el LLM retorne datos en el formato esperado
    con validación automática de constraints.
    """
    intent: str = Field(
        ...,  # Required field
        description="Main topic/intent of the ticket."
    )
    urgency: str = Field(
        ...,
        description="Urgency level for prioritization."
    )
    confidence: float = Field(
        ...,
        ge=0.0,  # ← Greater than or equal to 0
        le=1.0,  # ← Less than or equal to 1
        description="Classifier confidence 0..1."
    )
    rationale: str = Field(
        ...,
        description="Short explanation of why this classification was chosen."
    )
```

### Tipos de Constraints

| Constraint | Descripción | Ejemplo |
|------------|-------------|---------|
| `ge` | Greater than or equal | `ge=0.0` |
| `le` | Less than or equal | `le=1.0` |
| `gt` | Greater than | `gt=0` |
| `lt` | Less than | `lt=100` |
| `min_length` | Longitud mínima string | `min_length=1` |
| `max_length` | Longitud máxima string | `max_length=500` |
| `regex` | Patrón regex | `regex=r"^\d{3}-\d{3}$"` |

---

## Schemas del Sistema

### 1. TicketClassification

**Propósito**: Clasificar la intención y urgencia del ticket.

```python
from typing import Literal

Intent = Literal["refund", "billing", "account", "technical", "reservation", "other"]
Urgency = Literal["low", "medium", "high"]

class TicketClassification(BaseModel):
    intent: Intent = Field(..., description="Main topic/intent of the ticket.")
    urgency: Urgency = Field(..., description="Urgency level for prioritization.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classifier confidence 0..1.")
    rationale: str = Field(..., description="Short explanation of why this classification was chosen.")
```

**Ejemplo de uso**:

```python
classification = TicketClassification(
    intent="billing",
    urgency="high",
    confidence=0.92,
    rationale="User mentions duplicate charge"
)

# Validación automática
try:
    TicketClassification(
        intent="invalid_intent",  # ❌ No está en Intent Literal
        urgency="high",
        confidence=1.5,  # ❌ Fuera del rango 0-1
        rationale="test"
    )
except ValidationError as e:
    print(e)
    # ValidationError: 2 validation errors for TicketClassification
    # intent
    #   Input should be 'refund', 'billing', 'account', ... (type=literal_error)
    # confidence
    #   Input should be less than or equal to 1.0 (type=less_than_equal)
```

### 2. RoutingDecision

**Propósito**: Decidir qué agente debe manejar el ticket.

```python
Route = Literal[
    "billing_agent",
    "account_agent",
    "tech_agent",
    "reservation_agent",
    "escalation_agent"
]

class RoutingDecision(BaseModel):
    route: Route = Field(
        ...,
        description="Which specialist should handle this ticket next."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Routing confidence 0..1."
    )
    rationale: str = Field(
        ...,
        description="Why this route is best."
    )
    needs_more_info: bool = Field(
        default=False,
        description="True if the system must ask clarifying questions before acting."
    )
```

**Ejemplo de uso**:

```python
routing = RoutingDecision(
    route="billing_agent",
    confidence=0.88,
    rationale="Clear billing issue with high confidence",
    needs_more_info=False
)

# Acceso type-safe
if routing.needs_more_info:
    # Pedir más información al usuario
    pass
elif routing.confidence < 0.6:
    # Escalar a humano
    pass
else:
    # Proceder con el agente seleccionado
    agent = agents[routing.route]
```

### 3. Tool Outputs

**Propósito**: Outputs estructurados de las tools.

```python
class AccountLookupOutput(BaseModel):
    ok: bool = True
    found: bool
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_blocked: Optional[bool] = None

class SubscriptionStatusOutput(BaseModel):
    ok: bool = True
    found: bool
    user_id: Optional[str] = None
    active_subscription: bool = False
    plan: Optional[str] = None
    status: Optional[str] = None
    renewal_date: Optional[str] = None

class ToolError(BaseModel):
    ok: bool = Field(default=False)
    error: str
    details: Optional[Dict[str, Any]] = None
```

**Ejemplo de uso**:

```python
# Tool exitosa
result = account_lookup("user@example.com")
# AccountLookupOutput(ok=True, found=True, user_id="123", ...)

# Tool con error
result = account_lookup("invalid-email")
# ToolError(ok=False, error="invalid_email", details={"email": "invalid-email"})

# Manejo en agente
if not result["ok"]:
    return f"Error: {result['error']}"
```

---

## Validación y Constraints

### Constraints Numéricos

```python
class AnswerResponse(BaseModel):
    confidence: float = Field(
        ...,
        ge=0.0,      # ✅ CORRECTO: Mínimo 0.0
        le=1.0,      # ✅ CORRECTO: Máximo 1.0
        description="Validation between 0 and 1"
    )

# ❌ ERROR COMÚN (del revisor):
# confidence: float = Field(ge=0.0, le=0.0, ...)
# Esto hace que confidence SOLO pueda ser 0.0
```

### Default Factories

```python
from typing import List, Dict

class DocumentChunk(BaseModel):
    # ✅ CORRECTO
    document_ids: List[str] = Field(
        default_factory=list,  # ← Sin lambda
        description="List of document IDs"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,  # ← Sin lambda
        description="Document metadata"
    )

# ❌ INCORRECTO (del revisor):
# document_ids: List[str] = Field(default_factory=lambda: list, ...)
# Problema: lambda:list retorna la CLASE list, no una instancia []

# ❌ TAMBIÉN INCORRECTO:
# metadata: Dict[str, Any] = Field(default_factory=lambda: dict, ...)
```

**Por qué funciona sin lambda**:

```python
# default_factory espera un callable que retorne la instancia
# list() retorna []
# dict() retorna {}

# Equivalentes:
default_factory=list       # ✅ Mejor
default_factory=lambda: [] # ✅ Funciona pero verbose
default_factory=lambda: list  # ❌ Retorna la clase, no una instancia
```

### Validación Custom

```python
from pydantic import validator

class UserIntent(BaseModel):
    intent_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    
    @validator("reasoning")
    def reasoning_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Reasoning cannot be empty")
        return v.strip()
    
    @validator("intent_type")
    def intent_type_valid(cls, v):
        valid_intents = ["qa", "calculation", "summarization"]
        if v not in valid_intents:
            raise ValueError(f"Intent must be one of {valid_intents}")
        return v
```

---

## Integración con LangChain

### with_structured_output()

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

# Crear un LLM que retorna TicketClassification
ticket_classifier = llm.with_structured_output(TicketClassification)

# Uso
result = ticket_classifier.invoke("I was charged twice!")

# result es una instancia de TicketClassification
print(type(result))  # <class 'TicketClassification'>
print(result.intent)  # "billing"
print(result.confidence)  # 0.95
```

### Cómo Funciona

1. **Function Calling**: LangChain usa OpenAI function calling
2. **Schema Conversion**: Convierte Pydantic schema a JSON Schema
3. **Validation**: El LLM retorna JSON que se valida contra el schema
4. **Instantiation**: Se crea la instancia de Pydantic con los datos validados

### Prompt Engineering para Structured Outputs

```python
def classify_ticket(ticket_text: str) -> TicketClassification:
    prompt = f"""
You are a ticket classifier for a customer support system (CultPass).
Return a structured classification.

Ticket:
{ticket_text}

Guidelines:
- intent must be one of: refund, billing, account, technical, reservation, other
- urgency must be one of: low, medium, high
- confidence is 0..1 (float between 0 and 1)
- rationale should be short and practical (1-2 sentences)

IMPORTANT: Ensure confidence is between 0.0 and 1.0
""".strip()
    
    return ticket_classifier.invoke(prompt)
```

---

## Error Handling

### ValidationError

```python
from pydantic import ValidationError

try:
    classification = TicketClassification(
        intent="invalid",
        urgency="high",
        confidence=2.0,  # ❌ > 1.0
        rationale="test"
    )
except ValidationError as e:
    print(e.json(indent=2))
    # {
    #   "loc": ["confidence"],
    #   "msg": "ensure this value is less than or equal to 1.0",
    #   "type": "value_error.number.not_le"
    # }
```

### Handling en Producción

```python
def safe_classify(ticket_text: str) -> TicketClassification:
    """Classify with fallback en caso de error de validación"""
    try:
        return ticket_classifier.invoke(ticket_text)
    except ValidationError as e:
        # Log error
        logger.error(f"Validation error: {e}")
        
        # Fallback: clasificación de baja confianza
        return TicketClassification(
            intent="other",
            urgency="medium",
            confidence=0.3,  # Baja confianza → escalará
            rationale=f"Auto-fallback due to validation error: {e}"
        )
```

---

## Testing de Schemas

### Unit Tests

```python
import pytest
from pydantic import ValidationError

def test_classification_valid():
    """Test que datos válidos pasan la validación"""
    classification = TicketClassification(
        intent="billing",
        urgency="high",
        confidence=0.95,
        rationale="Clear billing issue"
    )
    assert classification.intent == "billing"
    assert classification.confidence == 0.95

def test_classification_confidence_bounds():
    """Test que confidence fuera de rango falla"""
    # Confidence > 1.0
    with pytest.raises(ValidationError) as exc_info:
        TicketClassification(
            intent="billing",
            urgency="high",
            confidence=1.5,  # ❌ Invalid
            rationale="test"
        )
    assert "less than or equal to 1.0" in str(exc_info.value)
    
    # Confidence < 0.0
    with pytest.raises(ValidationError):
        TicketClassification(
            intent="billing",
            urgency="high",
            confidence=-0.1,  # ❌ Invalid
            rationale="test"
        )

def test_classification_invalid_intent():
    """Test que intent inválido falla"""
    with pytest.raises(ValidationError):
        TicketClassification(
            intent="invalid_intent",  # ❌ No está en Literal
            urgency="high",
            confidence=0.9,
            rationale="test"
        )
```

### Integration Tests

```python
def test_classifier_returns_valid_schema():
    """Test que el LLM classifier retorna schema válido"""
    result = classify_ticket("I was charged twice")
    
    # Verificar que es del tipo correcto
    assert isinstance(result, TicketClassification)
    
    # Verificar que confidence está en rango
    assert 0.0 <= result.confidence <= 1.0
    
    # Verificar que intent es válido
    assert result.intent in ["refund", "billing", "account", "technical", "reservation", "other"]
    
    # Verificar que urgency es válido
    assert result.urgency in ["low", "medium", "high"]

def test_routing_decision_valid():
    """Test routing con clasificación válida"""
    classification = TicketClassification(
        intent="billing",
        urgency="high",
        confidence=0.9,
        rationale="test"
    )
    
    routing = decide_route("I was charged twice", classification)
    
    assert isinstance(routing, RoutingDecision)
    assert routing.route in ["billing_agent", "account_agent", "tech_agent", "reservation_agent", "escalation_agent"]
    assert 0.0 <= routing.confidence <= 1.0
```

---

## Mejores Prácticas

### ✅ DO

1. **Usar Literal para enums**:
   ```python
   Intent = Literal["billing", "technical", "other"]  # ✅
   # vs
   intent: str  # ❌ Permite cualquier string
   ```

2. **Agregar descriptions claras**:
   ```python
   confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence 0..1")
   ```

3. **Usar default_factory correctamente**:
   ```python
   tags: List[str] = Field(default_factory=list)  # ✅
   ```

4. **Documentar el schema**:
   ```python
   class MySchema(BaseModel):
       """
       Description de qué representa este schema.
       
       Usado por: X, Y, Z
       Validaciones: A, B, C
       """
   ```

5. **Testear validación**:
   ```python
   # Test happy path + edge cases + error cases
   ```

### ❌ DON'T

1. **No usar constraints imposibles**:
   ```python
   # ❌ le=0.0 + ge=0.0 → solo permite 0.0
   confidence: float = Field(ge=0.0, le=0.0)
   ```

2. **No usar lambda innecesarias**:
   ```python
   # ❌
   default_factory=lambda: list
   # ✅
   default_factory=list
   ```

3. **No ignorar ValidationError**:
   ```python
   try:
       obj = MySchema(**data)
   except ValidationError:
       pass  # ❌ Silent failure
   ```

4. **No usar tipos genéricos**:
   ```python
   intent: str  # ❌ Permite cualquier cosa
   intent: Literal["a", "b", "c"]  # ✅ Restringe opciones
   ```

---

## Ejemplo Completo: Test de Validación

```python
# test_validation.py

import pytest
from pydantic import ValidationError
from agentic.agents.agents import TicketClassification, RoutingDecision

class TestTicketClassification:
    """Tests para TicketClassification schema"""
    
    def test_valid_classification(self):
        """Test clasificación válida"""
        cls = TicketClassification(
            intent="billing",
            urgency="high",
            confidence=0.9,
            rationale="Clear billing issue"
        )
        assert cls.confidence == 0.9
    
    def test_confidence_out_of_bounds_high(self):
        """Test que confidence > 1.0 falla"""
        with pytest.raises(ValidationError) as exc_info:
            TicketClassification(
                intent="billing",
                urgency="high",
                confidence=1.5,
                rationale="test"
            )
        # Verificar mensaje de error específico
        errors = exc_info.value.errors()
        assert any("less than or equal to 1" in str(e) for e in errors)
    
    def test_confidence_out_of_bounds_low(self):
        """Test que confidence < 0.0 falla"""
        with pytest.raises(ValidationError):
            TicketClassification(
                intent="billing",
                urgency="high",
                confidence=-0.1,
                rationale="test"
            )
    
    def test_invalid_intent(self):
        """Test que intent inválido falla"""
        with pytest.raises(ValidationError):
            TicketClassification(
                intent="invalid_type",
                urgency="high",
                confidence=0.8,
                rationale="test"
            )
    
    def test_invalid_urgency(self):
        """Test que urgency inválido falla"""
        with pytest.raises(ValidationError):
            TicketClassification(
                intent="billing",
                urgency="critical",  # No está en ["low", "medium", "high"]
                confidence=0.8,
                rationale="test"
            )

class TestRoutingDecision:
    """Tests para RoutingDecision schema"""
    
    def test_valid_routing(self):
        """Test routing válido"""
        routing = RoutingDecision(
            route="billing_agent",
            confidence=0.85,
            rationale="High confidence billing issue",
            needs_more_info=False
        )
        assert routing.route == "billing_agent"
    
    def test_default_needs_more_info(self):
        """Test que needs_more_info default es False"""
        routing = RoutingDecision(
            route="tech_agent",
            confidence=0.7,
            rationale="test"
            # needs_more_info no especificado
        )
        assert routing.needs_more_info == False
    
    def test_invalid_route(self):
        """Test que route inválido falla"""
        with pytest.raises(ValidationError):
            RoutingDecision(
                route="invalid_agent",
                confidence=0.8,
                rationale="test"
            )
```

**Ejecutar tests**:

```bash
pytest test_validation.py -v
```

---

## Referencias

- [Pydantic Documentation](https://docs.pydantic.dev/latest/)
- [LangChain Structured Outputs](https://python.langchain.com/docs/modules/model_io/chat/structured_output/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- Implementación en `agentic/agents/agents.py`
- Tool schemas en `agentic/tools/tools.py`
