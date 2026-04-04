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

## Deferred from: previous reviews

(No previous deferred items)
