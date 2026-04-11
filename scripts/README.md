# Palace Framework — Scripts de Instalación y Desinstalación

Este directorio contiene los scripts necesarios para instalar, desinstalar y gestionar el Palace Framework en sistemas Windows.

---

## 📁 Archivos Disponibles

### Scripts de Instalación

| Archivo | Descripción |
|---------|-------------|
| `instalar-palace.bat` | Script principal de instalación — configura el framework global y el entorno virtual |

### Scripts de Desinstalación

| Archivo | Descripción |
|---------|-------------|
| `desinstalar-todo.bat` | **Menú principal** — selecciona qué operación querés realizar |
| `desinstalar-palace.bat` | Elimina el framework global (comando `palace`) |
| `limpiar-proyecto.bat` | Elimina las configuraciones de un proyecto específico (versión interactiva) |
| `limpiar-proyecto-rapido.bat` | Elimina las configuraciones de un proyecto específico (versión rápida desde CLI) |

### Documentación

| Archivo | Descripción |
|---------|-------------|
| `README-desinstalacion.md` | Guía completa de desinstalación |

---

## 🚀 Cómo Usar

### Instalación

1. Haz doble clic en **`instalar-palace.bat`**
2. Seguí los pasos del asistente
3. El script configurará:
   - El entorno virtual
   - Las dependencias
   - El comando `palace` global
   - Los archivos de contexto en tu proyecto

### Desinstalación

#### Opción 1: Menú Principal (Recomendado)

1. Haz doble clic en **`desinstalar-todo.bat`**
2. Seleccioná la operación deseada:
   - `[1]` Desinstalar framework global
   - `[2]` Limpiar proyecto específico
   - `[3]` Desinstalación completa
   - `[4]` Cancelar

#### Opción 2: Scripts Individuales

**Desinstalar framework global:**
```cmd
desinstalar-palace.bat
```

**Limpiar proyecto específico (versión interactiva):**
```cmd
limpiar-proyecto.bat
```

**Limpiar proyecto específico (versión rápida):**
```cmd
limpiar-proyecto-rapido.bat
```

O con ruta como argumento:
```cmd
limpiar-proyecto-rapido.bat "C:\Proyectos\mi-proyecto"
```

---

## 📋 Lo Que Se Elimina

### Framework Global

| Elemento | Ruta |
|----------|------|
| Repositorio | `%USERPROFILE%\palace-framework\` |
| Entorno virtual | `%USERPROFILE%\palace-framework\.venv\` |
| Comando PATH | `%USERPROFILE%\palace-framework\.venv\Scripts` |

### Proyectos Individuales

| Elemento | Ruta en proyecto |
|----------|------------------|
| Archivos de contexto | `ai_context/` |
| Configuración | `.palace.env` |
| Registro | En base de datos del framework |

### Nota sobre scripts de limpieza rápida

El script `limpiar-proyecto-rapido.bat` detecta automáticamente el directorio actual si no le pasás una ruta, y te permite confirmar antes de eliminar. Es ideal para usar cuando ya estás en la carpeta de tu proyecto.

---

## ⚠️ Importante

1. **Los proyectos NO se eliminan** — tu código fuente queda intacto
2. **Reiniciá la terminal** después de desinstalar para que el PATH se actualice
3. Los archivos `ai_context/` en tus proyectos **no se eliminan automáticamente** — tenés que borrarlos manualmente si querés limpiar todo rastro

---

## 🔧 Desinstalación Manual (Si es necesario)

### Quitar del PATH

Ejecutá en PowerShell:
```powershell
$path = [Environment]::GetEnvironmentVariable('Path', 'User')
$path = ($path -split ';' | Where-Object { $_ -ne '%USERPROFILE%\palace-framework\.venv\Scripts' }) -join ';'
[Environment]::SetEnvironmentVariable('Path', $path, 'User')
```

### Borrar carpeta de Palace

```cmd
rmdir /s /q "%USERPROFILE%\palace-framework"
```

---

## ❓ Preguntas Frecuentes

### ¿Se eliminan mis proyectos?
**NO.** Los scripts solo eliminan:
- El framework Palace (comando `palace`)
- Los archivos de contexto `ai_context/` en tus proyectos (si usás los scripts de limpieza)

### ¿Puedo reinstalar después?
**Sí.** Volvé a ejecutar `instalar-palace.bat` cuando quieras.

### ¿Qué pasa con las configuraciones guardadas?
Todas las configuraciones y registros se eliminan con la desinstalación completa.

---

## 📞 Soporte

Si tenés problemas durante la desinstalación:
1. Verificá que tengas permisos de escritura en `%USERPROFILE%`
2. Ejecutá el script como Administrador si遇到 errores de permisos
3. Consultá los logs en pantalla — todos los pasos se muestran en tiempo real

---

**Versión:** 1.0  
**Última actualización:** 2025-04-05