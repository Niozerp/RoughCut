//! SpacetimeDB module for RoughCut media asset storage
//! 
//! This module defines the database schema for media assets with
//! row-level security enforced through identity-based access control.

use spacetimedb::{table, reducer, Identity, Timestamp, ReducerContext};
use hex;

/// Media asset table with row-level security
/// 
/// Each asset is owned by a specific identity and can only be
/// accessed by that identity (enforced by reducers).
#[table(name = media_assets, public = false)]
pub struct MediaAsset {
    /// Unique identifier for the asset
    #[primary_key]
    pub asset_id: String,
    
    /// Owner identity for row-level security (stored as hex string for compatibility)
    pub owner_identity: String,
    
    /// Absolute path to the media file
    pub file_path: String,
    
    /// Filename without path
    pub file_name: String,
    
    /// Asset category: "music", "sfx", or "vfx"
    pub category: String,
    
    /// File size in bytes
    pub file_size: i64,
    
    /// MD5 hash for change detection
    pub file_hash: String,
    
    /// AI-generated tags for the asset
    pub ai_tags: Vec<String>,
    
    /// Last file modification timestamp
    pub modified_time: Timestamp,
    
    /// When the asset was first indexed
    pub created_at: Timestamp,
    
    /// When the asset was last updated
    pub updated_at: Timestamp,
}

/// Asset tag table for many-to-many relationship
/// 
/// Allows efficient tag-based queries with confidence scores.
#[table(name = asset_tags, public = false)]
pub struct AssetTag {
    #[primary_key]
    pub tag_id: u64,
    
    /// Foreign key to media_assets
    pub asset_id: String,
    
    /// Tag name/value
    pub tag_name: String,
    
    /// AI confidence score (0.0 to 1.0)
    pub confidence: f32,
}

/// User settings table for per-user configuration
#[table(name = user_settings, public = false)]
pub struct UserSettings {
    #[primary_key]
    pub identity: String,
    
    /// JSON-encoded settings blob
    pub settings_json: String,
    
    /// Last updated timestamp
    pub updated_at: Timestamp,
}

/// Convert Identity to hex string for storage
fn identity_to_string(identity: &Identity) -> String {
    format!("0x{}", hex::encode(identity.to_bytes()))
}

/// Helper function to check if caller owns the asset
fn is_owner(caller: &Identity, owner_identity_str: &str) -> bool {
    let caller_str = identity_to_string(caller);
    caller_str == owner_identity_str
}

/// Insert a new media asset (RLS enforced)
/// 
/// Only allows insertion if the asset's owner_identity matches
/// the caller's identity.
#[reducer]
pub fn insert_asset(ctx: &ReducerContext, asset: MediaAsset) -> Result<(), String> {
    // Enforce row-level security: asset must be owned by caller
    if !is_owner(&ctx.sender, &asset.owner_identity) {
        return Err("Unauthorized: cannot insert asset for another user".to_string());
    }
    
    // Validate asset data
    if asset.asset_id.is_empty() {
        return Err("Asset ID cannot be empty".to_string());
    }
    if asset.file_path.is_empty() {
        return Err("File path cannot be empty".to_string());
    }
    if asset.file_size < 0 {
        return Err("File size cannot be negative".to_string());
    }
    if asset.file_hash.is_empty() {
        return Err("File hash cannot be empty".to_string());
    }
    
    // Validate category
    let valid_categories = ["music", "sfx", "vfx"];
    if !valid_categories.contains(&asset.category.as_str()) {
        return Err(format!(
            "Invalid category '{}'. Must be one of: {:?}",
            asset.category, valid_categories
        ));
    }
    
    // Insert into database
    ctx.db.media_assets().insert(asset);
    Ok(())
}

/// Query all assets for the current user (RLS enforced) with LIMIT support
/// 
/// Returns only assets owned by the calling identity, limited to specified count.
#[reducer]
pub fn query_user_assets(
    ctx: &ReducerContext,
    limit: u64
) -> Vec<MediaAsset> {
    let caller_identity = identity_to_string(&ctx.sender);
    let effective_limit = if limit == 0 || limit > 10000 {
        10000  // Cap at 10000 for safety
    } else {
        limit
    };
    
    ctx.db.media_assets()
        .iter()
        .filter(|asset| asset.owner_identity == caller_identity)
        .take(effective_limit as usize)
        .collect()
}

/// Query assets by category for the current user with LIMIT support
#[reducer]
pub fn query_assets_by_category(
    ctx: &ReducerContext,
    category: String,
    limit: u64
) -> Vec<MediaAsset> {
    let caller_identity = identity_to_string(&ctx.sender);
    let effective_limit = if limit == 0 || limit > 10000 {
        10000
    } else {
        limit
    };
    
    ctx.db.media_assets()
        .iter()
        .filter(|asset| {
            asset.owner_identity == caller_identity && asset.category == category
        })
        .take(effective_limit as usize)
        .collect()
}

/// Query assets by tag for the current user with LIMIT support
#[reducer]
pub fn query_assets_by_tag(
    ctx: &ReducerContext,
    tag: String,
    limit: u64
) -> Vec<MediaAsset> {
    let caller_identity = identity_to_string(&ctx.sender);
    let effective_limit = if limit == 0 || limit > 10000 {
        10000
    } else {
        limit
    };
    
    ctx.db.media_assets()
        .iter()
        .filter(|asset| {
            asset.owner_identity == caller_identity && asset.ai_tags.contains(&tag)
        })
        .take(effective_limit as usize)
        .collect()
}

/// Update an existing asset (RLS enforced)
/// 
/// Only the owner can update their assets.
#[reducer]
pub fn update_asset(
    ctx: &ReducerContext,
    asset_id: String,
    updates: MediaAsset
) -> Result<(), String> {
    let caller_identity = identity_to_string(&ctx.sender);
    
    // Verify ownership of existing asset
    if let Some(existing) = ctx.db.media_assets().asset_id().find(&asset_id) {
        if existing.owner_identity != caller_identity {
            return Err("Unauthorized: cannot update another user's asset".to_string());
        }
    } else {
        return Err(format!("Asset not found: {}", asset_id));
    }
    
    // Verify new owner matches (can't transfer ownership via update)
    if updates.owner_identity != caller_identity {
        return Err("Cannot change asset ownership".to_string());
    }
    
    // Validate updates
    if updates.file_size < 0 {
        return Err("File size cannot be negative".to_string());
    }
    
    let valid_categories = ["music", "sfx", "vfx"];
    if !valid_categories.contains(&updates.category.as_str()) {
        return Err(format!(
            "Invalid category '{}'. Must be one of: {:?}",
            updates.category, valid_categories
        ));
    }
    
    // Update with new timestamp
    let mut updated = updates;
    updated.updated_at = ctx.timestamp;
    
    ctx.db.media_assets().asset_id().update(updated);
    Ok(())
}

/// Delete an asset (RLS enforced)
/// 
/// Only the owner can delete their assets.
#[reducer]
pub fn delete_asset(
    ctx: &ReducerContext,
    asset_id: String
) -> Result<(), String> {
    let caller_identity = identity_to_string(&ctx.sender);
    
    // Verify ownership before deletion
    if let Some(asset) = ctx.db.media_assets().asset_id().find(&asset_id) {
        if asset.owner_identity != caller_identity {
            return Err("Unauthorized: cannot delete another user's asset".to_string());
        }
        
        // Delete associated tags first
        let tags_to_delete: Vec<u64> = ctx.db.asset_tags()
            .iter()
            .filter(|at| at.asset_id == asset_id)
            .map(|at| at.tag_id)
            .collect();
        
        for tag_id in tags_to_delete {
            ctx.db.asset_tags().tag_id().delete(&tag_id);
        }
        
        // Delete the asset
        ctx.db.media_assets().asset_id().delete(&asset_id);
        Ok(())
    } else {
        Err(format!("Asset not found: {}", asset_id))
    }
}

/// Delete multiple assets by ID (RLS enforced)
#[reducer]
pub fn delete_assets_batch(
    ctx: &ReducerContext,
    asset_ids: Vec<String>
) -> Result<u64, String> {
    let caller_identity = identity_to_string(&ctx.sender);
    let mut deleted_count = 0u64;
    let mut errors: Vec<String> = Vec::new();
    
    for asset_id in asset_ids {
        if let Some(asset) = ctx.db.media_assets().asset_id().find(&asset_id) {
            if asset.owner_identity == caller_identity {
                // Delete associated tags
                let tags_to_delete: Vec<u64> = ctx.db.asset_tags()
                    .iter()
                    .filter(|at| at.asset_id == asset_id)
                    .map(|at| at.tag_id)
                    .collect();
                
                for tag_id in tags_to_delete {
                    ctx.db.asset_tags().tag_id().delete(&tag_id);
                }
                
                // Delete asset
                ctx.db.media_assets().asset_id().delete(&asset_id);
                deleted_count += 1;
            } else {
                errors.push(format!("Unauthorized to delete asset {}", asset_id));
            }
        } else {
            errors.push(format!("Asset {} not found", asset_id));
        }
    }
    
    // Return errors but don't fail the whole batch
    if !errors.is_empty() && deleted_count == 0 {
        return Err(format!("Batch delete failed: {}", errors.join("; ")));
    }
    
    Ok(deleted_count)
}

/// Insert multiple assets in a batch (RLS enforced)
#[reducer]
pub fn insert_assets_batch(
    ctx: &ReducerContext,
    assets: Vec<MediaAsset>
) -> Result<u64, String> {
    let caller_identity = identity_to_string(&ctx.sender);
    let mut inserted_count = 0u64;
    let mut errors: Vec<String> = Vec::new();
    
    for asset in assets {
        // Verify ownership
        if asset.owner_identity != caller_identity {
            errors.push(format!(
                "Asset {}: unauthorized owner",
                asset.asset_id
            ));
            continue;
        }
        
        // Validate asset
        if asset.asset_id.is_empty() {
            errors.push("Asset with empty ID skipped".to_string());
            continue;
        }
        
        if asset.file_size < 0 {
            errors.push(format!(
                "Asset {}: negative file size",
                asset.asset_id
            ));
            continue;
        }
        
        ctx.db.media_assets().insert(asset);
        inserted_count += 1;
    }
    
    // Return errors for debugging but don't fail the whole batch
    if !errors.is_empty() {
        log::warn!("Batch insert had {} errors", errors.len());
    }
    
    Ok(inserted_count)
}

/// Get asset count by category for the current user
#[reducer]
pub fn get_asset_counts(ctx: &ReducerContext) -> [(String, u64); 3] {
    let caller_identity = identity_to_string(&ctx.sender);
    let mut music_count = 0u64;
    let mut sfx_count = 0u64;
    let mut vfx_count = 0u64;
    
    for asset in ctx.db.media_assets().iter() {
        if asset.owner_identity == caller_identity {
            match asset.category.as_str() {
                "music" => music_count += 1,
                "sfx" => sfx_count += 1,
                "vfx" => vfx_count += 1,
                _ => {}
            }
        }
    }
    
    [
        ("music".to_string(), music_count),
        ("sfx".to_string(), sfx_count),
        ("vfx".to_string(), vfx_count)
    ]
}

/// Store user settings (RLS enforced - users can only store their own)
#[reducer]
pub fn store_settings(
    ctx: &ReducerContext,
    settings_json: String
) -> Result<(), String> {
    let caller_identity = identity_to_string(&ctx.sender);
    
    // Validate JSON is not empty
    if settings_json.is_empty() {
        return Err("Settings JSON cannot be empty".to_string());
    }
    
    // Check if settings already exist for this user
    if ctx.db.user_settings().identity().find(&caller_identity).is_some() {
        // Update existing settings
        let settings = UserSettings {
            identity: caller_identity,
            settings_json,
            updated_at: ctx.timestamp,
        };
        ctx.db.user_settings().identity().update(settings);
    } else {
        // Insert new settings
        let settings = UserSettings {
            identity: caller_identity,
            settings_json,
            updated_at: ctx.timestamp,
        };
        ctx.db.user_settings().insert(settings);
    }
    
    Ok(())
}

/// Get user settings for the current user
#[reducer]
pub fn get_settings(ctx: &ReducerContext) -> Option<String> {
    let caller_identity = identity_to_string(&ctx.sender);
    
    ctx.db.user_settings()
        .identity()
        .find(&caller_identity)
        .map(|s| s.settings_json)
}
