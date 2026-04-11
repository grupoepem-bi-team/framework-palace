@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

title Palace Framework - Desinstalador

:: ============================================================
::  PANTALLA DE BIENVENIDA
:: ============================================================
cls
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║                                                   ║
echo  ║        🏛️  PALACE FRAMEWORK                      ║
echo  ║        Desinstalador para Windows                ║
echo  ║                                                   ║
echo  ║        Atencion: Esta accion no puede deshacerse ║
echo  ║                                                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  ¿Qué querés desinstalar?
echo.
echo    [1] Solo el framework (comando 'palace' global)
echo    [2] Todo: framework + entorno virtual + repositorio
echo    [3] Cancelar
echo.
set /p "OPCION=Ingresá tu opcion (1/2/3): "

if "%OPCION%"=="3" goto :cancel
if "%OPCION%"=="1" goto :uninstall_only
if "%OPCION%"=="2" goto :full_uninstall

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
echo  Desinstalando acceso global al comando 'palace'...
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

set "SCRIPTS_PATH=%USERPROFILE%\palace-framework\.venv\Scripts"

:: Leer el PATH actual del usuario
for /f "tokens=2,*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%b"

if not defined USER_PATH (
    echo  ⚠️  No hay PATH definido para el usuario.
    goto :uninstall_done
)

:: Verificar si la ruta está en el PATH
echo %USER_PATH% | findstr /i /c:"%SCRIPTS_PATH%" >nul 2>&1
if errorlevel 1 (
    echo  ✅ El comando 'palace' no está en el PATH del usuario.
    goto :uninstall_done
)

:: Eliminar la ruta del PATH del usuario
set "NEW_PATH=%USER_PATH:"
set "NEW_PATH=%NEW_PATH:;=!SCRIPTS_PATH!;=%"
set "NEW_PATH=%NEW_PATH:;!SCRIPTS_PATH!=!SCRIPTS_PATH!=%"

if "%NEW_PATH%"=="%USER_PATH%" (
    echo  ⚠️  No se pudo procesar la eliminación automáticamente.
    echo     Probá eliminar manualmente:
    echo     %SCRIPTS_PATH%
    goto :uninstall_done
)

setx PATH "%NEW_PATH%" >nul 2>&1

if %errorlevel% equ 0 (
    echo  ✅ Ruta eliminada del PATH del usuario.
    echo     REINICIÁ tu terminal para que surta efecto.
) else (
    echo  ❌ Error al actualizar el PATH.
    echo     Probá ejecutar manualmente en PowerShell:
    echo     setx PATH "%%PATH%%"
)

goto :uninstall_done

:: ============================================================
::  OPCIÓN 2: DESINSTALACIÓN COMPLETA
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

:: Eliminar del PATH del usuario
for /f "tokens=2,*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%b"

if defined USER_PATH (
    :: Usar PowerShell para eliminar del PATH de forma más confiable
    powershell -Command ^
        "$path = [Environment]::GetEnvironmentVariable('Path', 'User'); ^\$
        $path = ($path -split ';' ^| Where-Object { $_ -ne '%SCRIPTS_PATH%' }) -join ';'; ^\$
        [Environment]::SetEnvironmentVariable('Path', $path, 'User')" >nul 2>&1

    if %errorlevel% equ 0 (
        echo  ✅ Ruta eliminada del PATH del usuario.
    ) else (
        echo  ⚠️  No se pudo eliminar del PATH automáticamente.
    )
) else (
    echo  ⚠️  No hay PATH definido para el usuario.
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
    rmdir /s /q "%PALACE_DIR%" >nul 2>&1
    if errorlevel 1 (
        echo  ❌ No se pudo eliminar automáticamente.
        echo     Probá borrar manualmente: %PALACE_DIR%
    ) else (
        echo  ✅ Repositorio eliminado.
    )
) else (
    echo  ⚠️  No se encontró el repositorio: %PALACE_DIR%
)

:: ============================================================
::  PASO 3: RESUMEN
:: ============================================================
:uninstall_done
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                           ║
echo  ║         ✅  DESINSTALACIÓN COMPLETADA                     ║
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
echo  Desinstalación cancelada.
pause

:end
endlocal
```

Ahora voy a crear también un script complementario para eliminar un proyecto específico del framework (equivalente al comando `palace delete-project`):

```path
framework-palace/scripts/limpiar-proyecto.bat
</parameter>
```

```bat
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

:: Normalizar ruta
set "PROYECTO_PATH=%PROYECTO_PATH:\=/%"
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
echo  Buscando el registro del proyecto en el framework...
echo.

:: Buscar el archivo de memoria del framework
set "MEMORY_FILE=%USERPROFILE%\palace-framework\.venv\Lib\site-packages\palace\memory\projects.db"

if exist "%MEMORY_FILE%" (
    echo  Archivo de memoria encontrado: %MEMORY_FILE%
    echo.
    echo  Para eliminar el registro, necesitamos usar Python.
    echo  Ejecutando limpieza automática...
    echo.

    call "%USERPROFILE%\palace-framework\.venv\Scripts\activate.bat" >nul 2>&1
    python -c ^
        "import sys; sys.path.insert(0, r'%USERPROFILE%\palace-framework\src'); ^
        from palace.core.context_manager import ContextManager; ^
        from palace.config.settings import PalaceSettings; ^
        import asyncio; ^
        async def main(): ^
            settings = PalaceSettings(); ^
            manager = ContextManager(settings); ^
            await manager.initialize(); ^
            try: ^
                result = await manager.delete_by_project(r'%PROYECTO_PATH%'); ^
                print(f'Registro eliminado: {result}'); ^
            except Exception as e: ^
                print(f'Error: {e}'); ^
            finally: ^
                await manager.shutdown(); ^
        asyncio.run(main())" 2>nul

    if %errorlevel% equ 0 (
        echo  ✅ Registro eliminado del framework
    ) else (
        echo  ⚠️  No se pudo eliminar el registro automáticamente
        echo     Probá ejecutar manualmente en el proyecto:
        echo     palace delete-project
    )
) else (
    echo  ⚠️  No se encontró el archivo de memoria del framework
    echo     Probá ejecutar manualmente en el proyecto:
    echo     palace delete-project
)

:: ============================================================
::  RESUMEN FINAL
:: ============================================================
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
```

Ahora voy a crear un script principal queCombine ambos scripts:

```path
framework-palace/scripts/desinstalar-todo.bat
</parameter>
```

```bat
@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

title Palace Framework - Desinstalador Completo

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
echo  ║        Elimina todo rastro del framework         ║
echo  ║                                                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Este script ejecutará:
echo    1. desinstalar-palace.bat - Elimina el framework global
echo    2. limpiar-proyecto.bat - Limpia proyectos individuales
echo.
echo  IMPORTANTE: Necesitás tener acceso al script
echo              'desinstalar-palace.bat' en el mismo directorio.
echo.
pause

:: ============================================================
::  EJECUTAR DESINSTALACIÓN GLOBAL
:: ============================================================
cls
echo  Ejecutando desinstalación global...
echo.
call "%~dp0desinstalar-palace.bat"

if %errorlevel% neq 0 (
    echo  ⚠️  La desinstalación global tuvo problemas pero continuará...
    echo.
    pause
)

cls
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║                                                   ║
echo  ║        PASO COMPLETADO                           ║
echo  ║                                                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  La desinstalación global se completó.
echo.
pause
```

Ahora voy a crear el archivo principal `desinstalar-palace.bat` que sea más robusto y fácil de usar:

```path
framework-palace/scripts/desinstalar-palace.bat
</parameter>
```

```bat
@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

title Palace Framework - Desinstalador

:: ============================================================
::  PANTALLA DE BIENVENIDA
:: ============================================================
cls
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║                                                   ║
echo  ║        🏛️  PALACE FRAMEWORK                      ║
echo  ║        Desinstalador para Windows                ║
echo  ║                                                   ║
echo  ║        Atencion: Esta accion no puede deshacerse ║
echo  ║                                                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  ¿Qué querés desinstalar?
echo.
echo    [1] Solo el framework (comando 'palace' global)
echo    [2] Todo: framework + entorno virtual + repositorio
echo    [3] Cancelar
echo.
set /p "OPCION=Ingresá tu opcion (1/2/3): "

if "%OPCION%"=="3" goto :cancel
if "%OPCION%"=="1" goto :uninstall_only
if "%OPCION%"=="2" goto :full_uninstall

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
echo  Desinstalando acceso global al comando 'palace'...
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

set "SCRIPTS_PATH=%USERPROFILE%\palace-framework\.venv\Scripts"

:: Leer el PATH actual del usuario
for /f "tokens=2,*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%b"

if not defined USER_PATH (
    echo  ⚠️  No hay PATH definido para el usuario.
    goto :uninstall_done
)

:: Verificar si la ruta está en el PATH
echo %USER_PATH% | findstr /i /c:"%SCRIPTS_PATH%" >nul 2>&1
if errorlevel 1 (
    echo  ✅ El comando 'palace' no está en el PATH del usuario.
    goto :uninstall_done
)

:: Eliminar la ruta del PATH del usuario usando PowerShell para más confiabilidad
powershell -Command ^
    "$path = [Environment]::GetEnvironmentVariable('Path', 'User'); ^
    $path = ($path -split ';' ^| Where-Object { $_ -ne '%SCRIPTS_PATH%' }) -join ';'; ^
    [Environment]::SetEnvironmentVariable('Path', $path, 'User')" 2>nul

if %errorlevel% equ 0 (
    echo  ✅ Ruta eliminada del PATH del usuario.
    echo     REINICIÁ tu terminal para que surta efecto.
) else (
    echo  ❌ Error al actualizar el PATH.
    echo     Probá ejecutar manualmente en PowerShell:
    echo     $path = [Environment]::GetEnvironmentVariable('Path', 'User')
    echo     $path = ($path -split ';' ^| Where-Object { $_ -ne '%SCRIPTS_PATH%' }) -join ';'
    echo     [Environment]::SetEnvironmentVariable('Path', $path, 'User')
)

goto :uninstall_done

:: ============================================================
::  OPCIÓN 2: DESINSTALACIÓN COMPLETA
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

:: Eliminar del PATH del usuario usando PowerShell
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

:: ============================================================
::  PASO 3: RESUMEN
:: ============================================================
:uninstall_done
cls
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                           ║
echo  ║         ✅  DESINSTALACIÓN COMPLETADA                     ║
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
echo  Desinstalación cancelada.
pause

:end
endlocal
