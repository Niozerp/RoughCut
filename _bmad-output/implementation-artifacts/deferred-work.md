## Deferred from: code review of 5-1-initiate-rough-cut-generation (2026-04-04)

### Race condition on session status check-then-act
- **Reason:** Pre-existing session manager pattern, not introduced by this change
- **Context:** Multiple concurrent requests could theoretically cause race conditions where two requests both check session.status == "format_selected" before either calls start_generation(). The session manager has basic locking but no atomic check-then-act semantics. This is a pre-existing architectural issue in session.py.

## Deferred from: code review of 6-1-create-new-timeline (2026-04-04)

### Unicode character handling in name sanitization [builder.py:387]
- **Reason:** UI enhancement, not blocking functionality
- **Context:** Non-ASCII characters (Chinese, Arabic, Cyrillic, accented) are replaced with underscores during name sanitization. This degrades user experience for non-English content but timelines are still created successfully.

### Timestamp format handling for ISO with timezone [builder.py:312-313]
- **Reason:** Edge case, most timestamps won't include timezone
- **Context:** ISO timestamps with timezone offsets like `2026-04-04T12:30:00+00:00` are not fully handled. The `+00:00` portion remains in the name. Most Resolve-generated timestamps won't have timezones.

### Media pool search only checks root folder [resolve_api.py:324-352]
- **Reason:** Could cause duplicate imports but non-critical
- **Context:** The `find_media_in_pool()` function only searches the root folder of the media pool. Media organized in subfolders won't be found for duplicate detection, potentially causing unnecessary re-imports.

### Windows case-insensitive path comparison [resolve_api.py:344]
- **Reason:** Could cause duplicate imports on Windows
- **Context:** File path comparison in `find_media_in_pool()` uses direct string comparison after `os.path.normpath()`. On Windows, paths like `C:\Media\File.mp4` and `c:\media\file.mp4` are the same file but comparison fails. May cause duplicate media imports.

### Track verification failure handling [builder.py:214-215]
- **Reason:** Warning only, doesn't stop operation
- **Context:** If track setup verification fails, only a warning is logged and operation continues. Could lead to timeline with wrong track count. Consider making this an error condition or including verification status in result.

## Deferred from: Fix Media Indexing Crash - Secondary Resilience (2026-04-12)

### Large file handling (>1GB) with skip option
- **Reason:** Secondary to crash diagnostics; part of broader resilience work
- **Context:** Files larger than 1GB during hashing can cause OOM. Add size check before hashing with configurable limit.

### File permission error resilience in scanner.py
- **Reason:** Secondary to crash diagnostics; part of broader resilience work  
- **Context:** Files with permission errors should be skipped with warning, not crash the entire scan.

### Network drive unavailability handling
- **Reason:** Secondary to crash diagnostics; part of broader resilience work
- **Context:** Network drives that become inaccessible during indexing should fail gracefully for that folder only.

### MediaBrowser retry action UI
- **Reason:** UI enhancement after core crash fixes are in place
- **Context:** Add a retry button in the MediaBrowser when indexing fails, allowing users to retry without reloading the app.


