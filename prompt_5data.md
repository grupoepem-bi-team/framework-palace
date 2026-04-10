# Prompt para generar los 5 archivos de `/ai_context/`

Copia y pega esto en tu herramienta de IA favorita (ChatGPT, Claude, Ollama, etc.), reemplazando la sección `[INFORMACIÓN DE TU PROYECTO]` con los datos reales:

---

```
Actuá como arquitecto de software senior. Vas a analizar un proyecto existente y generar 5 archivos de contexto para el framework Palace.

Estos archivos le permiten a un sistema multi-agente entender el proyecto y generar código que encaja perfectamente sin necesidad de aclaraciones.

──────────────────────────────────────
INFORMACIÓN DE TU PROYECTO (reemplazar)
──────────────────────────────────────

Nombre del proyecto: [ej: "Sistema de Reportes BI"]
Descripción breve: [ej: "Plataforma de Business Intelligence para clientes corporativos"]
Lenguaje principal: [ej: Python]
Framework backend: [ej: FastAPI]
Framework frontend: [ej: React + TypeScript]
Base de datos: [ej: PostgreSQL]
ORM: [ej: SQLAlchemy 2.0 async]
Autenticación: [ej: OAuth2 con Azure AD]
Despliegue: [ej: Docker + Azure App Service]
Estructura de carpetas:
[ej:]
src/
  api/v1/          # Endpoints REST
  models/          # Modelos SQLAlchemy
  services/        # Lógica de negocio
  schemas/         # Pydantic schemas
  core/            # Config, seguridad, dependencias
tests/
frontend/
  src/
    components/
    pages/
    services/
    hooks/
──────────────────────────────────────

REGLAS DE GENERACIÓN:

1. Cada archivo debe ser ESPECÍFICO del proyecto, no genérico.
2. Incluir nombres reales de módulos, tablas, endpoints, patrones.
3. Mencionar librerías con versiones si se conocen.
4. Ser conciso pero completo — no poner filler, cada línea debe aportar valor.
5. Usar español o inglés según el proyecto (si el código está en inglés, escribir en inglés).
6. Los archivos son Markdown pero el contenido es técnico y preciso.

──────────────────────────────────────

GENERÁ LOS SIGUIENTES 5 ARCHIVOS:

════════════════════════════════════════
ARCHIVO 1: architecture.md
════════════════════════════════════════

Describí la arquitectura del proyecto. Incluí:

- Overview: propósito del sistema y usuarios principales
- Diagrama de capas (API → Services → Models → DB)
- Patrones arquitectónicos usados (Repository, CQRS, Event-driven, etc.)
- Cómo se comunican los componentes (REST, eventos, colas)
- Flujo principal de un request (del cliente a la base de datos y vuelta)
- Componentes externos integrados (APIs de terceros, servicios cloud)
- Diagrama de despliegue si aplica (containers, servicios)

Formato:
# Architecture — [Nombre del Proyecto]

## Overview
[1-2 párrafos]

## Capas
[cada capa con su responsabilidad y ubicación en el código]

## Patrones
[patrones de diseño usados y dónde]

## Flujo Principal
[ejemplo de un request completo]

## Integraciones Externas
[APIs, servicios externos, herramientas]

## Despliegue
[cómo se despliega, ambientes]


════════════════════════════════════════
ARCHIVO 2: stack.md
════════════════════════════════════════

Listá TODA la tecnología usada. Incluí:

- Lenguajes y versiones
- Frameworks con versiones
- Librerías principales (las que se usan en código productivo, no dev deps)
- Herramientas de desarrollo (linters, formatters, test runners)
- Servicios de infraestructura (bases de datos, caches, message queues)
- APIs externas consumidas

Formato:
# Stack Tecnológico — [Nombre del Proyecto]

## Backend
- [Lenguaje] [versión]
- [Framework] [versión]
- [ORM/DB driver]
- [Librerías principales con propósito]

## Frontend
- [Framework] [versión]
- [Librerías UI]
- [State management]
- [HTTP client]

## Infraestructura
- [Base de datos]
- [Cache]
- [Message queue]
- [CI/CD]

## Herramientas de Desarrollo
- [Linter/formatter]
- [Test framework]
- [Type checker]

## APIs Externas
- [Servicio] — [propósito]


════════════════════════════════════════
ARCHIVO 3: conventions.md
════════════════════════════════════════

Definí TODAS las convenciones del proyecto. Incluí:

- Naming: variables, funciones, clases, archivos, tablas, columnas
- Estructura de código: cómo organizar imports, funciones, clases
- Endpoints REST: formato de URLs, métodos HTTP, códigos de respuesta
- Base de datos: nombres de tablas, columnas, migraciones
- Testing: qué testear, cómo nombrar tests, dónde ponerlos
- Git: formato de commits, estrategia de branches
- Documentación: docstrings, comentarios, README

Formato:
# Convenciones de Código — [Nombre del Proyecto]

## Nombres
- Variables: [snake_case / camelCase]
- Funciones: [snake_case / camelCase]
- Clases: [PascalCase]
- Archivos: [snake_case / kebab-case]
- Tablas DB: [snake_case plural / singular]
- Columnas DB: [snake_case]

## Estructura de Código
- [orden de imports]
- [cómo organizar funciones dentro de un archivo]
- [máximo de líneas por archivo / función]

## API REST
- URLs en plural: /api/v1/resources
- Respuestas exitosas: 200, 201, 204
- Errores: 400, 401, 403, 404, 422, 500
- Formato de error: {"detail": "mensaje"}
- Paginación: ?page=1&page_size=20

## Base de Datos
- Migraciones con [Alembic / Django / etc.]
- Soft delete con columna deleted_at
- Timestamps: created_at, updated_at

## Testing
- Framework: pytest
- Nombres: test_[módulo]_[escenario]_[resultado_esperado]
- Cobertura mínima: [X]%
- Fixtures en conftest.py

## Git
- Commits: tipo(scope): descripción
  - feat, fix, docs, refactor, test, chore
- Branches: main, develop, feature/*, hotfix/*

## Documentación
- Docstrings en [Google / NumPy / Sphinx] style
- [Qué se documenta y qué no]


════════════════════════════════════════
ARCHIVO 4: decisions.md
════════════════════════════════════════

Documentá las decisiones arquitectónicas tomadas (ADRs). Incluí:

- Decisiones de tecnología (por qué se eligió X sobre Y)
- Decisiones de arquitectura (por qué se separó en microservicios o monolito)
- Decisiones de seguridad (autenticación, autorización, encriptación)
- Decisiones de performance (caching, async, pagination)
- Decisiones de infraestructura (cloud, containers, CI/CD)
- Por cada decisión: contexto, decisión, consecuencias

Formato:
# Decisiones Arquitectónicas — [Nombre del Proyecto]

## ADR-001: [Título de la decisión]
- **Estado:** [Aceptada / En revisión / Deprecada]
- **Contexto:** [Por qué se necesitaba tomar esta decisión]
- **Decisión:** [Qué se decidió]
- **Consecuencias:** [Impacto positivo y negativo]

## ADR-002: [Título de la decisión]
- **Estado:** ...
- **Contexto:** ...
- **Decisión:** ...
- **Consecuencias:** ...

[Continuar con todas las decisiones importantes]


════════════════════════════════════════
ARCHIVO 5: constraints.md
════════════════════════════════════════

Documentá lo que NO se puede cambiar. Incluí:

- Requisitos del cliente que son fijos
- Limitaciones de infraestructura
- Compliance y regulaciones
- Performance: latencia, throughput, concurrencia
- Seguridad: autenticación, autorización, encriptación
- Compatibilidad: versiones, browsers, APIs
- Lo que se hace y lo que NO se hace

Formato:
# Restricciones del Proyecto — [Nombre del Proyecto]

## Requisitos del Cliente
- [Los que NO se negocian]

## Performance
- Latencia máxima: [X]ms para el 95% de requests
- Usuarios concurrentes: mínimo [X]
- Tiempo máximo de respuesta para reports: [X]s

## Seguridad
- Autenticación: [método, NO se cambia]
- Autorización: [método]
- Datos sensibles: [qué se encripta y cómo]
- HTTPS obligatorio

## Infraestructura
- Base de datos: [PostgreSQL / etc., NO se cambia]
- Deployment: [Docker / etc.]
- Ambientes: dev, staging, producción

## Regulaciones y Compliance
- [Si aplica: GDPR, SOC2, etc.]

## Compatibilidad
- Python [versión]+, no se soporta [versión anterior]
- Navegadores: [lista]
- API versioning: [estrategia]

## Lo que NO hacemos
- [Lista explícita de cosas que se decidieron no incluir]

──────────────────────────────────────

IMPORTANTE:
- Basate en la información provista arriba. Si falta algo, inferilo del contexto.
- Sé específico. "Usamos Python" no sirve. "Usamos Python 3.11+ con FastAPI 0.109+ para la API REST async" sí.
- Cada decisión debe tener contexto y justificación real.
- Las convenciones deben reflejar CÓMO se escribe código realmente en este proyecto, no un ideal genérico.
- Las restricciones deben ser las REALES del proyecto, no teóricas.
```

---

## Cómo usarlo

1. **Reemplazá** la sección `[INFORMACIÓN DE TU PROYECTO]` con los datos reales
2. **Pegá** el prompt completo en tu IA de preferencia
3. **Revisá** los 5 archivos generados y ajustá lo que no sea exacto
4. **Guardá** cada archivo en `tu-proyecto/ai_context/`
5. **Corré** `palace attach mi-proyecto --path .`

Cuanto más completa y precisa sea la información que pongas en la sección de reemplazo, mejor será el resultado. Los 5 archivos son la "personalidad" del proyecto — si están bien hechos, Palace genera código que encaja sin necesidad de correcciones.