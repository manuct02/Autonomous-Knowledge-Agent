# Agente de Decisión Universal (ADU)

## Resumen

Somos responsables de la construcción de **UDA-Hub**, un Agente de Decisión Universal diseñado capaz de enchufarse a sistemas de soporte del cliente existentes como (Zendesk, Intercom, FreshDesk, internal CRMs) y de resolver tickets de forma inteligente. Pero no es un bot de FAQ.

Se trata de diseñar un sistema agéntico que pueda:
  - Entender los tickets del cliente entre canales
  - Decidir qué agente o tool usar en según qué caso/momento
  - Recuperar o inferir respuestas cuando fuera posible
  - Escalar o resumir issues cuando sea neceario
  - Aprender de interacciones pasadas actualizando la memoria a largo plazo

### Introducción al proyecto

#### **Capacidades clave**: 
**1. Arquitectura multi-agéntica con LangGraph**: diseñar y orquestar agentes especializados (Supervisor, Clasificador, Solventador, Escalador...)

**2. Manejo del Input**: aceptar tickets de soporte entrantes en lenguaje natural con metadatos (plataforma, urgencia, historial)

**3. Decisión del routing y la resolución del ticket**:
  - enrutar tickets al agente adecuado basado en la clasificación 
  - recuperar el conocimiento relevante de un RAG si fuese necesario
  - resolver o escalar basándose en la confienza o el contexto

**4. Integración de Memoria**:
- mantiene el estado durante los pasos de la ejecución
- se usa la memoria a corto plazo a modo de contexto para mantener la conversación coherente durante la misma sesión
- almacenar y recall la memoria a largo plazo para preferncias, por ejemplo

#### **Inputs:**
- Tickets entrantes de soporte (texto + metadatos)
- Conocimeinto básico interno (FAQ, tickets previos)
- Tools internas opcionales (reembolso)
- Almacenamiento de memoria (para conversaciones previas y soluciones)

#### **Deliverables:**

Un sistema multi-agéntico impulsado por LangGraph que:
- Entienda los tickets
- Enrute al agente correcto con tools
- Resuelva o escale basándose en la lógica de decisión
- Use la memoria correctamente

## Instrucciones
Así debe lucir la distribución de los folders

```
starter/
├── agentic/
│   ├── agents/
│   ├── design/
│   ├── tools/
│   └── workflow.py
├── data/
│   ├── core/
│   ├── external/
│   └── models/
├── .env
├── 01_external_db_setup.ipynb
├── 02_core_db_setup.ipynb
├── 03_agentic_app.ipynb
└── utils.py
```
### Diseño

1. Comenzamos diseñando la solución. A continuación la implementación de la misma.
2. Colocar toda la documentación y diagramas sobre el diseño del sistema agéntico dentro de `agentic/design`.

### Setup

1. Correr el notebook `01_external_db_setup.ipynb` para tener todos los datos relacionados con la cuenta **Cultpass** . Se trata del primer cliente que adquirió **Uda-hub**.
2. Correr el 0`2_core_db_setup.ipynb` para obtener toda la documentación relacionada con la aplicación Uda-hub, incluyendo los archivos "recibidos" de Cultpass como `cultpass_articles.jsonl`
3. Necesitamos expandir culpass_articles de 4 a por lo menos **14 artículos**. Asegurar que tenemos varios topics para el sistema agéntico

### Workflow Agéntico

1. Desarrollamos los agentes en `agentic/agents` y las tools en `agentic/tools`.
2. Desarrollamos la orquestación del workflow en el `workflow.py`. Ya hay uno de muestra, pero no vale usarlo. **NO USAR EL WORKFLOW PRECONSTRUIDO**

3. Cuando desarrollemos las tool que abstraigan las base de datos para retrieval o acciones, hay que tener en cuenta los relative/absolute paths. Nos recomienda usar algo del palo MCP servers para las tools
4. Si usamos un RAG hay que documentar cómo se usa y cómo funciona
5. Para memoria a corto plazo (sesión), usamos thread_id. Para memoria a alrgo plazo mejor usar la búsqueda semántica.

### Run

1. Hay una función `chat_interface()` dentro de `utils.py`. 
2. No estamos obligados a usar el puñetero notebook 3, podemos crear un módulo .py per siempre llamándolo `03_agentic_app.py`.
3. Debemos crear **casos de prueba** para pasarlo. 