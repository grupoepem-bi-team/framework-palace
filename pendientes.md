# Tareas Pendientes - Palace Framework

Este documento lista las tareas pendientes organizadas por módulo, basadas en el análisis del código existente y los requerimientos del [canonico.md](./canonico.md) y [modules.md](./modules.md).

**Última actualización:** 2025-04-09  
**Estado:** [Ver terminado.md](./terminado.md) para lo completado.

---

## 📋 Resumen de Prioridades

| Prioridad | Módulo | Descripción |
|-----------|--------|-------------|
| 🟡 Media | Módulo 8 (API) | Endpoints REST para exponer funcionalidad |
| 🟡 Media | Módulo 9 (CLI) | Comandos CLI para interacción |
| 🟢 Baja | Módulo 7 (Pipeline) | Flujos de trabajo avanzados |
| 🟢 Baja | Módulo 11 (Refinamiento) | Mejoras de robustez y optimización |

---

## ✅ Módulo 4: Agentes — COMPLETADO

**Estado:** ✅ Completado  
**Ubicación:** `src/palace/agents/`

Todos los agentes han sido implementados con los métodos `run`, `can_handle` y `_build_system_prompt`. Ver [terminado.md](./terminado.md) para detalles.

---

## 🗂️ Módulo 6: Contexto — ✅ COMPLETADO

**Estado:** ✅ Completado  
**Ubicación:** `src/palace/context/`

### Componentes Implementados

#### Project Loader (`loader.py`)
- [x] Implementar clase `ProjectLoader`
- [x] Carga de archivos desde directorio `/ai_context/`
- [x] Soporte para archivos:
  - [x] `architecture.md` - Documentación arquitectónica
  - [x] `stack.md` - Stack tecnológico
  - [x] `conventions.md` - Convenciones de código
  - [x] `decisions.md` - Decisiones arquitectónicas (ADRs)
  - [x] `constraints.md` - Restricciones del proyecto
- [x] Parseo inteligente de markdown a estructuras de datos
- [x] Cacheo de archivos cargados para mejor performance
- [x] Estimación de tokens por archivo

#### Context Builder (`builder.py`)
- [x] Implementar clase `ContextBuilder`
- [x] Combinar múltiples fuentes de contexto:
  - [x] Contexto del proyecto (archivos cargados)
  - [x] Memoria relevante (vector store / RAG)
  - [x] Sesión actual (historial de conversación)
  - [x] Tarea actual (objetivo, requisitos)
- [x] Presupuesto de tokens distribuido (10% sistema, 30% proyecto, 30% memoria, 20% sesión, 10% tarea)
- [x] Generar prompt estructurado para agentes
- [x] Soporte para límites de tokens (truncamiento inteligente por sección)
- [x] Flujo de 6 pasos alineado con canonico.md

#### Context Retriever (`retriever.py`)
- [x] Implementar clase `ContextRetriever`
- [x] Búsqueda semántica por tipo de memoria (SEMANTIC, EPISODIC, PROCEDURAL)
- [x] `RetrievalConfig` con parámetros configurables (top_k, min_relevance, max_tokens)
- [x] Filtrado por relevancia mínima
- [x] Boost de recencia para entradas recientes
- [x] Deduplicación de contenido
- [x] Truncamiento inteligente a límite de tokens
- [x] Recuperación específica por rol de agente (`retrieve_for_agent()`)
- [x] Recuperación de contexto de proyecto

#### Session Manager (`session.py`)
- [x] Implementar clase `SessionManager`
- [x] `SessionState` con estados: ACTIVE, IDLE, SUMMARIZED, EXPIRED, CLOSED
- [x] Gestión de historial de mensajes con límite configurable
- [x] Sumarización automática cuando se alcanza umbral de mensajes
- [x] Formato de contexto reciente para prompts de agentes
- [x] Limpieza de sesiones expiradas por TTL
- [x] Evicción LRU cuando se excede la capacidad

#### Tipos de Contexto (`types.py`)
- [x] `ContextType` — Enum con 11 tipos de contexto
- [x] `ContextEntry` — Entrada individual con relevancia y tokens
- [x] `RetrievedContext` — Resultado de búsqueda con estadísticas
- [x] `SessionConfig` — Configuración de sesión
- [x] `ProjectConfig` — Configuración de proyecto específica para contexto

#### Mejoras al ContextManager (`manager.py`)
- [x] Implementar `_load_existing_projects()` — Carga desde registro en memoria
- [x] Implementar `_load_project_from_memory()` — Reconstruye ProjectContext desde JSON
- [x] Implementar `update_project_context()` — Actualización campo por campo con persistencia
- [x] Gestión de caché con TTL y estadísticas

#### Integración con Memoria
- [x] Conectar `ContextRetriever` con `MemoryStore` para recuperación de contexto
- [x] Implementar RAG (Retrieval Augmented Generation) para búsqueda semántica
- [x] Recuperación específica por rol de agente con priorización de tipos de memoria

---

## ⚙️ Módulo 7: Pipeline

**Estado:** ❌ No implementado  
**Ubicación:** `src/palace/pipelines/`

### Tareas Pendientes

- [ ] Diseñar arquitectura de pipelines (flujos de trabajo)
- [ ] Implementar clase base `Pipeline` en `pipelines/base.py`
- [ ] Crear pipelines específicos:
  - [ ] `DevelopmentPipeline` - Para desarrollo de features
  - [ ] `BugFixPipeline` - Para corrección de bugs
  - [ ] `RefactoringPipeline` - Para refactorizaciones
  - [ ] `ReviewPipeline` - Para revisiones de código
- [ ] Implementar steps/interfaces para cada etapa del pipeline
- [ ] Integrar pipelines con orquestador de agentes
- [ ] Añadir sistema de condiciones y branching en pipelines
- [ ] Implementar monitoreo y logging de ejecución de pipelines
- [ ] Crear API para gestionar pipelines (iniciar, pausar, cancelar)

---

## 🌐 Módulo 8: API

**Estado:** ⚠️ Parcialmente implementado  
**Ubicación:** `src/palace/api/`

### Tareas Pendientes

#### Endpoints faltantes en `main.py`
- [ ] `/tasks` - Gestión de tareas
  - [ ] `POST /tasks` - Crear y ejecutar tarea
  - [ ] `GET /tasks/{task_id}` - Obtener estado de tarea
  - [ ] `GET /tasks` - Listar tareas
  - [ ] `DELETE /tasks/{task_id}` - Cancelar tarea
- [ ] `/projects` - Gestión de proyectos
  - [ ] `POST /projects` - Crear proyecto
  - [ ] `GET /projects/{project_id}` - Obtener proyecto
  - [ ] `GET /projects` - Listar proyectos
  - [ ] `POST /projects/{project_id}/load` - Cargar contexto de proyecto
- [ ] `/memory` - Gestión de memoria
  - [ ] `POST /memory/search` - Buscar en memoria
  - [ ] `POST /memory` - Añadir a memoria
  - [ ] `GET /memory/{memory_id}` - Obtener de memoria
  - [ ] `DELETE /memory/{memory_id}` - Eliminar de memoria
- [ ] `/agents` - Información de agentes
  - [ ] `GET /agents` - Listar agentes disponibles
  - [ ] `GET /agents/{agent_id}` - Obtener estado de agente
  - [ ] `POST /agents/{agent_id}/execute` - Ejecutar tarea en agente específico

#### Mejoras de API
- [ ] Añadir autenticación y autorización (si es necesario)
- [ ] Implementar rate limiting
- [ ] Añadir documentación OpenAPI/Swagger completa
- [ ] Implementar WebSockets para updates en tiempo real
- [ ] Añadir endpoints de métricas y monitoreo
- [ ] Implementar validación robusta de inputs con Pydantic
- [ ] Añadir manejo de errores HTTP específicos

#### Tests de API
- [ ] Crear tests para cada endpoint
- [ ] Implementar fixtures para testing
- [ ] Añadir tests de integración con agentes y memoria

---

## 💻 Módulo 9: CLI

**Estado:** ⚠️ Parcialmente implementado  
**Ubicación:** `src/palace/cli/`

### Tareas Pendientes

#### Comandos faltantes en `main.py`
- [ ] `run` - Ejecutar una tarea
  - [ ] `palace run "Crear endpoint REST para usuarios"`
  - [ ] Opciones: `--project`, `--agent`, `--async`
- [ ] `attach` - Adjuntar a proyecto existente
  - [ ] `palace attach my-project`
  - [ ] Opciones: `--path`, `--context`
- [ ] `status` - Ver estado del proyecto/agentes
  - [ ] `palace status`
  - [ ] `palace status --project my-project`
- [ ] `memory` - Gestión de memoria
  - [ ] `palace memory search "error de autenticación"`
  - [ ] `palace memory add --type solution --content "solución a X"`
- [ ] `agents` - Gestión de agentes
  - [ ] `palace agents list`
  - [ ] `palace agents info backend`
- [ ] `config` - Configuración del framework
  - [ ] `palace config list`
  - [ ] `palace config set api_key "value"`

#### Mejoras de CLI
- [ ] Añadir colores y formato con Rich
- [ ] Implementar autocompletado para shells (bash, zsh, fish)
- [ ] Añadir comandos de ayuda contextual
- [ ] Implementar modo interactivo (REPL)
- [ ] Añadir exportación de resultados (JSON, YAML, markdown)
- [ ] Implementar logging verbose/debug con niveles

#### Integración con API
- [ ] Conectar comandos CLI con API REST
- [ ] Implementar fallback a modo local si API no disponible
- [ ] Añadir opción para especificar endpoint de API

---

## 🔧 Módulo 11: Refinamiento

**Estado:** ❌ No implementado  
**Ubicación:** Varios módulos

### Tareas Pendientes

#### Manejo de Errores Robusto
- [ ] Implementar excepciones específicas por dominio
- [ ] Añadir retry logic para llamadas a LLM
- [ ] Implementar circuit breakers para servicios externos
- [ ] Crear sistema de fallback para modelos no disponibles
- [ ] Añadir validación de inputs en todos los componentes

#### Logging Estructurado
- [ ] Configurar logging estructurado (JSON) para producción
- [ ] Añadir correlation IDs para rastrear flujos completos
- [ ] Implementar niveles de logging apropiados (DEBUG, INFO, WARN, ERROR)
- [ ] Añadir métricas de performance (latencia, uso de tokens)
- [ ] Integrar con sistemas de observabilidad (OpenTelemetry)

#### Control de Costos
- [ ] Implementar tracking de tokens por modelo
- [ ] Añadir límites de costo por proyecto/sesión
- [ ] Implementar caching de respuestas de LLM
- [ ] Crear sistema de priorización para tareas costosas
- [ ] Añadir estimaciones de costo antes de ejecución

#### Mejora de Orquestación
- [ ] Optimizar selección de agentes por tarea
- [ ] Implementar load balancing entre agentes similares
- [ ] Añadir timeout y deadlines para tareas
- [ ] Implementar concurrent execution para tareas independientes
- [ ] Crear sistema de checkpoint/recovery para tareas largas

#### Calidad de Memoria
- [ ] Implementar deduplicación de entradas en memoria vectorial
- [ ] Añadir expiración automática para datos temporales
- [ ] Implementar scoring de relevancia para filtrar información
- [ ] Crear sistema de limpieza periódica
- [ ] Añadir validación de calidad para datos almacenados

---

## 🧪 Tests y Calidad

### Tests Unitarios
- [ ] Crear tests para todos los agentes
- [ ] Crear tests para memoria vectorial
- [ ] Crear tests para contexto y project loader
- [ ] Crear tests para API endpoints
- [ ] Crear tests para comandos CLI
- [ ] Implementar coverage reporting

### Tests de Integración
- [ ] Tests de flujo completo (tarea → agentes → resultado)
- [ ] Tests de memoria y contexto integrados
- [ ] Tests de API completa
- [ ] Tests de CLI completa
- [ ] Tests de performance y carga

### Calidad de Código
- [ ] Configurar linters (ruff, black, mypy)
- [ ] Configurar pre-commit hooks
- [ ] Configurar CI/CD (GitHub Actions, GitLab CI)
- [ ] Añadir seguridad scanning (bandit, safety)
- [ ] Implementar code review automático

---

## 📚 Documentación

### Documentación Técnica
- [ ] Documentación de arquitectura
- [ ] Guía de desarrollo para nuevos contribuidores
- [ ] Documentación de API completa
- [ ] Documentación de CLI completa
- [ ] Ejemplos de uso para cada agente

### Documentación de Usuario
- [ ] Guía de instalación y configuración
- [ ] Tutorial paso a paso
- [ ] FAQ y troubleshooting
- [ ] Best practices
- [ ] Casos de uso comunes

---

## 🚀 Próximos Pasos (Roadmap)

### Fase 1 - Funcionalidad Básica (Alta Prioridad) ✅ Módulos 4 y 6 completados
1. ~~Completar agentes (Módulo 4)~~ ✅ Completado
2. ~~Completar contexto (Módulo 6)~~ ✅ Completado
3. Implementar endpoints API esenciales (Módulo 8) - **Siguiente paso**
4. Implementar comandos CLI esenciales (Módulo 9)

### Fase 2 - Funcionalidad Avanzada (Media Prioridad)
1. Implementar pipelines (Módulo 7)
2. Completar refinamientos (Módulo 11)
3. Mejorar orquestación y optimizaciones

### Fase 3 - Producción (Baja Prioridad)
1. Tests completos y CI/CD
2. Documentación exhaustiva
3. Performance tuning
4. Security hardening

---

## 📝 Notas Adicionales

### Dependencias Externas
- [ ] Evaluar necesidad de ChromaDB vs. memoria en producción
- [ ] Configurar conexión con Ollama Cloud
- [ ] Configurar Zep para memoria persistente (opcional)

### Configuración
- [ ] Sistema de configuración por entorno (.env, config files)
- [ ] Configuración de modelos por agente
- [ ] Límites de rate limiting para APIs externas

### Deployment
- [ ] Dockerfile para contenerización
- [ ] Helm chart para Kubernetes
- [ ] Configuración para cloud providers

### Monitoreo
- [ ] Dashboards para métricas de agentes
- [ ] Alertas para errores y performance
- [ ] Log aggregation (ELK, Loki)

---

**Nota:** Este documento se actualizó el 2025-04-09. Los **Módulos 4 (Agentes) y 6 (Contexto)** fueron completados. El siguiente paso son los **Módulos 8 (API) y 9 (CLI)**. Referirse a [terminado.md](./terminado.md) para ver el progreso actual.