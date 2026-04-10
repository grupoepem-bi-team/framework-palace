# Tareas Pendientes - Palace Framework

Este documento lista las tareas pendientes organizadas por módulo, basadas en el análisis del código existente y los requerimientos del [canonico.md](./canonico.md) y [modules.md](./modules.md).

**Última actualización:** 2025-04-09  
**Estado:** [Ver terminado.md](./terminado.md) para lo completado.

---

## 📋 Resumen de Prioridades

| Prioridad | Módulo | Descripción |
|-----------|--------|-------------|
| 🟡 Media | Módulo 7 (Pipeline) | Flujos de trabajo avanzados |
| 🟢 Baja | Módulo 11 (Refinamiento) | Mejoras de robustez y optimización |
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

### Fase 1 - Funcionalidad Básica (Alta Prioridad) ✅ Completada
1. ~~Completar agentes (Módulo 4)~~ ✅ Completado
2. ~~Completar contexto (Módulo 6)~~ ✅ Completado
3. ~~Implementar endpoints API esenciales (Módulo 8)~~ ✅ Completado
4. ~~Implementar comandos CLI esenciales (Módulo 9)~~ ✅ Completado

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

**Nota:** Este documento se actualizó el 2025-04-09. Los **Módulos 4, 6, 8 y 9** fueron completados. Los siguientes pasos son el **Módulo 7 (Pipeline)** y el **Módulo 11 (Refinamiento)**. Referirse a [terminado.md](./terminado.md) para ver el progreso actual.