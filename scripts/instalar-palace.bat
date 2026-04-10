@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: ============================================================
::  Palace Framework — Instalador para Windows
::  Para usar con Ollama Cloud + Zep IDE
::  Doble clic para ejecutar
:: ============================================================

title Palace Framework - Instalador

:: ============================================================
::  PANTALLA DE BIENVENIDA
:: ============================================================
cls
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║                                                   ║
echo  ║        🏛️  PALACE FRAMEWORK                      ║
echo  ║        Multi-agente inteligente para              ║
echo  ║        desarrollo de software                     ║
echo  ║                                                   ║
echo  ║        Instalador interactivo                    ║
echo  ║                                                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Este script va a:
echo    1. Verificar que tenés Python instalado
echo    2. Descargar Palace Framework
echo    3. Crear un entorno virtual
echo    4. Instalar las dependencias
echo    5. Configurar tu proyecto
echo    6. Crear los archivos de contexto (ai_context)
echo.
echo  Presioná cualquier tecla para empezar o Ctrl+C para cancelar.
echo.
pause

:: ============================================================
::  PASO 1: VERIFICAR PYTHON
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PASO 1 de 6 — Verificando Python
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Python no está instalado o no está en el PATH.
    echo.
    echo  Descargalo de: https://www.python.org/downloads/
    echo.
    echo  IMPORTANTE: Al instalar, marcá la opción:
    echo     ✅ "Add Python to PATH"
    echo.
    echo  Después de instalar Python, volvé a ejecutar este script.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^^&1') do set "PYVER=%%v"
echo  ✅ Python !PYVER! encontrado
echo.
pause

:: ============================================================
::  PASO 2: VERIFICAR GIT
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PASO 2 de 6 — Verificando Git
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

git --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Git no está instalado.
    echo.
    echo  Descargalo de: https://git-scm.com/download/win
    echo.
    echo  Después de instalar Git, volvé a ejecutar este script.
    echo.
    pause
    exit /b 1
)

echo  ✅ Git encontrado
echo.
pause

:: ============================================================
::  PASO 3: DESCARGAR E INSTALAR PALACE
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PASO 3 de 6 — Descargando Palace Framework
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

:: Carpeta de instalación en el hogar del usuario
set "PALACE_DIR=%USERPROFILE%\palace-framework"
set "PALACE_VENV=%PALACE_DIR%\.venv"

:: Clonar el repositorio si no existe
if not exist "%PALACE_DIR%\.git" (
    echo  Descargando Palace Framework desde GitHub...
    echo  Esto puede tardar unos segundos...
    echo.
    git clone https://github.com/grupoepem-bi-team/framework-palace.git "%PALACE_DIR%" 2>nul
    if errorlevel 1 (
        echo.
        echo  ❌ Error al descargar Palace.
        echo     Verificá tu conexión a internet.
        echo.
        pause
        exit /b 1
    )
    echo  ✅ Palace descargado
) else (
    echo  Palace ya está descargado. Actualizando...
    pushd "%PALACE_DIR%" >nul
    git pull origin main >nul 2>&1
    popd >nul
    echo  ✅ Palace actualizado a la última versión
)

:: Crear entorno virtual si no existe
if not exist "%PALACE_VENV%\Scripts\activate.bat" (
    echo  Creando entorno virtual...
    python -m venv "%PALACE_VENV%"
    if errorlevel 1 (
        echo  ❌ Error al crear el entorno virtual.
        pause
        exit /b 1
    )
    echo  ✅ Entorno virtual creado
) else (
    echo  ✅ Entorno virtual ya existe
)

:: Instalar dependencias
echo  Instalando dependencias (puede tardar 1-2 minutos)...
call "%PALACE_VENV%\Scripts\activate.bat" >nul 2>&1
pip install -e "%PALACE_DIR%" --quiet --no-color 2>nul
if errorlevel 1 (
    echo  Reintentando instalación...
    pip install --upgrade pip --quiet 2>nul
    pip install -e "%PALACE_DIR%" --quiet 2>nul
    if errorlevel 1 (
        echo  ❌ Error al instalar dependencias.
        echo     Probá ejecutar manualmente:
        echo     %PALACE_VENV%\Scripts\activate
        echo     pip install -e %PALACE_DIR%
        echo.
        pause
        exit /b 1
    )
)
echo  ✅ Dependencias instaladas

:: ============================================================
::  SOPORTE GLOBAL: Agregar Palace al PATH de Windows
:: ============================================================
echo.
echo  Configurando acceso global al comando 'palace'...

set "SCRIPTS_PATH=%PALACE_VENV%\Scripts"

:: Usamos PowerShell para añadir la ruta al PATH del usuario de forma segura
powershell -Command "[string]$oldPath = [Environment]::GetEnvironmentVariable('Path', 'User'); $newPath = '%SCRIPTS_PATH%'; if ($oldPath -notlike '*' + $newPath + '*') { [Environment]::SetEnvironmentVariable('Path', $oldPath + ';' + $newPath, 'User') }" >nul 2>&1

if %errorlevel% equ 0 (
    echo  ✅ Comando 'palace' registrado globalmente.
    echo     ⚠️  IMPORTANTE: Debes REINICIAR tu terminal para que el cambio surta efecto.
) else (
    echo  ⚠️  No se pudo registrar el comando global automáticamente.
    echo     Podrás usar el archivo 'palace-iniciar.bat' en tu proyecto.
)
echo.
pause

:: ============================================================
::  PASO 4: SELECCIONAR PROYECTO
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PASO 4 de 6 — Seleccioná tu proyecto
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo  ¿Dónde está tu proyecto? Ingresá la ruta completa.
echo.
echo  Ejemplos:
echo    C:\Desarrollos\mi-proyecto
echo    C:\Users\juan\Documents\app-web
echo    D:\trabajo\sistema-reportes
echo.

set /p "PROJECT_PATH=Ruta de tu proyecto: "

:: Validar que la ruta existe
set "PROJECT_PATH=!PROJECT_PATH:"=!"
if not exist "!PROJECT_PATH!" (
    echo.
    echo  ❌ La ruta no existe: !PROJECT_PATH!
    echo     Verificá que la ruta esté bien escrita.
    echo.
    pause
    exit /b 1
)

:: Obtener nombre del proyecto
for %%f in ("!PROJECT_PATH!") do set "PROJECT_NAME=%%~nf"

echo.
echo  ✅ Proyecto encontrado: !PROJECT_NAME!
echo     Ubicación: !PROJECT_PATH!
echo.
pause

:: ============================================================
::  PASO 5: CREAR CARPETA ai_context Y COPIAR PROMPT
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PASO 5 de 6 — Configurando contexto del proyecto
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

set "AI_CONTEXT=!PROJECT_PATH!\ai_context"

:: Crear carpeta ai_context
if not exist "!AI_CONTEXT!" (
    mkdir "!AI_CONTEXT!"
    echo  ✅ Carpeta creada: ai_context\
) else (
    echo  ✅ Carpeta ya existe: ai_context\
)

:: Copiar prompt_5data.md al proyecto
if exist "%PALACE_DIR%\prompt_5data.md" (
    copy /y "%PALACE_DIR%\prompt_5data.md" "!PROJECT_PATH!\prompt_5data.md" >nul 2>&1
    echo  ✅ Archivo prompt_5data.md copiado a tu proyecto
) else (
    echo  ⚠️  No se encontró prompt_5data.md en Palace
)

:: Crear archivo .env con la configuración de modelos
if not exist "!PROJECT_PATH!\.env" (
    (
        echo # Palace Framework - Configuracion del proyecto !PROJECT_NAME!
        echo # Generado automaticamente por el instalador
        echo.
        echo # --- Ollama Cloud ---
        echo # Para modelos :cloud, usar el endpoint local de Ollama
        echo # Si usas Zep IDE, Ollama ya corre en localhost:11434
        echo OLLAMA_BASE_URL=http://localhost:11434
        echo OLLAMA_API_KEY=
        echo.
        echo # --- Modelos por agente ---
        echo MODEL_ORCHESTRATOR=qwen3.5:cloud
        echo MODEL_DEVOPS=qwen3.5:cloud
        echo MODEL_BACKEND=qwen3-coder-next:cloud
        echo MODEL_FRONTEND=qwen3-coder-next:cloud
        echo MODEL_INFRA=qwen3-coder-next:cloud
        echo MODEL_DBA=deepseek-v3.2:cloud
        echo MODEL_QA=gemma4:31b-cloud
        echo MODEL_DESIGNER=mistral-large-3:675b-cloud
        echo MODEL_REVIEWER=mistral-large-3:675b-cloud
        echo MODEL_EMBEDDING=nomic-embed-text
        echo.
        echo # --- Memoria ---
        echo MEMORY_STORE_TYPE=sqlite
        echo LOCAL_MEMORY_PATH=./data/memory.db
        echo.
        echo # --- Base de datos ---
        echo DATABASE_URL=sqlite+aiosqlite:///./data/palace.db
        echo.
        echo # --- API ---
        echo API_HOST=0.0.0.0
        echo API_PORT=8000
        echo API_DEBUG=false
    ) > "!PROJECT_PATH!\.env"
    echo  ✅ Archivo .env creado con modelos Ollama Cloud
) else (
    echo  ✅ Archivo .env ya existe — no se sobreescribe
)

:: Verificar archivos de contexto existentes
set "CONTEXT_COUNT=0"
for %%f in ("architecture.md" "stack.md" "conventions.md" "decisions.md" "constraints.md") do (
    if exist "!AI_CONTEXT!\%%~f" set /a "CONTEXT_COUNT+=1"
)

echo.
echo  ─────────────────────────────────────────────
echo  Archivos de contexto: !CONTEXT_COUNT! de 5
echo  ─────────────────────────────────────────────

if "!CONTEXT_COUNT!"=="5" (
    echo.
    echo  ✅ Los 5 archivos de contexto ya existen.
    echo     Palace está listo para usar.
) else (
    echo.
    echo  ⚠️  Faltan archivos de contexto.
    echo.
    echo  ┌──────────────────────────────────────────────────────┐
    echo  │                                                       │
    echo  │  🔴  PROXIMO PASO IMPORTANTE                         │
    echo  │                                                       │
    echo  │  1. Abrí el archivo prompt_5data.md que se          │
    echo  │     copió en tu proyecto                             │
    echo  │                                                       │
    echo  │  2. Llená la sección [INFORMACIÓN DE TU PROYECTO]   │
    echo  │     con los datos de tu proyecto                    │
    echo  │                                                       │
    echo  │  3. Pegá ese prompt en ChatGPT, Claude, o la        │
    echo  │     IA de Zep IDE                                    │
    echo  │                                                       │
    echo  │  4. Copiá los 5 archivos generados a:               │
    echo  │     !AI_CONTEXT!\                     │
    echo  │                                                       │
    echo  │  5. Volvé a ejecutar este script                     │
    echo  │                                                       │
    echo  └──────────────────────────────────────────────────────┘
    echo.

    :: Abrir la carpeta ai_context para que el usuario pegue los archivos
    echo  ¿Querés abrir la carpeta ai_context ahora?
    choice /c SN /n /m "  [S]í / [N]o: "
    if errorlevel 2 goto :skip_open

    explorer "!AI_CONTEXT!"
    echo  ✅ Carpeta abierta. Pegá los 5 archivos ahí.
    echo.

    :skip_open
    echo  ¿Ya copiaste los 5 archivos?
    choice /c SN /n /m "  [S]í, ya los tengo / [N]o, aún no: "
    if errorlevel 2 (
        echo.
        echo  Ok. Ejecutá este script de nuevo cuando tengas los archivos.
        echo.
        pause
        exit /b 0
    )
)

echo.
pause

:: ============================================================
::  PASO 6: REGISTRAR PROYECTO EN PALACE
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PASO 6 de 6 — Registrando proyecto en Palace
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

call "%PALACE_VENV%\Scripts\activate.bat" >nul 2>&1

:: Cambiar al directorio del proyecto
cd /d "!PROJECT_PATH!"

:: Inicializar proyecto
echo  Registrando proyecto !PROJECT_NAME! en Palace...
echo.
palace init "!PROJECT_NAME!" --path "!PROJECT_PATH!" 2>nul
if errorlevel 1 (
    echo  Intentando con palace attach...
    palace attach "!PROJECT_NAME!" --path "!PROJECT_PATH!" 2>nul
)

echo.
echo  ✅ Proyecto registrado
echo.

:: Crear script de inicio rápido en el proyecto
set "LAUNCH_BAT=!PROJECT_PATH!\palace-iniciar.bat"

(
echo @echo off
echo chcp 65001 ^>nul 2^>^^&1
echo title Palace Framework - !PROJECT_NAME!
echo echo.
echo  🏛️  Palace Framework - !PROJECT_NAME!
echo echo.
echo call "%PALACE_VENV%\Scripts\activate.bat"
echo cd /d "!PROJECT_PATH!"
echo echo  Activando Palace...
echo echo.
echo echo  Comandos disponibles:
echo echo  ──────────────────────────────────────────
echo echo   palace run "tu tarea"         - Ejecutar tarea
echo echo   palace interactive            - Modo conversación
echo echo   palace agents                 - Ver agentes
echo echo   palace memory query "texto"   - Buscar en memoria
echo echo   palace status                 - Ver estado
echo echo  ──────────────────────────────────────────
echo echo.
echo cmd /k
) > "!LAUNCH_BAT!"

echo  ✅ Script de inicio creado: palace-iniciar.bat
echo.

:: ============================================================
::  PANTALLA FINAL
:: ============================================================
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                           ║
echo  ║       ✅  PALACE FRAMEWORK INSTALADO CORRECTAMENTE        ║
echo  ║                                                           ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  ┌─────────────────────────────────────────────────────────────┐
echo  │  RESUMEN                                                   │
echo  │                                                             │
echo  │  📁 Proyecto:     !PROJECT_NAME!                           │
echo  │  📂 Ubicación:    !PROJECT_PATH!                            │
echo  │  📝 Contexto:     !AI_CONTEXT!\                             │
echo  │  🏛️ Palace:       %PALACE_DIR%                             │
echo  │  🤖 Modelos:      Ollama Cloud (:cloud)                    │
echo  │                                                             │
echo  │  Archivos de contexto:                                      │
for %%f in ("architecture.md" "stack.md" "conventions.md" "decisions.md" "constraints.md") do (
    if exist "!AI_CONTEXT!\%%~f" (
        echo  │     ✅ %%~m                                      │
    ) else (
        echo  │     ❌ %%~m  ← FALTA                              │
    )
)
echo  │                                                             │
echo  │  🚀 Para empezar:                                           │
echo  │                                                             │
echo  │  Opción A — Doble clic:                                    │
echo  │    Abrí: palace-iniciar.bat                                 │
echo  │                                                             │
echo  │  Opción B — Desde CMD:                                      │
echo  │    cd !PROJECT_PATH!                                        │
echo  │    call "%PALACE_VENV%\Scripts\activate.bat"                 │
echo  │    palace interactive                                        │
echo  │                                                             │
echo  └─────────────────────────────────────────────────────────────┘
echo.

:: Verificar si faltan archivos de contexto
set "FALTAN=0"
for %%f in ("architecture.md" "stack.md" "conventions.md" "decisions.md" "constraints.md") do (
    if not exist "!AI_CONTEXT!\%%~f" set "FALTAN=1"
)

if "!FALTAN!"=="1" (
    echo  ═════════════════════════════════════════════════════
    echo  ⚠️  FALTAN ARCHIVOS DE CONTEXTO
    echo  ═════════════════════════════════════════════════════
    echo.
    echo  Los archivos de ai_context/ le enseñan a Palace sobre
    echo  tu proyecto. Sin ellos, Palace no conoce tu stack,
    echo  convenciones ni restricciones.
    echo.
    echo  ¿Cómo crear los archivos:
    echo.
    echo  1. Abrí: prompt_5data.md (en tu proyecto)
    echo  2. Completá la sección [INFORMACIÓN DE TU PROYECTO]
    echo  3. Pegá el prompt en ChatGPT, Claude, o Zep IDE
    echo  4. Copiá los 5 archivos generados a: ai_context\
    echo.
    echo  ═════════════════════════════════════════════════════
    echo.
)

:: Preguntar si quiere iniciar Palace
echo  ¿Querés iniciar Palace ahora?
choice /c SN /n /m "  [S]í / [N]o: "
if errorlevel 2 goto :skip_start

echo.
echo  Iniciando Palace en modo interactivo...
echo.
call "%PALACE_VENV%\Scripts\activate.bat" >nul 2>&1
cd /d "!PROJECT_PATH!"
palace interactive --project "!PROJECT_NAME!"

:skip_start
echo.
echo  Para usar Palace en el futuro, hacé doble clic en:
echo  !LAUNCH_BAT!
echo.
pause
