//! SpacetimeDB module for RoughCut media asset storage.
//!
//! This module keeps the runtime surface intentionally small and compatible
//! with SpacetimeDB 2.x. RoughCut primarily relies on the `media_assets`
//! table plus a few reducers for writes.

use spacetimedb::{ReducerContext, Table, Timestamp};

#[spacetimedb::table(accessor = media_assets, public)]
pub struct MediaAsset {
    #[primary_key]
    pub asset_id: String,
    pub owner_identity: String,
    pub file_path: String,
    pub file_name: String,
    #[index(btree)]
    pub category: String,
    pub file_size: i64,
    pub file_hash: String,
    pub ai_tags: Vec<String>,
    pub modified_time: Timestamp,
    pub created_at: Timestamp,
    pub updated_at: Timestamp,
}

#[spacetimedb::table(accessor = asset_tags, public)]
pub struct AssetTag {
    #[primary_key]
    #[auto_inc]
    pub tag_id: u64,
    pub asset_id: String,
    pub tag_name: String,
    pub confidence: f32,
}

#[spacetimedb::table(accessor = user_settings)]
pub struct UserSettings {
    #[primary_key]
    pub identity: String,
    pub settings_json: String,
    pub updated_at: Timestamp,
}

fn caller_identity(ctx: &ReducerContext) -> String {
    format!("0x{}", ctx.sender().to_hex())
}

fn validate_category(category: &str) -> Result<(), String> {
    let valid_categories = ["music", "sfx", "vfx"];
    if valid_categories.contains(&category) {
        return Ok(());
    }

    Err(format!(
        "Invalid category '{}'. Must be one of: {:?}",
        category, valid_categories
    ))
}

fn validate_asset(asset: &MediaAsset) -> Result<(), String> {
    if asset.asset_id.trim().is_empty() {
        return Err("Asset ID cannot be empty".into());
    }
    if asset.file_path.trim().is_empty() {
        return Err("File path cannot be empty".into());
    }
    if asset.file_hash.trim().is_empty() {
        return Err("File hash cannot be empty".into());
    }
    if asset.file_size < 0 {
        return Err("File size cannot be negative".into());
    }

    validate_category(asset.category.as_str())
}

fn normalize_asset(ctx: &ReducerContext, mut asset: MediaAsset) -> Result<MediaAsset, String> {
    validate_asset(&asset)?;
    asset.owner_identity = caller_identity(ctx);
    asset.updated_at = ctx.timestamp;
    Ok(asset)
}

#[spacetimedb::reducer]
pub fn insert_asset(ctx: &ReducerContext, asset: MediaAsset) -> Result<(), String> {
    let asset = normalize_asset(ctx, asset)?;

    if let Some(existing) = ctx.db.media_assets().asset_id().find(&asset.asset_id) {
        let mut updated = asset;
        updated.created_at = existing.created_at;
        ctx.db.media_assets().asset_id().update(updated);
    } else {
        ctx.db.media_assets().insert(asset);
    }

    Ok(())
}

#[spacetimedb::reducer]
pub fn insert_assets_batch(ctx: &ReducerContext, assets: Vec<MediaAsset>) -> Result<(), String> {
    for asset in assets {
        insert_asset(ctx, asset)?;
    }

    Ok(())
}

#[spacetimedb::reducer]
pub fn update_asset(
    ctx: &ReducerContext,
    asset_id: String,
    updates: MediaAsset,
) -> Result<(), String> {
    let Some(existing) = ctx.db.media_assets().asset_id().find(&asset_id) else {
        return Err(format!("Asset not found: {}", asset_id));
    };

    let mut updated = normalize_asset(ctx, updates)?;
    updated.asset_id = asset_id;
    updated.created_at = existing.created_at;
    ctx.db.media_assets().asset_id().update(updated);
    Ok(())
}

#[spacetimedb::reducer]
pub fn delete_asset(ctx: &ReducerContext, asset_id: String) -> Result<(), String> {
    if ctx.db.media_assets().asset_id().find(&asset_id).is_none() {
        return Err(format!("Asset not found: {}", asset_id));
    }

    ctx.db.media_assets().asset_id().delete(&asset_id);
    Ok(())
}

#[spacetimedb::reducer]
pub fn delete_assets_batch(ctx: &ReducerContext, asset_ids: Vec<String>) -> Result<(), String> {
    for asset_id in asset_ids {
        if ctx.db.media_assets().asset_id().find(&asset_id).is_some() {
            ctx.db.media_assets().asset_id().delete(&asset_id);
        }
    }

    Ok(())
}

#[spacetimedb::reducer]
pub fn store_settings(ctx: &ReducerContext, settings_json: String) -> Result<(), String> {
    if settings_json.trim().is_empty() {
        return Err("Settings JSON cannot be empty".into());
    }

    let settings = UserSettings {
        identity: caller_identity(ctx),
        settings_json,
        updated_at: ctx.timestamp,
    };

    if ctx.db.user_settings().identity().find(&settings.identity).is_some() {
        ctx.db.user_settings().identity().update(settings);
    } else {
        ctx.db.user_settings().insert(settings);
    }

    Ok(())
}
