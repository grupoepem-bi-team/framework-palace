@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

title Palace Framework - Menú Principal de Desinstalación

:: ============================================================
::  PANTALLA DE BIENVENIDA
:: ============================================================
cls
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║                                                   ║
echo  ║        🏛️  PALACE FRAMEWORK                      ║
echo  ║        Desinstalador Completo                    ║
echo  ║                                                   ║
echo  ║        Elimina configuraciones del framework     ║
echo  ║                                                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Seleccioná una opción:
echo.
echo    [1] Desinstalar framework global (comando 'palace')
echo    [2] Limpiar proyecto específico
echo    [3] Desinstalación completa (todo lo anterior)
echo    [4] Cancelar
echo.
set /p "OPCION=Ingresá tu opción (1/2/3/4): "

if "%OPCION%"=="4" goto :cancel
if "%OPCION%"=="1" goto :uninstall_only
if "%OPCION%"=="2" goto :cleanup_project
if "%OPCION%"=="3" goto :full_uninstall

cls
echo  ❌ Opción inválida. Ejecutá el script de nuevo.
pause
exit /b 1

:: ============================================================
::  OPCIÓN 1: SOLO DESINSTALAR COMANDO GLOBAL
:: ============================================================
:uninstall_only
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  DESINSTALAR FRAMEWORK GLOBAL
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

set "SCRIPTS_PATH=%USERPROFILE%\palace-framework\.venv\Scripts"

:: Verificar si ya está eliminado
for /f "tokens=2,*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%b"

if not defined USER_PATH (
    echo  ⚠️  No hay PATH definido para el usuario.
    goto :completed
)

echo %USER_PATH% | findstr /i /c:"%SCRIPTS_PATH%" >nul 2>&1
if errorlevel 1 (
    echo  ✅ El comando 'palace' ya no está en el PATH del usuario.
    goto :completed
)

:: Eliminar del PATH usando PowerShell
powershell -Command ^
    "$path = [Environment]::GetEnvironmentVariable('Path', 'User'); ^
    $path = ($path -split ';' ^| Where-Object { $_ -ne '%SCRIPTS_PATH%' }) -join ';'; ^
    [Environment]::SetEnvironmentVariable('Path', $path, 'User')" 2>nul

if %errorlevel% equ 0 (
    echo  ✅ Ruta eliminada del PATH del usuario.
    echo     REINICIÁ tu terminal para que surta efecto.
) else (
    echo  ⚠️  No se pudo eliminar automáticamente.
)

goto :completed

:: ============================================================
::  OPCIÓN 2: LIMPIAR PROYECTO ESPECÍFICO
:: ============================================================
:cleanup_project
cls
call "%~dp0limpiar-proyecto.bat"
goto :end

:: ============================================================
::  OPCIÓN 3: DESINSTALACIÓN COMPLETA
:: ============================================================
:full_uninstall
cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  DESINSTALACIÓN COMPLETA
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

:: Definir rutas
set "PALACE_DIR=%USERPROFILE%\palace-framework"

:: Confirmación
echo  ⚠️  VAS A ELIMINAR:
echo    - %PALACE_DIR%\  (todo el repositorio)
echo    - El acceso global al comando 'palace'
echo    - Los archivos de contexto en tus proyectos
echo.
echo  IMPORTANTE: Los proyectos que usan Palace (como moodle_clon)
echo              NO se eliminarán, pero los archivos ai_context/
echo              tendrás que borrarlos manualmente si querés.
echo.
set /p "CONFIRMAR=¿QUERÉS CONTINUAR? (SI/NO): "

if /i not "!CONFIRMAR!"=="SI" (
    echo  Desinstalación cancelada.
    pause
    exit /b 0
)

cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PASO 1: Eliminando acceso global al comando 'palace'
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

set "SCRIPTS_PATH=%USERPROFILE%\palace-framework\.venv\Scripts"

:: Eliminar del PATH usando PowerShell
powershell -Command ^
    "$path = [Environment]::GetEnvironmentVariable('Path', 'User'); ^
    $path = ($path -split ';' ^| Where-Object { $_ -ne '%SCRIPTS_PATH%' }) -join ';'; ^
    [Environment]::SetEnvironmentVariable('Path', $path, 'User')" 2>nul

if %errorlevel% equ 0 (
    echo  ✅ Ruta eliminada del PATH del usuario.
) else (
    echo  ⚠️  No se pudo eliminar del PATH automáticamente.
)

cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PASO 2: Eliminando archivos de Palace
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

:: Eliminar el repositorio de Palace
if exist "%PALACE_DIR%" (
    echo  Eliminando: %PALACE_DIR%
    rmdir /s /q "%PALACE_DIR%" 2>&1
    if errorlevel 1 (
        echo  ❌ No se pudo eliminar automáticamente.
        echo     Probá borrar manualmente: %PALACE_DIR%
    ) else (
        echo  ✅ Repositorio eliminado.
    )
) else (
    echo  ⚠️  No se encontró el repositorio: %PALACE_DIR%
)

cls
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PASO 3: Resumen
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

:: ============================================================
::  PANTALLA FINAL
:: ============================================================
:completed
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                           ║
echo  ║         ✅  OPERACIÓN COMPLETADA                          ║
echo  ║                                                           ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  IMPORTANTE:
echo    - Reiniciá tu terminal para que el PATH se limpie
echo    - Los archivos de contexto en tus proyectos (ai_context/)
echo      no se eliminan automáticamente — borrálos manualmente
echo      si querés limpiar todo rastro
echo    - Si querés eliminar un proyecto específico de Palace:
echo      Ejecutá 'palace delete-project' en ese proyecto
echo.
pause
goto :end

:: ============================================================
::  CANCELAR
:: ============================================================
:cancel
cls
echo  Operación cancelada.
pause

:end
endlocal
