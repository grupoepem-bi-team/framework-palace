@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

title Palace Framework - Limpiar Proyecto Rápido

:: ============================================================
::  PANTALLA DE BIENVENIDA
:: ============================================================
cls
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║                                                   ║
echo  ║        🏛️  PALACE FRAMEWORK                      ║
echo  ║        Limpiar Proyecto Rápido                   ║
echo  ║                                                   ║
echo  ║        Elimina las configuraciones de Palace     ║
echo  ║        de un proyecto específico                 ║
echo  ║                                                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Este script eliminará de tu proyecto actual:
echo    - La carpeta ai_context/
echo    - El archivo .palace.env (si existe)
echo    - El registro del proyecto en el framework
echo.
echo  IMPORTANTE: NO eliminará tu código fuente.
echo.
pause

:: ============================================================
::  OBTENER RUTA DEL PROYECTO (desde argumento o actual)
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  UBICACIÓN DEL PROYECTO
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo  Detecté que estás en: %CD%
echo.

if "%~1"=="" (
    set "PROYECTO_PATH=%CD%"
    echo  Usando el directorio actual como proyecto.
    echo  Si querés otro proyecto, ejecutá el script así:
    echo  limpiar-proyecto-rapido.bat "C:\Proyectos\mi-proyecto"
    echo.
    set /p "CONFIRMAR_PATH=¿QUERÉS CONTINUAR CON ESTA RUTA? (SI/NO): "
    if /i "!CONFIRMAR_PATH!"=="NO" (
        echo.
        echo  Ingresá la ruta manualmente:
        set /p "PROYECTO_PATH=Ruta completa del proyecto: "
    )
) else (
    set "PROYECTO_PATH=%~1"
)

:: Normalizar ruta (quitar comillas si existen y espacios extras)
set "PROYECTO_PATH=%PROYECTO_PATH:"=%"
set "PROYECTO_PATH=%PROYECTO_PATH: =%"

if not exist "%PROYECTO_PATH%" (
    echo  ❌ El proyecto no existe: %PROYECTO_PATH%
    echo.
    echo  Asegurá que la ruta sea correcta y volvé a intentar.
    pause
    exit /b 1
)

:: ============================================================
::  CONFIRMACIÓN DE ELIMINACIÓN
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  CONFIRMACIÓN DE ELIMINACIÓN
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo  Proyecto: %PROYECTO_PATH%
echo.
echo  Se eliminarán los siguientes elementos de Palace:
echo    [X] %PROYECTO_PATH%\ai_context\          (archivos de contexto IA)
echo    [X] %PROYECTO_PATH%\.palace.env          (configuración del proyecto)
echo    [X] Registro en la base de datos del framework
echo.
echo  ⚠️  ATENCIÓN: Esta acción NO puede deshacerse.
echo.
set /p "CONFIRMAR=¿QUERÉS CONTINUAR? (SI/NO): "

if /i not "!CONFIRMAR!"=="SI" (
    echo.
    echo  Operación cancelada. Tu proyecto queda intacto.
    pause
    exit /b 0
)

:: ============================================================
::  PASO 1: ELIMINAR ARCHIVOS DEL PROYECTO
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PASO 1 DE 2: Eliminando archivos de Palace
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

set "ELIMINADOS=0"
set "FALTANTES=0"

:: Eliminar carpeta ai_context
if exist "%PROYECTO_PATH%\ai_context" (
    echo  Eliminando ai_context/...
    rmdir /s /q "%PROYECTO_PATH%\ai_context" 2>nul
    if errorlevel 1 (
        echo     ⚠️  No se pudo eliminar automáticamente
        set /a "FALTANTES+=1"
    ) else (
        echo     ✅ ai_context/ eliminada correctamente
        set /a "ELIMINADOS+=1"
    )
) else (
    echo  ⚠️  No se encontró ai_context/ en el proyecto (ya está limpio)
    set /a "FALTANTES+=1"
)

:: Eliminar archivo .palace.env
if exist "%PROYECTO_PATH%\.palace.env" (
    echo  Eliminando .palace.env...
    del /q "%PROYECTO_PATH%\.palace.env" 2>nul
    if errorlevel 1 (
        echo     ⚠️  No se pudo eliminar automáticamente
        set /a "FALTANTES+=1"
    ) else (
        echo     ✅ .palace.env eliminado correctamente
        set /a "ELIMINADOS+=1"
    )
) else (
    echo  ⚠️  No se encontró .palace.env en el proyecto (ya está limpio)
    set /a "FALTANTES+=1"
)

:: ============================================================
::  PASO 2: LIMPIAR REGISTRO EN EL FRAMEWORK
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PASO 2 DE 2: Limpando registro en el framework
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

set "MEMORY_DIR=%USERPROFILE%\palace-framework"

if not exist "%MEMORY_DIR%" (
    echo  ⚠️  El framework Palace no está instalado globalmente.
    echo     No se puede eliminar el registro automáticamente.
    echo     Para eliminarlo manualmente, ejecutá en tu proyecto:
    echo     palace delete-project
    echo.
    goto :resumen
)

set "VENV_ACTIVATE=%MEMORY_DIR%\.venv\Scripts\activate.bat"

if not exist "%VENV_ACTIVATE%" (
    echo  ⚠️  No se encontró el entorno virtual de Palace en: %MEMORY_DIR%\.venv
    echo     No se puede eliminar el registro automáticamente.
    echo     Para eliminarlo manualmente, ejecutá en tu proyecto:
    echo     palace delete-project
    echo.
    goto :resumen
)

echo  Buscando el registro del proyecto en el framework...

:: Activar entorno virtual y ejecutar limpieza de registro
call "%VENV_ACTIVATE%" >nul 2>&1

if exist "%MEMORY_DIR%\src" (
    echo  Ejecutando limpieza automática del registro en la base de datos...
    echo.

    python -c "import sys; sys.path.insert(0, r'%MEMORY_DIR%\src'); from palace.core.context_manager import ContextManager; from palace.config.settings import PalaceSettings; import asyncio; async def main(): settings = PalaceSettings(); manager = ContextManager(settings); await manager.initialize(); await manager.delete_by_project(r'%PROYECTO_PATH%'); await manager.shutdown(); asyncio.run(main())" 2>nul

    if %errorlevel% equ 0 (
        echo  ✅ Registro eliminado correctamente de la base de datos del framework
        set /a "ELIMINADOS+=1"
    ) else (
        echo  ⚠️  No se pudo eliminar el registro automáticamente
        echo     Probá ejecutar manualmente en tu proyecto:
        echo     palace delete-project
        set /a "FALTANTES+=1"
    )
) else (
    echo  ⚠️  No se encontró el código fuente del framework en: %MEMORY_DIR%\src
    echo     Probá ejecutar manualmente en tu proyecto:
    echo     palace delete-project
    set /a "FALTANTES+=1"
)

:: ============================================================
::  RESUMEN FINAL
:: ============================================================
:resumen
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                           ║
echo  ║         ✅  LIMPIEZA COMPLETADA                           ║
echo  ║                                                           ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Resumen de operaciones realizadas en: %PROYECTO_PATH%
echo.
echo  Elementos eliminados: %ELIMINADOS%
echo  Elementos no encontrados (ya estaban limpios): %FALTANTES%
echo.
echo  Lo que NO se eliminó (y no debería):
echo    [✓] Tu código fuente (archivos .py, .js, .php, etc.)
echo    [✓] Configuraciones de tu proyecto (requirements.txt, package.json, etc.)
echo.
echo  Si querés eliminar completamente TODO rastro de Palace de tu proyecto,
echo  también podés borrar manualmente los siguientes archivos si existen:
echo    - .env (si solo tiene configuraciones de Palace)
echo    - .gitignore (si solo tiene entradas de Palace)
echo.
echo  IMPORTANTE: Si volvés a ejecutar palace init en este proyecto,
echo              se regenerarán los archivos de contexto automáticamente.
echo.
pause
endlocal
