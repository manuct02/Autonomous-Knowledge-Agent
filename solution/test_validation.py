"""
Tests de validación para UDA-Hub

Estos tests demuestran que:
1. Los schemas Pydantic validan correctamente los constraints
2. Los bounds de confidence (0-1) se respetan
3. Los intents y routes inválidos son rechazados
4. Las tools manejan errores correctamente
"""

import pytest
from pydantic import ValidationError
from agentic.agents.agents import TicketClassification, RoutingDecision
from agentic.tools.tools import account_lookup, subscription_status


class TestTicketClassificationValidation:
    """Tests para validación de TicketClassification schema"""
    
    def test_valid_classification(self):
        """Test que clasificación válida pasa la validación"""
        classification = TicketClassification(
            intent="billing",
            urgency="high",
            confidence=0.95,
            rationale="Clear billing issue with duplicate charge"
        )
        
        assert classification.intent == "billing"
        assert classification.urgency == "high"
        assert classification.confidence == 0.95
        assert isinstance(classification.rationale, str)
    
    def test_confidence_must_be_between_0_and_1(self):
        """
        Test crítico del revisor: confidence debe estar entre 0.0 y 1.0
        
        El revisor encontró que el schema tenía le=0.0 en vez de le=1.0,
        lo cual haría que confidence solo pudiera ser 0.0.
        """
        # Confidence válida en el rango
        valid = TicketClassification(
            intent="billing",
            urgency="high",
            confidence=0.5,
            rationale="test"
        )
        assert 0.0 <= valid.confidence <= 1.0
        
        # Confidence = 0.0 debe ser válida
        min_valid = TicketClassification(
            intent="billing",
            urgency="high",
            confidence=0.0,
            rationale="test"
        )
        assert min_valid.confidence == 0.0
        
        # Confidence = 1.0 debe ser válida
        max_valid = TicketClassification(
            intent="billing",
            urgency="high",
            confidence=1.0,
            rationale="test"
        )
        assert max_valid.confidence == 1.0
    
    def test_confidence_above_1_raises_error(self):
        """Test que confidence > 1.0 falla validación"""
        with pytest.raises(ValidationError) as exc_info:
            TicketClassification(
                intent="billing",
                urgency="high",
                confidence=1.5,  # ❌ Fuera del rango
                rationale="test"
            )
        
        # Verificar que el error menciona el constraint
        error_msg = str(exc_info.value)
        assert "less than or equal" in error_msg or "1.0" in error_msg
    
    def test_confidence_below_0_raises_error(self):
        """Test que confidence < 0.0 falla validación"""
        with pytest.raises(ValidationError):
            TicketClassification(
                intent="billing",
                urgency="high",
                confidence=-0.1,  # ❌ Fuera del rango
                rationale="test"
            )
    
    def test_invalid_intent_rejected(self):
        """Test que intent fuera del Literal es rechazado"""
        with pytest.raises(ValidationError) as exc_info:
            TicketClassification(
                intent="invalid_intent",  # ❌ No está en el Literal
                urgency="high",
                confidence=0.8,
                rationale="test"
            )
        
        # El error debe mencionar los valores válidos
        error_msg = str(exc_info.value)
        assert "refund" in error_msg or "billing" in error_msg
    
    def test_invalid_urgency_rejected(self):
        """Test que urgency fuera del Literal es rechazado"""
        with pytest.raises(ValidationError):
            TicketClassification(
                intent="billing",
                urgency="critical",  # ❌ No está en ["low", "medium", "high"]
                confidence=0.8,
                rationale="test"
            )
    
    def test_all_valid_intents(self):
        """Test que todos los intents válidos funcionan"""
        valid_intents = ["refund", "billing", "account", "technical", "reservation", "other"]
        
        for intent in valid_intents:
            classification = TicketClassification(
                intent=intent,
                urgency="medium",
                confidence=0.8,
                rationale="test"
            )
            assert classification.intent == intent
    
    def test_all_valid_urgencies(self):
        """Test que todos los urgencies válidos funcionan"""
        valid_urgencies = ["low", "medium", "high"]
        
        for urgency in valid_urgencies:
            classification = TicketClassification(
                intent="billing",
                urgency=urgency,
                confidence=0.8,
                rationale="test"
            )
            assert classification.urgency == urgency


class TestRoutingDecisionValidation:
    """Tests para validación de RoutingDecision schema"""
    
    def test_valid_routing_decision(self):
        """Test que routing válido pasa la validación"""
        routing = RoutingDecision(
            route="billing_agent",
            confidence=0.88,
            rationale="High confidence billing issue",
            needs_more_info=False
        )
        
        assert routing.route == "billing_agent"
        assert routing.confidence == 0.88
        assert routing.needs_more_info == False
    
    def test_routing_confidence_bounds(self):
        """Test que confidence de routing respeta bounds 0-1"""
        # Válido en el rango
        valid = RoutingDecision(
            route="tech_agent",
            confidence=0.7,
            rationale="test"
        )
        assert 0.0 <= valid.confidence <= 1.0
        
        # Fuera del rango debe fallar
        with pytest.raises(ValidationError):
            RoutingDecision(
                route="tech_agent",
                confidence=1.2,
                rationale="test"
            )
    
    def test_invalid_route_rejected(self):
        """Test que route inválido es rechazado"""
        with pytest.raises(ValidationError):
            RoutingDecision(
                route="invalid_agent",  # ❌ No está en el Literal
                confidence=0.8,
                rationale="test"
            )
    
    def test_needs_more_info_defaults_to_false(self):
        """Test que needs_more_info default es False"""
        routing = RoutingDecision(
            route="account_agent",
            confidence=0.75,
            rationale="test"
            # needs_more_info no especificado
        )
        
        assert routing.needs_more_info == False
    
    def test_all_valid_routes(self):
        """Test que todos los routes válidos funcionan"""
        valid_routes = [
            "billing_agent",
            "account_agent",
            "tech_agent",
            "reservation_agent",
            "escalation_agent"
        ]
        
        for route in valid_routes:
            routing = RoutingDecision(
                route=route,
                confidence=0.8,
                rationale="test"
            )
            assert routing.route == route


class TestToolOutputValidation:
    """Tests para validación de tool outputs"""
    
    def test_account_lookup_with_invalid_email(self):
        """Test que account_lookup rechaza email inválido"""
        result = account_lookup.invoke({"email": "not-an-email"})
        
        # Debe retornar error, NO lanzar excepción
        assert result["ok"] == False
        assert result["error"] == "invalid_email"
    
    def test_account_lookup_with_valid_email(self):
        """Test que account_lookup con email válido retorna structure correcta"""
        # Este test requiere que la DB esté configurada
        # Si no existe el usuario, debe retornar found=False
        result = account_lookup.invoke({"email": "test@example.com"})
        
        assert "ok" in result
        assert "found" in result
        
        # Si encontrado, debe tener estos campos
        if result.get("found"):
            assert "user_id" in result
            assert "email" in result
    
    def test_subscription_status_missing_params(self):
        """Test que subscription_status sin user_id ni email retorna error"""
        result = subscription_status.invoke({})
        
        assert result["ok"] == False
        assert "error" in result


class TestEndToEndValidation:
    """Tests end-to-end de validación"""
    
    def test_classification_to_routing_flow(self):
        """Test que classification válida puede usarse en routing"""
        from agentic.agents.agents import decide_route
        
        # Crear clasificación válida
        classification = TicketClassification(
            intent="billing",
            urgency="high",
            confidence=0.9,
            rationale="Duplicate charge reported"
        )
        
        # Usarla en routing (no debe fallar)
        routing = decide_route(
            ticket_text="I was charged twice",
            classification=classification
        )
        
        # Verificar que routing es válido
        assert isinstance(routing, RoutingDecision)
        assert routing.route in [
            "billing_agent",
            "account_agent",
            "tech_agent",
            "reservation_agent",
            "escalation_agent"
        ]
        assert 0.0 <= routing.confidence <= 1.0
    
    def test_low_confidence_triggers_escalation(self):
        """Test que baja confianza escala automáticamente"""
        from agentic.agents.agents import decide_route
        
        # Clasificación con baja confianza
        classification = TicketClassification(
            intent="other",
            urgency="medium",
            confidence=0.4,  # < 0.55 threshold
            rationale="Unclear intent"
        )
        
        routing = decide_route(
            ticket_text="Something is wrong",
            classification=classification
        )
        
        # Debe escalar por baja confianza
        assert routing.route == "escalation_agent"


class TestSchemaDocumentation:
    """Tests que verifican que los schemas están bien documentados"""
    
    def test_classification_has_fields(self):
        """Test que TicketClassification tiene todos los campos requeridos"""
        schema = TicketClassification.model_json_schema()
        required_fields = {"intent", "urgency", "confidence", "rationale"}
        assert required_fields.issubset(set(schema["properties"].keys()))
    
    def test_classification_fields_have_descriptions(self):
        """Test que todos los campos tienen descriptions"""
        schema = TicketClassification.model_json_schema()
        
        for field_name, field_info in schema["properties"].items():
            assert "description" in field_info, f"Field {field_name} missing description"
    
    def test_routing_fields_have_descriptions(self):
        """Test que RoutingDecision fields tienen descriptions"""
        schema = RoutingDecision.model_json_schema()
        
        for field_name, field_info in schema["properties"].items():
            assert "description" in field_info, f"Field {field_name} missing description"


# Ejecutar con: pytest test_validation.py -v
# Para ver coverage: pytest test_validation.py --cov=agentic --cov-report=html
