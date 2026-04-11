# Migration Guide — Palace Framework Refactoring

This guide documents the breaking changes introduced in the refactoring effort and how to migrate your code.

---

## Overview

The refactoring focused on:

1. **Consolidated Domain Types** — All enums moved to a single source of truth
2. **Security Hardening** — Default values changed to be more secure
3. **Code Quality** — Removed dead code and fixed naming inconsistencies

---

## Breaking Changes

### 1. Domain Types Location

**Before:**
```python
from palace.core.types import AgentRole, TaskStatus
from palace.models import AgentRole, TaskStatus  # Duplicate!
```

**After:**
```python
# Single source of truth
from palace.models.domain_types import AgentRole, TaskStatus, MemoryType, ...

# Re-exported for backward compatibility (deprecated)
from palace.core.types import AgentRole, TaskStatus  # Use models.domain_types instead
```

**Migration:**
- Update imports to use `palace.models.domain_types`
- Remove duplicate imports from `palace.models`
- `palace.core.types` still works but will be deprecated in v0.2

---

### 2. Security Defaults

**Before:**
- `API.host`: `0.0.0.0` (exposed to all interfaces)
- `CORS.origins`: `["*"]` (allowed all origins)
- `Security.secret_key`: `"change-me-in-production"` (insecure default)

**After:**
- `API.host`: `"127.0.0.1"` (localhost only by default)
- `CORS.origins`: `[]` (empty list, no origins allowed by default)
- `Security.secret_key`: `""` (empty string, raises error in production)

**Migration:**

If you were using the API, add explicit configuration:

```env
# .env file example
API_HOST=0.0.0.0          # If you need external access (NOT recommended)
CORS_ORIGINS=https://your-domain.com,https://admin.your-domain.com
SECRET_KEY=your-secure-random-string-here
```

**Important:** The framework now **raises an error in production** if `SECRET_KEY` is not set.

---

### 3. Removed Files

**Deleted:**
- `src/palace/core/memory_quality.py` — Not used, functionality moved to memory stores

**Migration:**
- Remove any imports referencing `palace.core.memory_quality`
- The functionality is now integrated into the memory store classes

---

### 4. Configuration Changes

**Before:**
```python
from palace.core.config import settings

# Insecure defaults (no validation)
print(settings.security.secret_key)  # "change-me-in-production"
```

**After:**
```python
from palace.core.config import settings

# Validation enforced
secret_key = settings.get_secret_key()  # Raises error if production + no key
```

**Migration:**
- Use `settings.get_secret_key()` instead of direct attribute access
- Add `SECRET_KEY` to your `.env` file before deploying

---

### 5. Models Simplified

**Before:**
- `palace/core/types.py` had Pydantic models
- `palace/models/__init__.py` had duplicate Pydantic models

**After:**
- `palace/models/domain_types.py` — Domain enums only
- `palace/models/__init__.py` — Pydantic request/response models only

**Migration:**
- Import domain types from `palace.models.domain_types`
- Import API models from `palace.models` (unchanged)
- Dataclasses moved to `palace.core.types` (backward compatible)

---

## Migration Checklist

### For All Users

- [ ] Update imports: `from palace.models.domain_types import ...`
- [ ] Add `SECRET_KEY` to `.env` before deploying to production
- [ ] Update CORS configuration: `CORS_ORIGINS=...`
- [ ] Remove imports of `palace.core.memory_quality`

### For API Users

- [ ] Test with new host setting (`127.0.0.1`)
- [ ] Configure CORS origins explicitly
- [ ] Update client to use correct API key header

### For CLI Users

- [ ] No changes required if using default settings
- [ ] Add `.env` with custom configuration if needed

---

## Testing the Migration

Run the following to verify your migration:

```bash
# Test imports
python -c "from palace.models.domain_types import AgentRole, TaskStatus; print('OK')"

# Test configuration
python -c "from palace.core.config import settings; print(settings.api.host)"

# Test framework initialization (if applicable)
python -c "from palace import PalaceFramework; print('Framework import OK')"
```

---

## Support

If you encounter issues:

1. Check the **Analysis of Issues** in `agent_git.md`
2. Review the **Suggested Improvements** section
3. Create an issue with the error message and code snippet

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2025-04-05 | Initial release with refactoring |
| 0.1.1 | TBD | Will remove deprecated imports |

---

**Note:** This is a breaking change release. Plan accordingly for your deployments.
```

Ahora voy a commit y push los cambios: