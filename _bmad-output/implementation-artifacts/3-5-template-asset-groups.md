# Story 3.5: Template Asset Groups

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a video editor,
I want format templates to define template asset groups for common scene elements,
So that the AI knows what types of assets to suggest for specific moments.

## Acceptance Criteria

1. **Given** A format template defines asset groups
   **When** The template is loaded
   **Then** Groups are parsed (e.g., "intro_music", "narrative_bed", "outro_chime")

2. **Given** Asset groups are defined
   **When** AI processes the rough cut
   **Then** It matches assets from the appropriate categories to template moments

3. **Given** Template specifies "corporate upbeat" music for intro
   **When** AI suggests music
   **Then** It searches indexed assets with "corporate" and "upbeat" tags

4. **Given** A format has multiple asset group types
   **When** RoughCut displays template details
   **Then** All groups are listed with their intended use cases

## Tasks / Subtasks

- [ ] Design AssetGroup data model (AC: #1, #4)
  - [ ] Create `AssetGroup` dataclass with: name, description, category, required_tags, optional_tags, duration_hint, priority
  - [ ] Define `AssetGroupCategory` enum: MUSIC, SFX, VFX, TRANSITION
  - [ ] Add validation for required vs optional tags
  - [ ] Support duration hints (exact, range, flexible)
  - [ ] Add priority scoring for asset matching (high/medium/low)

- [ ] Implement asset group YAML parser (AC: #1)
  - [ ] Create `AssetGroupParser` class for parsing YAML asset group definitions
  - [ ] Parse from template markdown `# Asset Groups` YAML code block
  - [ ] Handle nested group definitions (e.g., intro_music → variations)
  - [ ] Validate required fields: name, description, category, tags
  - [ ] Support optional fields: duration, priority, fallback_groups
  - [ ] Return list of `AssetGroup` objects

- [ ] Create asset group validator (AC: #1, #3)
  - [ ] Validate tag format (lowercase, no spaces, underscores allowed)
  - [ ] Check category is valid enum value
  - [ ] Validate duration format (ISO 8601 or mm:ss)
  - [ ] Ensure at least one tag specified per group
  - [ ] Log validation errors with group name and specific issues

- [ ] Build asset matching engine (AC: #2, #3)
  - [ ] Create `AssetMatcher` class to match indexed assets to asset groups
  - [ ] Implement tag-based scoring: exact match = 100%, partial = 50%, none = 0%
  - [ ] Add category filtering (only match music assets to MUSIC groups)
  - [ ] Support tag weighting (required vs optional tags)
  - [ ] Return ranked list of matching assets with scores
  - [ ] Limit results to top N matches (configurable, default 5)

- [ ] Implement asset matching protocol handler (AC: #2, #3)
  - [ ] Add `match_assets_for_group` protocol method
  - [ ] Accept: session_id, group_name, media_category
  - [ ] Query indexed media from database (Story 2.x patterns)
  - [ ] Apply asset matching algorithm
  - [ ] Return: list of matched assets with scores and paths
  - [ ] Handle errors: group not found, no matching assets, database error

- [ ] Create template asset groups display UI (AC: #4)
  - [ ] Add asset groups section to template preview dialog
  - [ ] Display groups by category: Music, SFX, VFX, Transitions
  - [ ] Show per-group: description, required tags, duration hint
  - [ ] Add "View Matching Assets" button per group (opens browser)
  - [ ] Handle templates with no asset groups gracefully

- [ ] Add asset group matching preview (AC: #3, #4)
  - [ ] Create "Preview Matches" feature in format management
  - [ ] For each asset group, show top 3 matching indexed assets
  - [ ] Display match scores and asset metadata (name, tags, path)
  - [ ] Indicate when no assets match (helps editors expand library)

- [ ] Testing and validation (AC: #1, #2, #3, #4)
  - [ ] Unit tests for `AssetGroup` dataclass validation
  - [ ] Unit tests for `AssetGroupParser` with sample YAML
  - [ ] Unit tests for `AssetMatcher` scoring algorithm
  - [ ] Integration test: parse template → match assets → return ranked results
  - [ ] Test edge cases: empty tags, no matching assets, invalid categories
  - [ ] Manual test: Verify asset groups display in template preview
  - [ ] Manual test: Preview matches shows actual indexed assets

## Dev Notes

### Architecture Context

This story **enables AI asset matching** by defining what assets are needed for each template moment. Story 3.4 loaded templates; this story parses their asset group requirements and creates the matching engine for Epic 5.

**Key Architectural Requirements:**
- **Declarative Asset Needs**: Templates declare needed assets via tags, not hardcoded paths [Source: prd.md#FR12]
- **Tag-Based Matching**: AI searches indexed assets by tags, not names [Source: epics.md#Story 3.5]
- **Category Separation**: Music, SFX, VFX groups match only their respective asset categories
- **Scored Matching**: Multiple assets can match; return ranked by relevance [Source: prd.md#FR22-FR24]

**Data Flow:**
```
Template loaded (Story 3.4)
    ↓
AssetGroupParser extracts groups from template YAML
    ↓
Asset groups cached with template
    ↓
Editor views template preview (AC #4)
    ↓
"Preview Matches" clicked
    ↓
AssetMatcher queries indexed media database
    ↓
Tag matching algorithm scores each asset
    ↓
Ranked results displayed: "epic_corporate_track.wav (95% match)"
    ↓
Epic 5: AI uses these patterns for rough cut generation
```

**Integration with Previous Stories:**
- **Story 3.4**: Uses `TemplateMarkdownParser` output containing raw asset group YAML
- **Story 3.4**: Enhances `FormatTemplate` dataclass with parsed `asset_groups: List[AssetGroup]`
- **Story 2.x**: Queries indexed media via existing database patterns (media_assets table)
- **Story 3.2**: Extends template preview UI to show asset groups
- **Epic 5**: AI rough cut generation uses `AssetMatcher` for contextual suggestions

### Project Structure Notes

**New Directories and Files:**
```
src/roughcut/backend/formats/
├── __init__.py
├── models.py                   # UPDATED: Add AssetGroup, AssetGroupCategory
├── parser.py                   # UPDATED: Add AssetGroupParser
├── matcher.py                  # NEW: AssetMatcher for tag-based matching
└── validator.py                # UPDATED: Add asset group validation

src/roughcut/backend/database/
├── queries.py                  # REFERENCE: Media asset queries from Story 2.x

src/roughcut/protocols/handlers/
├── formats.py                  # UPDATED: Add asset matching handlers
└── assets.py                   # REFERENCE: Existing asset query handlers

lua/
└── formats_manager.lua         # UPDATED: Add asset groups display
```

**Alignment with Existing Structure:**
- Extends `formats/models.py` with AssetGroup (follows existing dataclass patterns)
- Integrates with `database/queries.py` media asset queries (Story 2.x)
- Uses same protocol handler structure as Story 3.4
- UI enhancements follow Story 3.2 preview dialog patterns

### Technical Requirements

**AssetGroup Dataclass:**
```python
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Union

class AssetGroupCategory(Enum):
    """Category of assets for type-appropriate matching."""
    MUSIC = "music"
    SFX = "sfx"
    VFX = "vfx"
    TRANSITION = "transition"

class DurationHint:
    """Flexible duration specification for asset groups."""
    
    def __init__(self, 
                 exact: Optional[str] = None,
                 min_duration: Optional[str] = None,
                 max_duration: Optional[str] = None,
                 flexible: bool = True):
        self.exact = self._parse_duration(exact) if exact else None
        self.min = self._parse_duration(min_duration) if min_duration else None
        self.max = self._parse_duration(max_duration) if max_duration else None
        self.flexible = flexible
    
    @staticmethod
    def _parse_duration(dur: str) -> int:
        """Parse mm:ss or seconds to total seconds."""
        if ':' in dur:
            parts = dur.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        return int(dur)

@dataclass
class AssetGroup:
    """
    Defines a group of assets needed for a specific template moment.
    
    Example: intro_music needs upbeat corporate music for 15 seconds
    """
    name: str                          # Unique identifier: "intro_music"
    description: str                   # Human-readable: "Upbeat attention grabber"
    category: AssetGroupCategory       # MUSIC, SFX, VFX, TRANSITION
    
    # Tag matching criteria
    required_tags: List[str] = field(default_factory=list)   # Must have ALL
    optional_tags: List[str] = field(default_factory=list)   # Nice to have ANY
    
    # Duration constraints
    duration_hint: Optional[DurationHint] = None
    
    # Matching preferences
    priority: str = "medium"           # high, medium, low (matching priority)
    fallback_groups: List[str] = field(default_factory=list)  # If no matches
    
    def __post_init__(self):
        """Validate asset group on creation."""
        if not self.name or not self.name.strip():
            raise ValueError("Asset group name is required")
        
        if not self.description or not self.description.strip():
            raise ValueError("Asset group description is required")
        
        if not isinstance(self.category, AssetGroupCategory):
            raise ValueError(f"Invalid category: {self.category}")
        
        if not self.required_tags and not self.optional_tags:
            raise ValueError("At least one tag required (required or optional)")
        
        # Normalize tags to lowercase
        self.required_tags = [t.lower().strip() for t in self.required_tags]
        self.optional_tags = [t.lower().strip() for t in self.optional_tags]
    
    def matches_asset(self, asset_tags: List[str]) -> float:
        """
        Calculate match score for this group against asset tags.
        
        Returns:
            Score 0.0-1.0 where 1.0 = perfect match
        """
        asset_tags = set(t.lower() for t in asset_tags)
        
        # Required tags must all match (binary - fail if any missing)
        required_match = all(r in asset_tags for r in self.required_tags)
        if not required_match:
            return 0.0
        
        # Score based on optional tags
        if not self.optional_tags:
            return 1.0 if required_match else 0.0
        
        optional_matches = sum(1 for o in self.optional_tags if o in asset_tags)
        optional_score = optional_matches / len(self.optional_tags)
        
        # Weight: required = 70%, optional = 30%
        return 0.7 + (0.3 * optional_score)
    
    def to_dict(self) -> dict:
        """Serialize for protocol responses."""
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'required_tags': self.required_tags,
            'optional_tags': self.optional_tags,
            'duration_hint': {
                'exact': self.duration_hint.exact if self.duration_hint else None,
                'min': self.duration_hint.min if self.duration_hint else None,
                'max': self.duration_hint.max if self.duration_hint else None,
                'flexible': self.duration_hint.flexible if self.duration_hint else True
            },
            'priority': self.priority,
            'fallback_groups': self.fallback_groups
        }
```

**AssetGroupParser Class:**
```python
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

class AssetGroupParser:
    """Parses asset group definitions from template YAML."""
    
    REQUIRED_FIELDS = ['description', 'tags']
    
    def __init__(self):
        self.validator = AssetGroupValidator()
    
    def parse_yaml_block(self, yaml_content: str) -> List[AssetGroup]:
        """
        Parse asset groups from YAML code block content.
        
        Args:
            yaml_content: Raw YAML string from template markdown
            
        Returns:
            List of AssetGroup objects
            
        Raises:
            AssetGroupParseError: If YAML is invalid
        """
        try:
            data = yaml.safe_load(yaml_content)
            
            if not isinstance(data, dict):
                raise AssetGroupParseError("Asset groups must be a YAML dictionary")
            
            groups = []
            for group_name, group_def in data.items():
                try:
                    group = self._parse_single_group(group_name, group_def)
                    groups.append(group)
                except (ValueError, KeyError) as e:
                    # Log error but continue with other groups
                    logger.warning(f"Skipping invalid asset group '{group_name}': {e}")
                    continue
            
            return groups
            
        except yaml.YAMLError as e:
            raise AssetGroupParseError(f"Invalid YAML in asset groups: {e}")
    
    def _parse_single_group(self, name: str, definition: Dict[str, Any]) -> AssetGroup:
        """Parse a single asset group definition."""
        # Validate required fields present
        self.validator.validate_definition(name, definition)
        
        # Parse category
        category_str = definition.get('category', self._infer_category(name))
        category = AssetGroupCategory(category_str.lower())
        
        # Parse tags (can be string or list)
        tags = definition.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]
        
        # Split into required and optional
        required_tags = definition.get('required_tags', tags)
        optional_tags = definition.get('optional_tags', [])
        
        # Parse duration hint
        duration_hint = None
        if 'duration' in definition:
            duration_hint = self._parse_duration(definition['duration'])
        elif 'duration_hint' in definition:
            duration_hint = self._parse_duration(definition['duration_hint'])
        
        return AssetGroup(
            name=name,
            description=definition['description'],
            category=category,
            required_tags=required_tags,
            optional_tags=optional_tags,
            duration_hint=duration_hint,
            priority=definition.get('priority', 'medium'),
            fallback_groups=definition.get('fallback_groups', [])
        )
    
    def _infer_category(self, name: str) -> str:
        """Infer category from group name heuristics."""
        name_lower = name.lower()
        if 'music' in name_lower or 'track' in name_lower or 'bed' in name_lower:
            return 'music'
        elif 'sfx' in name_lower or 'sound' in name_lower or 'chime' in name_lower:
            return 'sfx'
        elif 'vfx' in name_lower or 'effect' in name_lower or 'lower_third' in name_lower:
            return 'vfx'
        elif 'transition' in name_lower or 'wipe' in name_lower:
            return 'transition'
        return 'music'  # Default
    
    def _parse_duration(self, duration_def: Union[str, Dict]) -> DurationHint:
        """Parse duration specification."""
        if isinstance(duration_def, str):
            # Single duration string: "0:15" or "15"
            return DurationHint(exact=duration_def)
        elif isinstance(duration_def, dict):
            # Dictionary with exact/min/max/flexible
            return DurationHint(
                exact=duration_def.get('exact'),
                min_duration=duration_def.get('min'),
                max_duration=duration_def.get('max'),
                flexible=duration_def.get('flexible', True)
            )
        else:
            raise AssetGroupParseError(f"Invalid duration format: {duration_def}")
```

**AssetMatcher Class:**
```python
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class MatchedAsset:
    """Result of matching an asset to an asset group."""
    asset_id: str
    file_path: str
    file_name: str
    tags: List[str]
    score: float                    # 0.0-1.0 match score
    category: str                   # music, sfx, vfx

class AssetMatcher:
    """
    Matches indexed media assets to template asset groups.
    
    Used by AI in Epic 5 for contextual asset suggestions.
    """
    
    def __init__(self, database_client):
        self.db = database_client
    
    def match_assets_for_group(
        self, 
        asset_group: AssetGroup,
        limit: int = 5,
        min_score: float = 0.5
    ) -> List[MatchedAsset]:
        """
        Find matching assets for an asset group.
        
        Args:
            asset_group: The asset group to match against
            limit: Maximum number of results to return
            min_score: Minimum match score to include (0.0-1.0)
            
        Returns:
            List of MatchedAsset objects, sorted by score descending
        """
        # Query database for assets in matching category
        category_filter = asset_group.category.value
        assets = self.db.get_assets_by_category(category_filter)
        
        # Score each asset
        scored_matches = []
        for asset in assets:
            score = asset_group.matches_asset(asset.get('ai_tags', []))
            if score >= min_score:
                scored_matches.append(MatchedAsset(
                    asset_id=asset.get('id'),
                    file_path=asset.get('file_path'),
                    file_name=asset.get('file_name'),
                    tags=asset.get('ai_tags', []),
                    score=score,
                    category=asset.get('category')
                ))
        
        # Sort by score descending and return top matches
        scored_matches.sort(key=lambda x: x.score, reverse=True)
        return scored_matches[:limit]
    
    def match_all_groups(
        self,
        asset_groups: List[AssetGroup],
        limit_per_group: int = 3
    ) -> Dict[str, List[MatchedAsset]]:
        """
        Match assets for multiple asset groups.
        
        Returns:
            Dictionary mapping group name to list of matched assets
        """
        results = {}
        for group in asset_groups:
            results[group.name] = self.match_assets_for_group(
                group, 
                limit=limit_per_group
            )
        return results
    
    def get_best_match(self, asset_group: AssetGroup) -> Optional[MatchedAsset]:
        """
        Get single best matching asset for a group.
        
        Returns:
            Best matched asset or None if no matches
        """
        matches = self.match_assets_for_group(asset_group, limit=1)
        return matches[0] if matches else None
```

**Protocol Handler - Asset Matching:**
```python
def handle_match_assets_for_group(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Match indexed assets to an asset group.
    
    Request format:
    {
        "method": "match_assets_for_group",
        "params": {
            "template_id": "youtube-interview",
            "group_name": "intro_music",
            "limit": 5,
            "min_score": 0.5
        },
        "id": "req_001"
    }
    
    Response format:
    {
        "result": {
            "group_name": "intro_music",
            "matches": [
                {
                    "asset_id": "asset_001",
                    "file_path": "/assets/music/corporate/bright_theme.wav",
                    "file_name": "bright_theme.wav",
                    "tags": ["corporate", "upbeat", "bright"],
                    "score": 0.95,
                    "category": "music"
                },
                ...
            ],
            "total_matches": 12,
            "returned": 5
        },
        "error": null,
        "id": "req_001"
    }
    """
    try:
        template_id = params.get('template_id')
        group_name = params.get('group_name')
        limit = params.get('limit', 5)
        min_score = params.get('min_score', 0.5)
        
        if not template_id or not group_name:
            return error_response(
                'INVALID_PARAMS',
                'template_id and group_name are required'
            )
        
        # Load template and find asset group
        cache = get_template_cache()
        template = cache.get(template_id)
        
        if not template:
            return error_response(
                'TEMPLATE_NOT_FOUND',
                f'Template {template_id} not found'
            )
        
        asset_group = next(
            (g for g in template.asset_groups if g.name == group_name),
            None
        )
        
        if not asset_group:
            return error_response(
                'GROUP_NOT_FOUND',
                f'Asset group {group_name} not found in template'
            )
        
        # Perform matching
        matcher = AssetMatcher(get_database_client())
        matches = matcher.match_assets_for_group(
            asset_group,
            limit=limit,
            min_score=min_score
        )
        
        return success_response({
            'group_name': group_name,
            'matches': [m.__dict__ for m in matches],
            'total_matches': len(matches),
            'returned': len(matches)
        })
        
    except Exception as e:
        return error_response('MATCHING_FAILED', str(e))


def handle_match_all_groups(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Match assets for all groups in a template.
    
    Request format:
    {
        "method": "match_all_groups",
        "params": {
            "template_id": "youtube-interview",
            "limit_per_group": 3
        }
    }
    """
    try:
        template_id = params.get('template_id')
        limit_per_group = params.get('limit_per_group', 3)
        
        cache = get_template_cache()
        template = cache.get(template_id)
        
        if not template:
            return error_response('TEMPLATE_NOT_FOUND', f'Template {template_id} not found')
        
        matcher = AssetMatcher(get_database_client())
        all_matches = matcher.match_all_groups(
            template.asset_groups,
            limit_per_group=limit_per_group
        )
        
        # Convert to serializable format
        result = {}
        for group_name, matches in all_matches.items():
            result[group_name] = [m.__dict__ for m in matches]
        
        return success_response({
            'template_id': template_id,
            'groups': result,
            'total_groups': len(result)
        })
        
    except Exception as e:
        return error_response('MATCHING_FAILED', str(e))
```

**Lua UI - Asset Groups Display:**
```lua
-- formats_manager.lua (enhancement)

function buildAssetGroupsSection(parent, templateId)
    """Build asset groups display section for template preview."""
    
    -- Query asset groups for this template
    local result = Protocol.request({
        method = "get_template_preview",
        params = { template_id = templateId }
    })
    
    if not result.result or not result.result.asset_groups then
        return nil  -- No asset groups defined
    end
    
    local groups = result.result.asset_groups
    
    -- Create section container
    local section = CreateGroupBox(parent, "Asset Groups")
    
    -- Group by category
    local byCategory = {
        music = {},
        sfx = {},
        vfx = {},
        transition = {}
    }
    
    for _, group in ipairs(groups) do
        local cat = group.category
        if byCategory[cat] then
            table.insert(byCategory[cat], group)
        end
    end
    
    -- Display each category
    for category, categoryGroups in pairs(byCategory) do
        if #categoryGroups > 0 then
            local catLabel = CreateLabel(section, string.upper(category))
            catLabel:SetStyleSheet("font-weight: bold; font-size: 14px;")
            
            for _, group in ipairs(categoryGroups) do
                local groupRow = CreateHorizontalLayout()
                
                -- Group info
                local nameLabel = CreateLabel(groupRow, group.name)
                nameLabel:SetStyleSheet("font-weight: bold;")
                
                local descLabel = CreateLabel(groupRow, group.description)
                descLabel:SetWordWrap(true)
                
                -- Tags display
                local tagsText = "Tags: " .. table.concat(group.required_tags, ", ")
                if #group.optional_tags > 0 then
                    tagsText = tagsText .. " (optional: " .. table.concat(group.optional_tags, ", ") .. ")"
                end
                local tagsLabel = CreateLabel(groupRow, tagsText)
                tagsLabel:SetStyleSheet("color: gray; font-size: 11px;")
                
                -- "Preview Matches" button
                local previewBtn = CreateButton(groupRow, "Preview Matches")
                previewBtn.clicked = function()
                    showAssetMatchesDialog(templateId, group.name)
                end
                
                section:AddLayout(groupRow)
            end
        end
    end
    
    return section
end

function showAssetMatchesDialog(templateId, groupName)
    """Show dialog with matching assets for a group."""
    
    local dlg = CreateDialog("Matching Assets - " .. groupName)
    dlg:SetMinimumSize(600, 400)
    
    -- Query matches
    local result = Protocol.request({
        method = "match_assets_for_group",
        params = {
            template_id = templateId,
            group_name = groupName,
            limit = 5
        }
    })
    
    if result.error then
        ShowErrorDialog("Failed to load matches: " .. result.error.message)
        return
    end
    
    local matches = result.result.matches
    
    if #matches == 0 then
        local msg = CreateLabel(dlg, "No matching assets found.\n\nConsider adding assets with these tags to your library.")
        msg:SetWordWrap(true)
    else
        -- Display matches in list
        local list = CreateListWidget(dlg)
        
        for i, match in ipairs(matches) do
            local item = CreateListItem()
            
            local scorePercent = math.floor(match.score * 100)
            local scoreColor = scorePercent >= 80 and "green" or (scorePercent >= 60 and "orange" or "red")
            
            item:SetText(string.format(
                "%d. %s\nScore: %d%% | Tags: %s",
                i,
                match.file_name,
                scorePercent,
                table.concat(match.tags, ", ")
            ))
            
            list:AddItem(item)
        end
    end
    
    dlg:Show()
end
```

**Enhanced FormatTemplate with Asset Groups:**
```python
# Add to formats/models.py

@dataclass
class FormatTemplate:
    """Enhanced with asset_groups from Story 3.5."""
    
    # ... existing fields from Story 3.2 ...
    
    # Story 3.5: Asset groups for AI matching
    asset_groups: List[AssetGroup] = field(default_factory=list)
    
    def get_asset_group(self, name: str) -> Optional[AssetGroup]:
        """Find asset group by name."""
        return next((g for g in self.asset_groups if g.name == name), None)
    
    def get_groups_by_category(self, category: AssetGroupCategory) -> List[AssetGroup]:
        """Get all asset groups of a specific category."""
        return [g for g in self.asset_groups if g.category == category]
    
    def validate_asset_groups(self) -> List[str]:
        """Validate all asset groups, return list of errors."""
        errors = []
        
        # Check for duplicate names
        names = [g.name for g in self.asset_groups]
        if len(names) != len(set(names)):
            errors.append("Duplicate asset group names detected")
        
        # Validate each group
        for group in self.asset_groups:
            try:
                # Re-validation triggers __post_init__
                AssetGroup(**group.__dict__)
            except ValueError as e:
                errors.append(f"Asset group '{group.name}': {e}")
        
        return errors
```

### Dependencies

**Python Libraries:**
- `pyyaml` - YAML parsing (standard, already used)
- Standard library: `dataclasses`, `enum`, `typing`, `logging`
- Existing: Database client from Story 2.x
- Existing: `FormatTemplate` from Story 3.2/3.4

**Lua Modules:**
- `protocol.lua` - Existing protocol communication
- `formats_manager.lua` - Enhanced with asset groups display

### Error Handling Strategy

Following patterns from Stories 3.1-3.4:

1. **Invalid Asset Group YAML:**
   - Return `INVALID_ASSET_GROUP` error code
   - Include specific validation failure (missing field, invalid category)
   - Skip invalid groups but load others

2. **No Matching Assets:**
   - Return empty list (not an error)
   - UI shows "No matches - consider expanding library"
   - Log info message for debugging

3. **Database Query Failure:**
   - Return `DATABASE_ERROR` error code
   - Include suggestion: "Check media indexing status"
   - Graceful degradation (return empty matches)

4. **Template Not Found:**
   - Return `TEMPLATE_NOT_FOUND` (reused from Story 3.4)
   - UI suggests reloading templates

### Previous Story Intelligence

**Lessons from Story 3.4 (Template Loading):**
- YAML parsing with `python-frontmatter` is reliable
- Thread-safe cache implementation pattern (from code review fixes)
- Structured error objects work well for Lua UI

**Lessons from Story 2.x (Media Indexing):**
- Asset database schema: `media_assets` table with `ai_tags` column
- Query patterns via database client
- Tag storage as list/array in database

**Patterns to Continue:**
- Dataclass-based models with `__post_init__` validation
- Protocol handler error response format
- Lua UI follows Resolve conventions
- Thread-safe operations with locks where needed

**Patterns to Extend:**
- Tag-based matching algorithm (new for this story)
- Scored/ranked result sets
- Category-specific asset filtering
- Fallback group chaining

**Integration Points:**
- Enhances `FormatTemplate` from Story 3.4 with `asset_groups` field
- Queries `media_assets` table from Story 2.x
- Used by Epic 5 AI processing for contextual suggestions
- Displays in template preview UI from Story 3.2

### Performance Considerations

- **Database Queries**: Cache asset lists per category to reduce repeated queries
- **Matching Algorithm**: O(N*M) where N=assets, M=groups; acceptable for typical libraries (<20k assets)
- **Pre-computation**: Could pre-compute match scores if asset libraries are static
- **Lazy Loading**: Only match when "Preview Matches" clicked, not on template load

**Optimization Strategies:**
- Index asset tags in database for faster filtering
- Cache match results for repeated queries
- Background pre-matching for active templates (optional)

### Security Considerations

- **Tag Injection**: Sanitize tag values (alphanumeric + underscore only)
- **Path Exposure**: Asset file paths returned in matches (intentional for Epic 6)
- **Database Access**: Use parameterized queries (follow Story 2.x patterns)

### References

- [Source: epics.md#Story 3.5] - Story requirements and acceptance criteria
- [Source: _bmad-output/implementation-artifacts/3-4-load-templates-from-markdown.md] - Template parsing patterns, FormatTemplate dataclass
- [Source: architecture.md#Naming Patterns] - Naming conventions (Python snake_case, dataclasses)
- [Source: architecture.md#Error Handling] - Structured error objects pattern
- [Source: prd.md#FR12] - Template asset groups functional requirement
- [Source: prd.md#FR22-FR24] - AI music/SFX/VFX matching requirements
- [Source: prd.md#NFR15] - Human-readable format template syntax

## Dev Agent Record

### Agent Model Used

(To be filled during implementation)

### Debug Log References

N/A - New story

### Completion Notes List

(To be filled during implementation)

### File List

**New Files to Create:**
- `src/roughcut/backend/formats/matcher.py` - AssetMatcher class
- `src/roughcut/backend/formats/validators.py` - AssetGroupValidator (enhancement)
- `tests/unit/backend/formats/test_asset_groups.py` - AssetGroup dataclass tests
- `tests/unit/backend/formats/test_matcher.py` - AssetMatcher tests
- `tests/fixtures/templates/with_asset_groups.md` - Test template with asset groups

**Files to Modify:**
- `src/roughcut/backend/formats/models.py` - Add AssetGroup, AssetGroupCategory, enhance FormatTemplate
- `src/roughcut/backend/formats/parser.py` - Add AssetGroupParser
- `src/roughcut/protocols/handlers/formats.py` - Add match_assets_for_group, match_all_groups handlers
- `lua/formats_manager.lua` - Add asset groups display and preview matches UI

**Integration with Epic 5:**
- `src/roughcut/backend/ai/prompt_engine.py` - Use AssetMatcher for contextual asset suggestions (future)

## Code Review

### Review Date
(To be filled after code review)

### Issues Found
(To be filled after code review)

## Story Completion Status

**Status:** backlog → ready-for-dev

**Completion Note:** Story context created - comprehensive developer guide ready for implementation.

**Key Implementation Points:**
1. AssetGroup dataclass defines needed assets via tags, not hardcoded paths
2. Tag-based matching algorithm scores assets 0.0-1.0 (required + optional tags)
3. Category separation ensures MUSIC groups only match music assets
4. AssetMatcher queries indexed media and returns ranked results
5. UI shows asset groups in template preview with "Preview Matches" feature
6. Epic 5 AI will use AssetMatcher for contextual suggestions

**Next Steps:**
1. Review story with dev agent
2. Run `dev-story` for implementation
3. Run `code-review` when complete
4. Proceed to Story 3.6: Parse Format Rules
