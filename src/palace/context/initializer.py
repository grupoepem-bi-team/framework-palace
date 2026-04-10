"""
Palace Framework - Project Initializer

This module provides the functionality to automatically analyze an existing project
and generate the mandatory AI context files required for the framework to operate.
It uses smart templates based on project analysis instead of requiring a live LLM,
making it fast and reliable.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from palace.context.loader import ProjectLoader
from palace.core.exceptions import PalaceError

logger = structlog.get_logger()


class ProjectInitializer:
    """
    Handles the automatic initialization of a project for the Palace Framework.

    This includes scanning the project structure, generating context files
    using smart templates based on the analysis, and registering the project.
    """

    def __init__(self, framework: Any):
        """
        Initialize the project initializer.

        Args:
            framework: The main PalaceFramework instance.
        """
        self.framework = framework
        self.settings = framework.settings

    async def initialize(self, project_path: Path) -> str:
        """
        Perform the full zero-friction initialization process.

        Args:
            project_path: Path to the target project root.

        Returns:
            The project_id used for registration.

        Raises:
            PalaceError: If the initialization process fails.
        """
        project_id = project_path.name
        logger.info("starting_auto_initialization", project_id=project_id, path=str(project_path))

        try:
            # 1. Analyze the existing project
            logger.info("analyzing_project_structure")
            analysis = self._analyze_project(project_path)

            # 2. Generate the context files using smart templates
            logger.info("generating_context_files")
            contents = self._generate_context_files(analysis)

            # 3. Write the files to the /ai_context/ directory
            logger.info("writing_context_files_to_disk")
            self._write_files(project_path, contents)

            # 4. Register the project in the framework memory
            logger.info("registering_project_in_framework")
            await self._register_project(project_id, project_path)

            logger.info("auto_initialization_completed", project_id=project_id)
            return project_id

        except Exception as e:
            logger.exception("initialization_failed", error=str(e))
            raise PalaceError(f"Failed to automatically initialize project: {e}")

    # =========================================================================
    # PROJECT ANALYSIS
    # =========================================================================

    def _analyze_project(self, path: Path) -> Dict[str, Any]:
        """
        Scan the project directory to detect languages, frameworks, and structure.
        """
        analysis: Dict[str, Any] = {
            "project_name": path.name,
            "path": str(path),
            "languages": [],
            "frameworks": [],
            "databases": [],
            "package_managers": [],
            "structure": [],
            "has_docker": False,
            "has_tests": False,
            "has_ci": False,
            "config_files": {},
            "dependencies": [],
            "dev_dependencies": [],
        }

        # 1. Detect from key config files
        self._detect_from_package_json(path, analysis)
        self._detect_from_requirements(path, analysis)
        self._detect_from_pyproject(path, analysis)
        self._detect_from_docker(path, analysis)

        # 2. Scan directory structure (depth 2)
        analysis["structure"] = self._scan_structure(path)

        # 3. Check for common directories
        analysis["has_tests"] = (
            (path / "tests").exists() or (path / "test").exists() or (path / "__tests__").exists()
        )
        analysis["has_docker"] = (path / "Dockerfile").exists() or (
            path / "docker-compose.yml"
        ).exists()
        analysis["has_ci"] = (path / ".github" / "workflows").exists() or (
            path / ".gitlab-ci.yml"
        ).exists()

        # 4. Default fallbacks
        if not analysis["languages"]:
            analysis["languages"] = self._guess_language_from_structure(path)

        return analysis

    def _detect_from_package_json(self, path: Path, analysis: Dict[str, Any]) -> None:
        """Detect project info from package.json."""
        pkg_path = path / "package.json"
        if not pkg_path.exists():
            return

        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                pkg = json.load(f)

            analysis["config_files"]["package.json"] = pkg
            analysis["languages"].append("JavaScript/TypeScript")
            analysis["package_managers"].append("npm")

            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            dep_list = list(deps.keys())
            analysis["dependencies"] = dep_list

            # Detect frameworks
            if "react" in deps:
                analysis["frameworks"].append("React")
            if "next" in deps:
                analysis["frameworks"].append("Next.js")
            if "vue" in deps:
                analysis["frameworks"].append("Vue.js")
            if "angular" in deps or "@angular/core" in deps:
                analysis["frameworks"].append("Angular")
            if "express" in deps:
                analysis["frameworks"].append("Express.js")
            if "fastify" in deps:
                analysis["frameworks"].append("Fastify")
            if "nestjs" in deps or "@nestjs/core" in deps:
                analysis["frameworks"].append("NestJS")
            if "tailwindcss" in deps:
                analysis["frameworks"].append("Tailwind CSS")
            if "typescript" in deps:
                analysis["languages"].append("TypeScript")

        except Exception as e:
            logger.warning("failed_to_parse_package_json", error=str(e))

    def _detect_from_requirements(self, path: Path, analysis: Dict[str, Any]) -> None:
        """Detect project info from requirements.txt."""
        req_path = path / "requirements.txt"
        if not req_path.exists():
            return

        analysis["languages"].append("Python")
        analysis["package_managers"].append("pip")

        try:
            with open(req_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            deps = [
                line.strip()
                .split("==")[0]
                .split(">=")[0]
                .split("<=")[0]
                .split("~=")[0]
                .strip()
                .lower()
                for line in lines
                if line.strip() and not line.startswith("#")
            ]
            analysis["dependencies"] = deps

            # Detect frameworks
            if "fastapi" in deps:
                analysis["frameworks"].append("FastAPI")
            if "flask" in deps:
                analysis["frameworks"].append("Flask")
            if "django" in deps:
                analysis["frameworks"].append("Django")
            if "sqlalchemy" in deps:
                analysis["databases"].append("SQLAlchemy (ORM)")
            if "pydantic" in deps:
                analysis["frameworks"].append("Pydantic")
            if "celery" in deps:
                analysis["frameworks"].append("Celery")
            if "scrapy" in deps:
                analysis["frameworks"].append("Scrapy")

        except Exception as e:
            logger.warning("failed_to_parse_requirements", error=str(e))

    def _detect_from_pyproject(self, path: Path, analysis: Dict[str, Any]) -> None:
        """Detect project info from pyproject.toml."""
        pyproject_path = path / "pyproject.toml"
        if not pyproject_path.exists():
            return

        analysis["languages"].append("Python")

        try:
            with open(pyproject_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Simple parsing - look for project name and dependencies
            if "[project]" in content:
                if "poetry" in content.lower() or "[tool.poetry]" in content:
                    analysis["package_managers"].append("Poetry")
                else:
                    analysis["package_managers"].append("pip (pyproject)")

        except Exception as e:
            logger.warning("failed_to_parse_pyproject", error=str(e))

    def _detect_from_docker(self, path: Path, analysis: Dict[str, Any]) -> None:
        """Detect infrastructure info from Docker files."""
        dockerfile = path / "Dockerfile"
        compose = path / "docker-compose.yml"

        if dockerfile.exists():
            analysis["has_docker"] = True
            try:
                with open(dockerfile, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                if "postgres" in content or "postgresql" in content:
                    analysis["databases"].append("PostgreSQL")
                if "mysql" in content or "mariadb" in content:
                    analysis["databases"].append("MySQL/MariaDB")
                if "mongo" in content:
                    analysis["databases"].append("MongoDB")
                if "redis" in content:
                    analysis["databases"].append("Redis")
            except Exception:
                pass

        if compose.exists():
            analysis["has_docker"] = True
            try:
                with open(compose, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                if "postgres" in content or "postgresql" in content:
                    analysis["databases"].append("PostgreSQL")
                if "mysql" in content or "mariadb" in content:
                    analysis["databases"].append("MySQL/MariaDB")
                if "mongo" in content:
                    analysis["databases"].append("MongoDB")
                if "redis" in content:
                    analysis["databases"].append("Redis")
                if "rabbitmq" in content:
                    analysis["frameworks"].append("RabbitMQ")
            except Exception:
                pass

    def _scan_structure(self, path: Path) -> List[str]:
        """Scan directory structure up to depth 2."""
        structure = []
        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith(".") or item.name in (
                    "node_modules",
                    "__pycache__",
                    ".venv",
                    "venv",
                    "dist",
                    "build",
                ):
                    continue
                if item.is_dir():
                    structure.append(f"{item.name}/")
                    try:
                        for sub in sorted(item.iterdir()):
                            if not sub.name.startswith("."):
                                structure.append(f"  {item.name}/{sub.name}")
                    except PermissionError:
                        pass
                else:
                    structure.append(item.name)
        except PermissionError:
            pass
        return structure[:100]  # Limit to 100 entries

    def _guess_language_from_structure(self, path: Path) -> List[str]:
        """Guess language when no config files are found."""
        languages = []
        py_files = list(path.glob("*.py"))
        js_files = list(path.glob("*.js")) + list(path.glob("*.ts"))
        java_files = list(path.glob("*.java"))
        go_files = list(path.glob("*.go"))

        if py_files:
            languages.append("Python")
        if js_files:
            languages.append("JavaScript/TypeScript")
        if java_files:
            languages.append("Java")
        if go_files:
            languages.append("Go")

        return languages or ["Unknown"]

    # =========================================================================
    # CONTEXT FILE GENERATION
    # =========================================================================

    def _generate_context_files(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Generate all 5 context files using smart templates."""
        return {
            "architecture.md": self._gen_architecture(analysis),
            "stack.md": self._gen_stack(analysis),
            "conventions.md": self._gen_conventions(analysis),
            "decisions.md": self._gen_decisions(analysis),
            "constraints.md": self._gen_constraints(analysis),
        }

    def _gen_architecture(self, a: Dict[str, Any]) -> str:
        name = a["project_name"]
        langs = ", ".join(dict.fromkeys(a["languages"])) or "Not detected"
        frameworks = ", ".join(dict.fromkeys(a["frameworks"])) or "Not detected"
        dbs = ", ".join(dict.fromkeys(a["databases"])) or "Not detected"
        structure = "\n".join(f"  {s}" for s in a["structure"][:30]) or "  (empty project)"

        has_api = any(
            f in a["frameworks"] for f in ["FastAPI", "Flask", "Django", "Express.js", "NestJS"]
        )
        has_frontend = any(f in a["frameworks"] for f in ["React", "Vue.js", "Angular", "Next.js"])

        layers = []
        if has_frontend:
            layers.append("- **Frontend**: UI components, pages, state management")
        if has_api:
            layers.append("- **API Layer**: REST/GraphQL endpoints, request validation")
            layers.append("- **Service Layer**: Business logic, domain rules")
            layers.append("- **Data Layer**: Database models, ORM, repositories")
        else:
            layers.append("- **Application Layer**: Core business logic")
            layers.append("- **Data Layer**: Data access and persistence")

        return f"""# Architecture — {name}

## Overview
{name} is a software project built with {langs}.
{"It uses a client-server architecture with a dedicated API backend." if has_api else "It follows a standard application architecture."}

## Capas
{chr(10).join(layers)}

## Patrones
- **Repository Pattern**: Data access abstraction (if applicable)
- **Service Layer**: Business logic separated from presentation
- **Dependency Injection**: Used for configuration and testing

## Flujo Principal
1. Client sends request to the application
2. Request is validated and routed to the appropriate handler
3. Service layer processes business logic
4. Data layer persists or retrieves information
5. Response is returned to the client

## Integraciones Externas
- Database: {dbs}
- Review `package.json` or `requirements.txt` for third-party API integrations

## Despliegue
{"- Docker-based deployment (Dockerfile detected)" if a["has_docker"] else "- Deployment configuration not detected"}
{"- CI/CD pipeline detected" if a["has_ci"] else "- No CI/CD configuration detected"}

## Estructura del Proyecto
```
{structure}
```

> **Note**: This file was auto-generated by `palace init`. Review and complete with specific details.
"""

    def _gen_stack(self, a: Dict[str, Any]) -> str:
        name = a["project_name"]
        langs = list(dict.fromkeys(a["languages"]))
        frameworks = list(dict.fromkeys(a["frameworks"]))
        dbs = list(dict.fromkeys(a["databases"]))
        pkg_mgrs = list(dict.fromkeys(a["package_managers"]))
        deps = a.get("dependencies", [])

        is_python = "Python" in langs or "Python" in str(a["languages"])
        is_js = "JavaScript/TypeScript" in langs or "JavaScript/TypeScript" in str(a["languages"])

        backend_section = "## Backend\n- Not detected\n"
        frontend_section = "## Frontend\n- Not detected\n"

        if is_python:
            backend_section = f"""## Backend
- **Language**: Python
- **Frameworks**: {", ".join(frameworks) or "Not detected"}
- **Package Manager**: {", ".join(pkg_mgrs) or "pip"}
- **Key Libraries**:
"""
            for dep in deps[:20]:
                backend_section += f"  - {dep}\n"

        if is_js:
            js_frameworks = [
                f
                for f in frameworks
                if f in ("React", "Vue.js", "Angular", "Next.js", "Express.js", "NestJS", "Fastify")
            ]
            ui_frameworks = [f for f in frameworks if f in ("Tailwind CSS",)]
            frontend_section = f"""## Frontend
- **Language**: {"TypeScript" if "TypeScript" in langs else "JavaScript"}
- **Frameworks**: {", ".join(js_frameworks) or "Not detected"}
- **UI Libraries**: {", ".join(ui_frameworks) or "Not detected"}
- **Key Dependencies**:
"""
            for dep in deps[:20]:
                frontend_section += f"  - {dep}\n"

        infra_section = f"""## Infraestructura
- **Databases**: {", ".join(dbs) or "Not detected"}
- **Containerization**: {"Docker" if a["has_docker"] else "Not detected"}
- **CI/CD**: {"Configured" if a["has_ci"] else "Not detected"}
"""

        return f"""# Stack Tecnológico — {name}

{backend_section}
{frontend_section}
{infra_section}

## Herramientas de Desarrollo
- **Linter/Formatter**: Review project config for details
- **Testing**: {"pytest" if is_python else "jest/vitest" if is_js else "Not detected"}

> **Note**: This file was auto-generated by `palace init`. Review and complete with specific versions and details.
"""

    def _gen_conventions(self, a: Dict[str, Any]) -> str:
        name = a["project_name"]
        is_python = "Python" in a["languages"] or "Python" in str(a["languages"])
        is_js = "JavaScript/TypeScript" in a["languages"] or "JavaScript/TypeScript" in str(
            a["languages"]
        )

        if is_python:
            naming = """## Nombres
- Variables: `snake_case`
- Funciones: `snake_case`
- Clases: `PascalCase`
- Archivos: `snake_case.py`
- Constantes: `UPPER_SNAKE_CASE`"""
            code_structure = """## Estructura de Código
- Imports ordenados: stdlib → third-party → local
- Type hints obligatorios
- Docstrings en formato Google/NumPy"""
            api_section = """## API REST
- URLs en plural: `/api/v1/resources`
- Respuestas exitosas: 200, 201, 204
- Errores: 400, 401, 403, 404, 422, 500
- Formato de error: `{"detail": "message"}`"""
        elif is_js:
            naming = """## Nombres
- Variables: `camelCase`
- Funciones: `camelCase`
- Clases/Componentes: `PascalCase`
- Archivos: `kebab-case.tsx` o `PascalCase.tsx`
- Constantes: `UPPER_SNAKE_CASE`"""
            code_structure = """## Estructura de Código
- Imports ordenados: React → third-party → local → styles
- TypeScript strict mode preferido"""
            api_section = """## API REST
- URLs en plural: `/api/v1/resources`
- Seguir RESTful conventions"""
        else:
            naming = "## Nombres\n- Follow project's existing conventions"
            code_structure = "## Estructura de Código\n- Follow project's existing patterns"
            api_section = "## API REST\n- Follow project's existing API patterns"

        return f"""# Convenciones de Código — {name}

{naming}

{code_structure}

{api_section}

## Base de Datos
- Nombres de tablas: `snake_case` plural
- Columnas: `snake_case`
- Timestamps: `created_at`, `updated_at`
- Soft delete: `deleted_at` (si aplica)

## Testing
- Framework: {"pytest" if is_python else "jest" if is_js else "por definir"}
- Nombres: `test_<módulo>_<escenario>_<resultado>`
- Ubicación: `tests/`

## Git
- Commits: `tipo(scope): descripción`
  - feat, fix, docs, refactor, test, chore
- Branches: `main`, `develop`, `feature/*`, `hotfix/*`

## Documentación
- {"Docstrings en Google style" if is_python else "JSDoc/TSDoc para funciones públicas" if is_js else "Documentar APIs y funciones públicas"}

> **Note**: This file was auto-generated by `palace init`. Adjust to match your project's actual conventions.
"""

    def _gen_decisions(self, a: Dict[str, Any]) -> str:
        name = a["project_name"]
        frameworks = list(dict.fromkeys(a["frameworks"]))
        dbs = list(dict.fromkeys(a["databases"]))
        is_python = "Python" in a["languages"] or "Python" in str(a["languages"])

        adrs = []

        if frameworks:
            fw_list = ", ".join(frameworks)
            adrs.append(f"""## ADR-001: Elección de Framework
- **Estado**: Aceptada
- **Contexto**: Se necesitaba un framework para el desarrollo del proyecto
- **Decisión**: Se utilizaron {fw_list} por productividad y ecosistema
- **Consecuencias**: Rapidez en desarrollo, pero dependencia del ecosistema elegido""")

        if dbs:
            db_list = ", ".join(dbs)
            adrs.append(f"""## ADR-002: Elección de Base de Datos
- **Estado**: Aceptada
- **Contexto**: Se necesita persistencia de datos
- **Decisión**: Se utiliza {db_list}
- **Consecuencias**: Requiere conocimiento específico de la tecnología elegida""")

        if a["has_docker"]:
            adrs.append("""## ADR-003: Containerización
- **Estado**: Aceptada
- **Contexto**: Se necesita consistencia entre ambientes de desarrollo y producción
- **Decisión**: Usar Docker para containerización
- **Consecuencias**: Mayor complejidad inicial, pero despliegue consistente""")

        adrs_section = (
            "\n\n".join(adrs)
            if adrs
            else "## ADR-001: Pendiente\n- **Estado**: Pendiente\n- **Contexto**: Sin decisiones registradas aún\n- **Decisión**: Por definir\n- **Consecuencias**: Por definir"
        )

        return f"""# Decisiones Arquitectónicas — {name}

{adrs_section}

> **Note**: This file was auto-generated by `palace init`. Document your actual architectural decisions here as the project evolves.
"""

    def _gen_constraints(self, a: Dict[str, Any]) -> str:
        name = a["project_name"]
        is_python = "Python" in a["languages"] or "Python" in str(a["languages"])
        is_js = "JavaScript/TypeScript" in a["languages"] or "JavaScript/TypeScript" in str(
            a["languages"]
        )

        compat = []
        if is_python:
            compat.append("- Python 3.11+")
        if is_js:
            compat.append("- Node.js 18+")
            compat.append("- Modern browsers (last 2 versions)")

        compat_section = "\n".join(compat) if compat else "- To be defined"

        return f"""# Restricciones del Proyecto — {name}

## Requisitos del Cliente
- Define non-negotiable client requirements here

## Performance
- Latencia máxima: Definir según requisitos
- Usuarios concurrentes: Definir según requisitos
- Tiempo máximo de respuesta: Definir según requisitos

## Seguridad
- HTTPS obligatorio en producción
- Autenticación: Método por definir
- Autorización: Método por definir
- Datos sensibles: Encriptar en reposo y tránsito

## Infraestructura
- Base de datos: {", ".join(dict.fromkeys(a["databases"])) or "Por definir"}
- Deployment: {"Docker" if a["has_docker"] else "Por definir"}
- Ambientes: dev, staging, producción

## Regulaciones y Compliance
- Revisar si aplica: GDPR, SOC2, etc.

## Compatibilidad
{compat_section}

## Lo que NO hacemos
- Definir explícitamente features fuera de alcance

> **Note**: This file was auto-generated by `palace init`. Fill in your project's real constraints and limits.
"""

    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================

    def _write_files(self, project_path: Path, contents: Dict[str, str]) -> None:
        """
        Create the ai_context directory and write the generated markdown files.
        """
        context_dir = project_path / "ai_context"
        context_dir.mkdir(parents=True, exist_ok=True)

        for filename, content in contents.items():
            file_path = context_dir / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.debug("context_file_written", file=filename)

    # =========================================================================
    # PROJECT REGISTRATION
    # =========================================================================

    async def _register_project(self, project_id: str, project_path: Path) -> None:
        """
        Register the project in the framework's memory store and load its context.
        """
        try:
            # Access the context manager (private attribute but accessible)
            context_manager = getattr(self.framework, "_context_manager", None)
            if context_manager is not None:
                await context_manager.create_project(
                    project_id=project_id,
                    name=project_id,
                    description="Proyecto inicializado automáticamente por Palace Framework",
                )
                logger.info("project_registered_in_context_manager", project_id=project_id)
            else:
                logger.warning("context_manager_not_available", project_id=project_id)
        except Exception as e:
            logger.warning("project_registration_failed", error=str(e))
            # Don't fail the whole initialization if registration fails

        # Load the newly created files into memory
        try:
            loader = ProjectLoader(project_path=project_path)
            await loader.load()
            logger.info("context_loaded_into_memory", project_id=project_id)
        except Exception as e:
            logger.warning("context_loading_failed", error=str(e))
            # Don't fail the whole initialization if loading fails
