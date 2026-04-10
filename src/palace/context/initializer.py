"""
Palace Framework - Project Initializer

This module provides the functionality to automatically analyze an existing project
and generate the mandatory AI context files required for the framework to operate.
It implements the 'Zero-Friction' setup by automating the analysis, generation,
and registration process.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from palace.context.loader import ProjectLoader
from palace.context.manager import ContextManager
from palace.core.exceptions import PalaceError
from palace.llm.router import LLMRouter

logger = structlog.get_logger()


class ProjectInitializer:
    """
    Handles the automatic initialization of a project for the Palace Framework.

    This includes scanning the project structure, using the LLM to generate
    architectural context files, and registering the project in the system.
    """

    def __init__(self, framework: Any):
        """
        Initialize the project initializer.

        Args:
            framework: The main PalaceFramework instance.
        """
        self.framework = framework
        self.llm = framework.llm_router
        self.context_manager = framework.context_manager

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
            snapshot = self._analyze_project(project_path)

            # 2. Generate the context files using the LLM
            logger.info("generating_context_files_with_llm")
            contents = await self._generate_context_files(snapshot)

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

    def _analyze_project(self, path: Path) -> str:
        """
        Scan the project directory to create a snapshot of its structure and key files.
        """
        analysis = ["Project Analysis Snapshot", "========================"]

        # 1. Directory Structure (Depth 2)
        analysis.append("\n[Directory Structure]")
        for root, dirs, files in os.walk(path):
            level = root.relative_to(path).parts
            if len(level) > 2:
                continue
            indent = "  " * len(level)
            analysis.append(f"{indent}{os.path.basename(root)}/")
            sub_indent = "  " * (len(level) + 1)
            for f in files:
                # Only list key files to avoid noise
                if f.endswith(
                    (".py", ".js", ".ts", ".json", ".md", ".toml", ".txt", ".yml", ".yaml")
                ):
                    analysis.append(f"{sub_indent}{f}")

        # 2. Key Configuration Files
        critical_files = {
            "package.json": "Node.js/Frontend config",
            "requirements.txt": "Python dependencies",
            "pyproject.toml": "Python project config",
            "README.md": "Project overview",
            "docker-compose.yml": "Infrastructure",
            "Dockerfile": "Containerization",
        }

        for filename, description in critical_files.items():
            file_path = path / filename
            if file_path.exists():
                analysis.append(f"\n[{description}: {filename}]")
                try:
                    # Read first 100 lines to get a good idea of the project
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = "".join([next(f) for _ in range(100)])
                        analysis.append(content)
                except Exception as e:
                    analysis.append(f"Error reading file: {e}")

        return "\n".join(analysis)

    async def _generate_context_files(self, snapshot: str) -> Dict[str, str]:
        """
        Send the project snapshot to the LLM and request the 5 mandatory context files.
        """
        prompt = f"""
Actúas como un Arquitecto de Software Senior. Tu objetivo es analizar el siguiente snapshot de un proyecto y generar los 5 archivos de contexto obligatorios para el framework Palace.

ESTOS ARCHIVOS SON CRUCIALES. Permiten que un sistema multi-agente entienda el proyecto y genere código que encaje perfectamente sin errores.

──────────────────────────────────────
SNAPSHOT DEL PROYECTO:
──────────────────────────────────────
{snapshot}
──────────────────────────────────────

REGLAS DE GENERACIÓN:
1. Cada archivo debe ser ESPECÍFICO del proyecto, no genérico.
2. Incluir nombres reales de módulos, carpetas, tablas y patrones detectados en el snapshot.
3. Sé conciso pero técnico y preciso.
4. Usa Markdown.

DEBES GENERAR EXACTAMENTE ESTOS 5 ARCHIVOS:
1. architecture.md: Propósito, capas (API -> Service -> DB), patrones y flujo de requests.
2. stack.md: Lenguajes, versiones, frameworks, bases de datos y librerías principales.
3. conventions.md: Naming (variables, clases), estructura de carpetas, estándares de API y Git.
4. decisions.md: Decisiones arquitectónicas clave (ADRs) inferidas del stack y estructura.
5. constraints.md: Restricciones técnicas, de seguridad o de infraestructura.

FORMATO DE RESPUESTA:
Para cada archivo, usa el siguiente delimitador exacto para que yo pueda parsearlos:

---FILE: architecture.md---
(contenido aquí)
---END_FILE---

---FILE: stack.md---
(contenido aquí)
---END_FILE---

(Sigue así con los 5 archivos)
"""
        response = await self.llm.complete(prompt)
        return self._parse_llm_response(response)

    def _parse_llm_response(self, response: str) -> Dict[str, str]:
        """
        Parse the LLM response to extract the content of each file.
        """
        files = {}
        pattern = re.compile(r"---FILE: (.*?)---(.*?)---END_FILE---", re.DOTALL)
        matches = pattern.findall(response)

        for filename, content in matches:
            files[filename.strip()] = content.strip()

        # Validation: Ensure we have all 5 files
        expected = [
            "architecture.md",
            "stack.md",
            "conventions.md",
            "decisions.md",
            "constraints.md",
        ]
        missing = [f for f in expected if f not in files]

        if missing:
            logger.warn("llm_generation_incomplete", missing_files=missing)
            # Create empty files for missing ones to avoid breaking the system
            for m in missing:
                files[m] = f"# {m}\n\n[Contenido no generado automáticamente por la IA]"

        return files

    def _write_files(self, project_path: Path, contents: Dict[str, str]):
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

    async def _register_project(self, project_id: str, project_path: Path):
        """
        Register the project in the framework's memory store and load its context.
        """
        # 1. Create the project record
        await self.context_manager.create_project(
            project_id=project_id,
            name=project_id,
            description="Proyecto inicializado automáticamente por Palace Framework",
        )

        # 2. Load the newly created files into the framework's memory
        loader = ProjectLoader(project_path=project_path)
        await loader.load()

        logger.info("project_registered_and_loaded", project_id=project_id)
