@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

title Palace Framework - Limpiar Proyecto

:: ============================================================
::  PANTALLA DE BIENVENIDA
:: ============================================================
cls
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║                                                   ║
echo  ║        🏛️  PALACE FRAMEWORK                      ║
echo  ║        Limpiar Proyecto                          ║
echo  ║                                                   ║
echo  ║        Elimina las configuraciones de Palace     ║
echo  ║        de un proyecto específico                 ║
echo  ║                                                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Este script eliminará:
echo    - La carpeta ai_context/
echo    - El archivo .palace.env (si existe)
echo    - El registro del proyecto en el framework
echo.
echo  IMPORTANTE: NO eliminará tu código fuente.
echo.
pause

:: ============================================================
::  OBTENER RUTA DEL PROYECTO
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  INGRESAR RUTA DEL PROYECTO
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo  Ingresá la ruta completa del proyecto:
echo  Ejemplo: C:\Proyectos\moodle_clon
echo.
set /p "PROYECTO_PATH=Ruta del proyecto: "

if "%PROYECTO_PATH%"=="" (
    echo  ❌ Ruta vacía.
    pause
    exit /b 1
)

:: Normalizar ruta (quitar espacios extras)
set "PROYECTO_PATH=%PROYECTO_PATH: =%"

if not exist "%PROYECTO_PATH%" (
    echo  ❌ El proyecto no existe: %PROYECTO_PATH%
    pause
    exit /b 1
)

cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  CONFIRMACIÓN
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo  Proyecto: %PROYECTO_PATH%
echo.
echo  Se eliminarán:
echo    - %PROYECTO_PATH%\ai_context\
echo    - %PROYECTO_PATH%\.palace.env
echo.
set /p "CONFIRMAR=¿QUERÉS CONTINUAR? (SI/NO): "

if /i not "!CONFIRMAR!"=="SI" (
    echo  Operación cancelada.
    pause
    exit /b 0
)

cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  ELIMINANDO ARCHIVOS
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

:: Eliminar carpeta ai_context
if exist "%PROYECTO_PATH%\ai_context" (
    rmdir /s /q "%PROYECTO_PATH%\ai_context" >nul 2>&1
    if errorlevel 1 (
        echo  ⚠️  No se pudo eliminar ai_context/ automáticamente
    ) else (
        echo  ✅ ai_context/ eliminada
    )
) else (
    echo  ⚠️  No se encontró ai_context/ en el proyecto
)

:: Eliminar archivo .palace.env
if exist "%PROYECTO_PATH%\.palace.env" (
    del /q "%PROYECTO_PATH%\.palace.env" >nul 2>&1
    if errorlevel 1 (
        echo  ⚠️  No se pudo eliminar .palace.env automáticamente
    ) else (
        echo  ✅ .palace.env eliminado
    )
) else (
    echo  ⚠️  No se encontró .palace.env en el proyecto
)

:: ============================================================
::  LIMPIAR REGISTRO EN EL FRAMEWORK
:: ============================================================
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  LIMPIAR REGISTRO EN EL FRAMEWORK
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo  Buscando el archivo de memoria del framework...
echo.

:: Buscar el archivo de memoria del framework
set "MEMORY_DIR=%USERPROFILE%\palace-framework"

if not exist "%MEMORY_DIR%" (
    echo  ⚠️  No se encontró el repositorio de Palace: %MEMORY_DIR%
    echo     Probá ejecutar manualmente en el proyecto:
    echo     palace delete-project
    goto :summary
)

set "MEMORY_FILE=%MEMORY_DIR%\.venv\Lib\site-packages\palace\memory\projects.db"

if exist "%MEMORY_DIR%\.venv" (
    echo  Ejecutando limpieza automática del registro...
    echo.

    call "%MEMORY_DIR%\.venv\Scripts\activate.bat" >nul 2>&1
    if exist "%MEMORY_DIR%\src" (
        python -c "import sys; sys.path.insert(0, r'%MEMORY_DIR%\src'); from palace.core.context_manager import ContextManager; from palace.config.settings import PalaceSettings; import asyncio; async def main(): settings = PalaceSettings(); manager = ContextManager(settings); await manager.initialize(); await manager.delete_by_project(r'%PROYECTO_PATH%'); await manager.shutdown(); asyncio.run(main())" 2>nul
    )

    if %errorlevel% equ 0 (
        echo  ✅ Registro eliminado del framework
    ) else (
        echo  ⚠️  No se pudo eliminar el registro automáticamente
        echo     Probá ejecutar manualmente en el proyecto:
        echo     palace delete-project
    )
) else (
    echo  ⚠️  No se encontró el entorno virtual de Palace
    echo     Probá ejecutar manualmente en el proyecto:
    echo     palace delete-project
)

:: ============================================================
::  RESUMEN FINAL
:: ============================================================
:summary
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                           ║
echo  ║         ✅  LIMPIEZA COMPLETADA                           ║
echo  ║                                                           ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Resumen:
echo    - ai_context/: eliminada (si existía)
echo    - .palace.env: eliminado (si existía)
echo    - Registro en framework: verificado arriba
echo.
echo  Tu código fuente NO se eliminó.
echo.
pause
endlocal
