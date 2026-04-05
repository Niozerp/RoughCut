## Deferred from: code review of 5-1-initiate-rough-cut-generation (2026-04-04)

### Race condition on session status check-then-act
- **Reason:** Pre-existing session manager pattern, not introduced by this change
- **Context:** Multiple concurrent requests could theoretically cause race conditions where two requests both check session.status == "format_selected" before either calls start_generation(). The session manager has basic locking but no atomic check-then-act semantics. This is a pre-existing architectural issue in session.py.

## Deferred from: code review of 5-7-chunked-context-processing (2026-04-04)

### Unused Import of ContextChunker [ai.py:2066,2204]
- **Reason:** Code clutter but not harmful - cleanup later as part of general import hygiene
- **Context:** ContextChunker is imported but never used in the handler functions. Safe to remove in future cleanup pass.

### Hardcoded Configuration Values [prompt_engine.py:928-930]
- **Reason:** Consistent with existing codebase patterns
- **Context:** Temperature=0.3 and max_tokens=4000 are hardcoded in the new chunked prompt builder, but this matches the existing pattern elsewhere in the codebase. Should be refactored globally to use PromptConfig consistently across all prompt building methods.

