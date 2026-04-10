# Tareas Pendientes - Palace Framework

Este documento lista las tareas pendientes organizadas por módulo, basadas en el análisis del código existente y los requerimientos del [canonico.md](./canonico.md) y [modules.md](./modules.md).

**Última actualización:** 2025-04-09  
**Estado:** [Ver terminado.md](./terminado.md) para lo completado.

---

## 📋 Resumen de Prioridades

| Prioridad | Módulo | Descripción |
|-----------|--------|-------------|
| 🟢 Baja | Tests y Calidad | Tests unitarios e integración |
| 🟢 Baja | Documentación | Guías de uso, ejemplos, API docs |
| 🟢 Baja | Optimización | Performance tuning, security hardening |

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

## ⚙️ Módulo 7: Pipeline — ✅ COMPLETADO

**Estado:** ✅ Completado
**Ubicación:** `src/palace/pipelines/`

### Componentes Implementados

#### Tipos y Configuración (`types.py`)
- [x] `StepType` — Enum con 6 tipos: AGENT_TASK, CONDITIONAL, PARALLEL, VALIDATION, TRANSFORM, HUMAN_APPROVAL
- [x] `PipelineType` — Enum con 8 tipos: FEATURE_DEVELOPMENT, CODE_REVIEW, DEPLOYMENT, DATABASE_MIGRATION, REFACTORING, DOCUMENTATION, BUG_FIX, CUSTOM
- [x] `StepConfig` — Configuración de paso con dependencias, retry, timeout, templates
- [x] `PipelineConfig` — Configuración de pipeline con steps, max_retries, timeout, auto_approve
- [x] `StepDefinition`, `PipelineDefinition` — Definiciones estructuradas

#### Clases Base (`base.py`)
- [x] `PipelineStatus` — Enum: PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED
- [x] `StepStatus` — Enum: PENDING, RUNNING, COMPLETED, FAILED, SKIPPED, WAITING_APPROVAL
- [x] `StepResult` — Resultado de paso con artefactos, tokens, tiempo de ejecución
- [x] `PipelineResult` — Resultado de pipeline con step_results, artefactos, errores
- [x] `PipelineContext` — Contexto compartido entre pasos (variables, step_outputs)
- [x] `PipelineStep` — ABC con `execute()` y `can_execute()`, template variable substitution
- [x] `Pipeline` — ABC con `build_steps()` y `get_initial_context()`, validación

#### Ejecutor (`executor.py`)
- [x] `PipelineExecutor` — Ejecución con resolución de dependencias (topological sort)
- [x] Ejecución paralela de pasos sin dependencias (asyncio.gather)
- [x] Manejo de errores con retry y stop_on_failure
- [x] Soporte para PARALLEL, CONDITIONAL, AGENT_TASK steps
- [x] Integración con PalaceFramework para ejecución real de agentes
- [x] `get_executor()` — Singleton factory

#### Pipelines Específicos
- [x] `FeatureDevelopmentPipeline` — 6 pasos: analyze → database → backend → frontend → testing → review
- [x] `CodeReviewPipeline` — 4 pasos: analyze_code → security_review → suggest_improvements → final_report
- [x] `DeploymentPipeline` — 5 pasos: pre_deploy_check → build_and_test → deploy → post_deploy_verify → monitor
- [x] `DatabaseMigrationPipeline` — 5 pasos: analyze_schema → design_migration → review_migration → execute_migration → verify_migration
- [x] `RefactoringPipeline` — 5 pasos: analyze_code → plan_refactoring → implement_refactoring → test_refactoring → final_review
- [x] `DocumentationPipeline` — 4 pasos: analyze_codebase → generate_api_docs → generate_user_docs → review_docs
- [x] `AgentStep` — Clase concreta que delega ejecución a agentes con template variable injection

### Mejoras Pendientes (Baja Prioridad)
- [ ] Añadir sistema de condiciones y branching avanzado en pipelines
- [ ] Implementar monitoreo y logging detallado de ejecución
- [ ] Crear API para gestionar pipelines (iniciar, pausar, cancelar) via REST
- [ ] Implementar `BugFixPipeline` como pipeline específico
- [ ] Añadir persistencia de resultados de pipeline en memoria
- [ ] Tests de pipelines

---

## 🌐 Módulo 8: API — ✅ COMPLETADO

**Estado:** ✅ Completado
**Ubicación:** `src/palace/api/`

### Componentes Implementados

#### Proyectos — CRUD completo
- [x] `POST /projects` — Crear proyecto (integrado con ContextManager)
- [x] `GET /projects` — Listar proyectos (integrado con ContextManager)
- [x] `GET /projects/{project_id}` — Obtener proyecto con datos reales
- [x] `DELETE /projects/{project_id}` — Eliminar proyecto
- [x] `GET /projects/{project_id}/status` — Estado del proyecto

#### Tareas — Ejecución y consulta
- [x] `POST /tasks` — Crear y ejecutar tarea via Orchestrator
- [x] `GET /tasks/{task_id}` — Consultar estado de tarea

#### Sesiones — Gestión completa
- [x] `POST /sessions` — Crear sesión (integrado con ContextManager)
- [x] `GET /sessions/{session_id}` — Obtener sesión con datos reales
- [x] `GET /sessions/{session_id}/history` — Historial con paginación

#### Memoria — Búsqueda y almacenamiento
- [x] `POST /memory/query` — Búsqueda semántica (integrado con ContextManager.retrieve_context)
- [x] `POST /memory/entries` — Añadir entrada (integrado con MemoryStore)
- [x] `GET /memory/types` — Listar tipos de memoria

#### Agentes — Información dinámica
- [x] `GET /agents` — Listar agentes desde instancias reales del Orchestrator
- [x] `GET /agents/{agent_name}` — Detalle de agente con datos dinámicos

#### Sistema — Health check y configuración
- [x] `GET /health` — Health check
- [x] `GET /` — Info de la API
- [x] `POST /debug/reload` — Recargar framework (desarrollo)
- [x] `GET /debug/config` — Ver configuración (desarrollo)

#### Infraestructura API
- [x] Modelos Pydantic para request/response
- [x] Manejo de errores con PalaceError y HTTPException
- [x] Lifespan management para el framework
- [x] Configuración de CORS

### Mejoras Pendientes (Baja Prioridad)
- [ ] Añadir autenticación y autorización
- [ ] Implementar rate limiting
- [ ] Añadir documentación OpenAPI/Swagger completa
- [ ] Implementar WebSockets para updates en tiempo real
- [ ] Añadir endpoints de métricas y monitoreo
- [ ] Tests de API para cada endpoint

---

## 💻 Módulo 9: CLI — ✅ COMPLETADO

**Estado:** ✅ Completado
**Ubicación:** `src/palace/cli/`

### Componentes Implementados

#### Proyectos
- [x] `palace init` — Inicializar proyecto con carga de `/ai_context/` via ProjectLoader
- [x] `palace attach` — Adjuntar a proyecto existente y cargar contexto
- [x] `palace status` — Ver estado del proyecto
- [x] `palace list` — Listar proyectos

#### Tareas
- [x] `palace run` — Ejecutar tarea con opciones `--project`, `--agent`, `--session`, `--verbose`

#### Agentes
- [x] `palace agents` — Listar agentes dinámicamente desde el Orchestrator
- [x] `palace info` — Información detallada de agente con datos reales

#### Memoria
- [x] `palace memory query` — Búsqueda semántica con `--type`, `--top`, `--project`
- [x] `palace memory add` — Añadir entrada con tipo y metadatos

#### Sesiones
- [x] `palace session new` — Crear sesión (integrado con ContextManager)
- [x] `palace session history` — Ver historial con `--limit`

#### Configuración
- [x] `palace config` — Ver configuración actual

#### Modo interactivo
- [x] `palace interactive` — REPL con carga de contexto del proyecto

### Mejoras Pendientes (Baja Prioridad)
- [ ] Implementar autocompletado para shells (bash, zsh, fish)
- [ ] Añadir exportación de resultados (JSON, YAML, markdown)
- [ ] Implementar logging verbose/debug con niveles
- [ ] Conectar comandos CLI con API REST como alternativa
- [ ] Tests de CLI para cada comando

---

## 🔧 Módulo 11: Refinamiento — ✅ COMPLETADO

**Estado:** ✅ Completado
**Ubicación:** `src/palace/core/` (costs.py, logging_config.py, resilience.py, memory_quality.py)

### Componentes Implementados

#### Control de Costos (`costs.py`)
- [x] `CostTier` — Enum con 5 niveles: FREE, LOW, MEDIUM, HIGH, PREMIUM
- [x] `ModelPricing` — Precios por modelo (input/output por 1K tokens)
- [x] `UsageRecord` — Registro de uso con tokens, costo, timestamp
- [x] `CostBudget` — Presupuesto por proyecto (diario, mensual, por tarea) con alertas
- [x] `CostTracker` — Rastreador principal con 11 métodos:
  - [x] `record_usage()` — Registrar uso de modelo con cálculo automático de costo
  - [x] `estimate_cost()` — Estimar costo antes de ejecución
  - [x] `check_budget()` — Verificar si está dentro del presupuesto
  - [x] `set_budget()` — Configurar presupuesto por proyecto
  - [x] `get_usage_report()` — Reporte de uso filtrable (por proyecto, modelo, agente, fechas)
  - [x] `get_project_spend()` — Gasto actual del proyecto
  - [x] `add_model_pricing()` — Añadir precios de modelos
  - [x] `get_model_recommendation()` — Recomendación de modelo según tarea y presupuesto
- [x] Precios predefinidos para: qwen3.5, qwen3-coder-next, deepseek-v3.2, mistral-large, gemma4:31b

#### Logging Estructurado (`logging_config.py`)
- [x] `LogLevel` — Enum con niveles DEBUG, INFO, WARNING, ERROR, CRITICAL
- [x] `LoggingConfig` — Configuración de logging (formato JSON/console, timestamp, caller, archivo)
- [x] `configure_logging()` — Configuración principal de structlog con procesadores
- [x] `get_logger()` — Obtener logger estructurado
- [x] `bind_context()` / `unbind_context()` / `clear_context()` / `get_context()` — Gestión de contexto
- [x] `new_correlation_id()` / `set_correlation_id()` / `get_correlation_id()` — IDs de correlación
- [x] `log_performance()` — Context manager para medir duración de operaciones

#### Patrones de Resiliencia (`resilience.py`)
- [x] `CircuitState` — Enum: CLOSED, OPEN, HALF_OPEN
- [x] `RetryConfig` — Configuración de retry con backoff exponencial y jitter
- [x] `CircuitBreakerConfig` — Configuración de circuit breaker
- [x] `CircuitOpenError` — Excepción cuando el circuit breaker está abierto
- [x] `RetryWithBackoff` — Retry con backoff exponencial y jitter configurable
- [x] `CircuitBreaker` — Circuit breaker completo con `call()`, `is_available()`, `get_state()`, `get_stats()`, `reset()`
- [x] `ModelFallback` — Estrategia de fallback para modelos LLM con cadena de prioridad
- [x] `retry()` — Función de conveniencia a nivel de módulo

#### Calidad de Memoria (`memory_quality.py`)
- [x] `QualityScore` — Enum: HIGH (≥0.8), MEDIUM (0.5-0.8), LOW (0.3-0.5), IRRELEVANT (<0.3)
- [x] `CleanupPolicy` — Política de limpieza configurable
- [x] `MemoryQualityChecker` — Verificador de calidad con 7 métodos:
  - [x] `check_quality()` — Scoring 0.0-1.0 basado en contenido, acceso, recencia, metadata
  - [x] `classify_quality()` — Clasificación por rango de score
  - [x] `is_duplicate()` — Detección de duplicados por normalización y comparación
  - [x] `should_expire()` — Verificar expiración según política y tipo de memoria
  - [x] `get_entries_to_cleanup()` — Identificar entradas a eliminar
  - [x] `deduplicate_entries()` — Eliminar duplicados manteniendo el de mayor score
  - [x] `score_entry()` — Scoring completo con recomendación (keep/remove/review)
- [x] `MemoryCleanupTask` — Tarea de limpieza asíncrona con estadísticas acumulativas

### Mejoras Pendientes (Baja Prioridad)
- [ ] Integrar CostTracker en llamadas reales a LLM del framework
- [ ] Integrar CircuitBreaker en Orchestrator para protección de agentes
- [ ] Integrar MemoryQualityChecker en el ciclo de vida de MemoryStore
- [ ] Añadir validación de inputs con Pydantic en todos los endpoints API
- [ ] Implementar checkpoint/recovery para tareas largas en pipelines
- [ ] Integrar con OpenTelemetry para observabilidad

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

### Fase 1 - Funcionalidad Básica (Alta Prioridad) ✅ Completada
1. ~~Completar agentes (Módulo 4)~~ ✅ Completado
2. ~~Completar contexto (Módulo 6)~~ ✅ Completado
3. ~~Implementar endpoints API esenciales (Módulo 8)~~ ✅ Completado
4. ~~Implementar comandos CLI esenciales (Módulo 9)~~ ✅ Completado

### Fase 2 - Funcionalidad Avanzada (Media Prioridad) ✅ Completada
1. ~~Implementar pipelines (Módulo 7)~~ ✅ Completado
2. ~~Completar refinamientos (Módulo 11)~~ ✅ Completado
3. Mejorar orquestación y optimizaciones — **Siguiente paso**

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

**Nota:** Este documento se actualizó el 2025-04-09. **Todos los módulos de funcionalidad (1-11) fueron completados.** Los siguientes pasos son **Tests, Documentación y Optimización**. Referirse a [terminado.md](./terminado.md) para ver el progreso actual.