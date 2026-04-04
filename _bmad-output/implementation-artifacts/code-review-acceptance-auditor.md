# Acceptance Auditor Review Prompt

## Story: 2.2 - Incremental Media Indexing

You are the **Acceptance Auditor** — checking implementation against requirements. You have the story spec and context documents.

### Story File

**Location**: `_bmad-output/implementation-artifacts/2-2-incremental-media-indexing.md`

### Acceptance Criteria (from Story)

1. **AC #1**: Given I have configured media folders, When I trigger manual indexing, Then the system scans only new or changed files since last index

2. **AC #2**: Given Media indexing is in progress, When The operation exceeds 5 seconds, Then A blocking UI with progress indicator displays, And I see clear status messages (e.g., "Indexing: epic_whoosh.wav")

3. **AC #3**: Given Indexing is running, When Progress updates occur, Then Updates display every N items or every M seconds (never >5 seconds without update)

4. **AC #4**: Given 100 new assets are being indexed, When The process completes, Then It finishes within 2 minutes on standard consumer hardware

### Implementation Files

Same 10 files as previous reviewers - see Blind Hunter prompt for full contents.

### Technical Requirements (from Dev Notes)

- **Lua/Python Split**: GUI in Lua, logic in Python
- **JSON-RPC Protocol**: Progress updates streamed via JSON-RPC
- **Async Processing**: Python uses `async/await` for I/O
- **Progress Reporting**: Updates every N items or M seconds, never >5s gap
- **Performance**: <2 minutes for 100 assets (NFR1)
- **File Hash Caching**: MD5 for change detection
- **Database**: SpacetimeDB for asset storage

### Tasks from Story (All Marked Complete)

- ✅ File system scanning with change detection
- ✅ Incremental indexing algorithm  
- ✅ Progress reporting system
- ✅ Blocking UI with progress dialog
- ✅ Database models
- ✅ Performance optimization
- ✅ Integration testing

---

## YOUR TASK

Review the code against the spec and acceptance criteria. Check for:

1. **Violations of acceptance criteria** - Code doesn't meet AC requirements
2. **Deviations from spec intent** - Implementation differs from spec purpose
3. **Missing implementation** - Specified behavior not implemented
4. **Contradictions** - Code contradicts spec constraints

### Output Format

```markdown
1. **AC Violation**: [Which AC is violated]
   - **Finding**: [Description of the issue]
   - **Evidence**: [Code reference showing the problem]
   - **Severity**: [Blocker/High/Med/Low]
   - **Fix Required**: [What needs to change]

2. **Spec Deviation**: [Which spec section]
   - **Finding**: [How implementation differs]
   - **Evidence**: [Code vs Spec comparison]
   - **Impact**: [What this affects]
```

---

## DETAILED REVIEW CHECKLIST

### AC #1: Incremental Scanning

**Required Behavior**:
- System scans only new or changed files since last index
- Must not re-process unchanged files
- Must detect deleted files

**Code Areas to Check**:
- `incremental.py:scan_for_changes()` - Does it correctly identify only new/modified/deleted?
- `indexer.py:index_media()` - Does it skip unchanged files?
- `hash_cache.py` - Is MD5 hashing used for change detection?

**Potential Issues**:
- Hash computation might be expensive for large files
- No persistent storage of index state (hash_cache.save_to_disk exists but not integrated)
- Database storage is placeholder (`_store_assets_batch` is no-op)

### AC #2: Blocking UI with Progress

**Required Behavior**:
- Blocking UI appears after 5 seconds
- Progress indicator displays
- Clear status messages show current file

**Code Areas to Check**:
- `lua/roughcut/progress_dialog.lua` - Is it actually blocking? (Currently simulated/non-blocking)
- `indexer.py:_send_progress()` - Does it send current file name?
- Is there a 5-second threshold before showing UI?

**Potential Issues**:
- Lua progress dialog is not actually blocking (just prints to console)
- No mechanism to trigger UI after 5 seconds
- FFI definitions may not match actual Fusion API

### AC #3: Progress Update Frequency

**Required Behavior**:
- Updates every N items OR every M seconds
- Never >5 seconds without update

**Code Areas to Check**:
- `indexer.py:_maybe_send_progress()` - Check the logic
- `update_interval = 5.0` and `items_per_update = 10`

**Actual Code**:
```python
if (now - self._last_update_time >= self.update_interval or 
    items_since_update >= self.items_per_update):
```

**Status**: ✅ Correctly implements the requirement

### AC #4: Performance (<2min for 100 assets)

**Required Behavior**:
- 100 assets indexed in <2 minutes

**Code Areas to Check**:
- `scanner.py` - Uses async with thread pool
- `incremental.py` - O(n) lookup using dictionary
- `hash_cache.py` - Caches hashes, uses mtime quick check
- Batch operations in `_store_assets_batch`

**Potential Issues**:
- No actual performance benchmarking
- MD5 hashing could be slow for large media files
- No file size limits or streaming for large files
- Database operations are placeholders

### Technical Requirements Review

**Lua/Python Split**:
- ✅ Lua: `progress_dialog.lua`
- ✅ Python: All backend logic

**JSON-RPC Protocol**:
- ✅ `media.py` adds handlers
- ⚠️ Progress updates sent via callback, but JSON-RPC streaming not fully implemented

**Async Processing**:
- ✅ `async/await` used in scanner and indexer
- ⚠️ `index_media` handler creates new event loop each call - potential resource leak

**File Hash Caching**:
- ✅ MD5 with chunked reading
- ✅ Mtime-based quick check
- ⚠️ No integration with persistent storage

**SpacetimeDB**:
- ⚠️ Database operations are placeholders (TODO comments)
- Models defined but not connected to actual DB

---

## REVIEWER OUTPUT

Provide your findings as a Markdown list. For each finding:

1. **Which AC or spec section** is affected
2. **What the code does** vs **what the spec requires**
3. **Evidence** from the code
4. **Severity** (Blocker/High/Med/Low)
5. **Required fix**

Focus on SPEC VIOLATIONS and MISSING IMPLEMENTATION, not general code quality.
