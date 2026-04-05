# Deferred Work Items

This file tracks issues and improvements that have been deferred from code reviews.

---

## Deferred from: code review of 3-4-load-templates-from-markdown (2026-04-04)

### [W1] Singleton Cache Testing Issues
**Source:** Edge Case Hunter  
**Location:** `cache.py:180-215`  
**Issue:** Global singleton makes test isolation difficult  
**Defer Reason:** Testing infrastructure issue, not blocking functionality  
**Defer To:** Testing story or Epic 4

### [W2] Thread Lock Scope Optimization
**Source:** Edge Case Hunter  
**Location:** `cache.py:112-116`  
**Issue:** is_stale() wraps entire method in lock for read-only operation  
**Defer Reason:** Performance optimization, not correctness issue (RLock allows concurrent reads anyway)  
**Defer To:** Performance optimization phase

### [W3] Category List Hardcoded
**Source:** Acceptance Auditor  
**Location:** `validator.py:35`  
**Issue:** VALID_CATEGORIES list hardcoded, requires code change to extend  
**Defer Reason:** Architectural improvement, not blocking current functionality  
**Defer To:** Configuration system story

### [W4] Missing Cache Cleanup for Deleted Files
**Source:** Edge Case Hunter  
**Location:** `cache.py` (no specific method)  
**Issue:** No mechanism to remove cache entries for deleted template files  
**Defer Reason:** Feature enhancement requiring background tasks or TTL mechanism  
**Defer To:** Epic 5 or maintenance phase

---

## Deferred from: code review of 4-4-error-recovery-workflow (2026-04-04)

### [W5] AUDIO_CLEANUP_GUIDE Inline Dictionary
**Source:** Blind Hunter  
**Location:** `media.py:39-96`  
**Issue:** 58-line inline dictionary in module root. Consider externalizing to JSON/YAML for easier editing without code changes.  
**Defer Reason:** Works correctly, can be improved post-MVP without breaking changes  
**Defer To:** Maintenance phase or configuration system story

### [W6] Hardcoded Search Patterns for Cleaned Clips
**Source:** Blind Hunter  
**Location:** `media.py:1236-1240`  
**Issue:** Search patterns `*cleaned*`, `*NR*` are hardcoded. Should be configurable per user preference.  
**Defer Reason:** Works for MVP, low priority enhancement  
**Defer To:** Configuration system story or user preferences epic

### [W7] Guide Structure Validation
**Source:** Edge Case Hunter  
**Location:** `media.py` (get_cleanup_guide handler)  
**Issue:** Guide content returned directly without structure validation. If structure changes, Lua may break.  
**Defer Reason:** Overkill for MVP - static structure is well-tested  
**Defer To:** Future enhancement when guide becomes dynamic
