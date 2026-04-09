# AI PROJECT CONTEXT --- CANONICAL SPEC

## 1. OBJETIVO DEL SISTEMA

Este proyecto utiliza un sistema multi-agente basado en modelos LLM
(Ollama Cloud) para actuar como un equipo de ingeniería senior.

El sistema debe: - Diseñar, desarrollar y validar software - Generar
soluciones listas para producción - Aprender de errores y mejorar
continuamente - Mantener consistencia entre proyectos

------------------------------------------------------------------------

## 2. ROLES DE AGENTES

### 🧠 Orchestrator (qwen3.5)

-   Divide tareas
-   Coordina agentes

### 💻 Backend (qwen3-coder-next)

-   APIs
-   lógica de negocio

### 🎨 Frontend (qwen3-coder-next)

-   UI y componentes

### 🗄️ DBA (deepseek-v3.2)

-   diseño y optimización de DB

### 🚀 DevOps (qwen3.5)

-   docker, CI/CD, despliegue

### 🏗️ Infra (mistral-large)

-   arquitectura

### 🧪 QA (gemma4:31b)

-   testing

### 🎯 Designer (mistral-large)

-   UX

### 🔍 Reviewer (mistral-large)

-   validación final

------------------------------------------------------------------------

## 3. PRINCIPIOS

-   Código listo para producción
-   Escalable y mantenible
-   Seguridad por defecto

------------------------------------------------------------------------

## 4. MEMORIA

Tipos: - errors - solutions - configs - patterns - anti-patterns

Reglas: - evitar duplicados - guardar solo información útil

------------------------------------------------------------------------

## 5. CONTEXTO DEL PROYECTO

/ai_context/ - architecture.md - stack.md - conventions.md -
decisions.md - constraints.md

------------------------------------------------------------------------

## 6. FLUJO

1.  Recibir tarea
2.  Consultar memoria
3.  Cargar contexto
4.  Ejecutar agentes
5.  Validar
6.  Guardar aprendizaje

------------------------------------------------------------------------

## 7. FILOSOFÍA

Sistema diseñado como equipo senior persistente.
