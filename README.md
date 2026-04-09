# Palace - Framework de Agentes Inteligentes para Desarrollo de Software

## Descripción

**Palace** es un framework multi-agente diseñado para automatizar y asistir en el desarrollo de software. Combina múltiples agentes especializados con un orquestador central, memoria vectorial y gestión de contexto por proyecto.

## Arquitectura

El framework está organizado en capas:

- **Core**: Componentes base, excepciones, configuración y contratos
- **Agents**: Agentes especializados (Backend, Frontend, DevOps, DBA, QA, etc.)
- **Memory**: Almacén vectorial y gestión de memoria episódica/semántica
- **Context**: Gestión de contexto por proyecto y sesiones
- **API**: Interfaz REST con FastAPI
- **CLI**: Interfaz de línea de comandos
- **Pipelines**: Flujos de trabajo predefinidos
- **Tools**: Herramientas compartidas por los agentes

## Modelos Disponibles

| Agente | Modelo | Uso |
|--------|--------|-----|
| Orquestador | `qwen3.5` | Coordinación y planificación |
| DevOps | `qwen3.5` | Pipelines y despliegue |
| Backend | `qwen3-coder-next` | Desarrollo backend |
| Frontend | `qwen3-coder-next` | Desarrollo frontend |
| Infra | `qwen3-coder-next` | Infraestructura como código |
| DBA | `deepseek-v3.2` | Base de datos y migraciones |
| QA | `gemma4:31b` | Calidad y testing |
| Diseñador | `mistral-large` | Diseño UI/UX |
| Reviewer | `mistral-large` | Revisión de código |

## Estructura del Proyecto

```
framework-palace/
├── src/palace/
│   ├── core/           # Componentes base del framework
│   ├── agents/        # Agentes especializados
│   ├── memory/        # Memoria vectorial y persistencia
│   ├── context/       # Gestión de contexto por proyecto
│   ├── api/           # API REST (FastAPI)
│   ├── cli/           # Interfaz de línea de comandos
│   ├── pipelines/     # Flujos de trabajo
│   ├── tools/         # Herramientas compartidas
│   └── models/        # Modelos de datos (Pydantic)
├── tests/             # Tests unitarios e integración
├── docs/              # Documentación
├── examples/          # Ejemplos de uso
├── pyproject.toml     # Configuración del proyecto
└── README.md          # Este archivo
```

## Instalación

```bash
# Clonar el repositorio
git clone <repository-url>
cd framework-palace

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -e .
```

## Uso Rápido

### CLI

```bash
# Inicializar un nuevo proyecto
palace init mi-proyecto

# Ejecutar una tarea
palace run "Crear endpoint REST para gestión de usuarios"

# Ver estado del proyecto
palace status
```

### API

```python
from palace import PalaceClient

client = PalaceClient()
result = await client.execute(
    project_id="mi-proyecto",
    task="Crear endpoint REST para gestión de usuarios"
)
```

## Configuración

Ver `.env.example` para las variables de entorno necesarias.

## Licencia

MIT License
```
