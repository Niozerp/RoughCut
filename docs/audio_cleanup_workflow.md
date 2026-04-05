# Audio Cleanup Workflow for Better Transcription

This guide walks you through cleaning up poor-quality audio in DaVinci Resolve using Fairlight noise reduction, so you can get better transcription results in RoughCut.

## When to Use This Guide

Use this workflow when RoughCut shows **"Transcription quality low - audio cleanup recommended"** after reviewing your transcript. Common scenarios include:

- HVAC noise in the background
- Echo or reverb in the recording space
- Distant microphone placement
- Outdoor/windy recording conditions
- Low-bitrate audio compression artifacts

## Overview

The goal is to apply noise reduction in Resolve's Fairlight page, render a cleaned version, and then retry transcription in RoughCut with significantly improved results.

---

## Step 1: Open Your Clip in the Edit Page

**Objective:** Locate and prepare the clip for processing.

1. Switch to the **Edit** page in DaVinci Resolve
2. Find your clip in either:
   - The **Timeline** (if already placed)
   - The **Media Pool** (source clip view)
3. Double-click the clip to open it in the timeline viewer

**Tip:** You can also drag the clip from the Media Pool directly to the timeline if it's not already there.

**Resolve Location:** Edit page → Timeline or Media Pool

---

## Step 2: Apply Fairlight Noise Reduction

**Objective:** Add Resolve's built-in noise reduction effect to your audio.

1. Open the **Effects Library** sidebar (usually on the top-left)
2. Navigate to **Fairlight FX** category
3. Find **Noise Reduction** in the list
4. Drag the Noise Reduction effect onto your audio clip

**Alternative Method:**
- Right-click the audio clip in the timeline
- Select **Fairlight FX** → **Noise Reduction**

**Resolve Location:** Effects Library sidebar → Fairlight FX → Noise Reduction

**Note:** Fairlight effects are different from Fusion effects. Make sure you're in the "Fairlight FX" category, not "Fusion" or "OpenFX".

---

## Step 3: Adjust Noise Reduction Settings

**Objective:** Configure optimal settings for speech clarity.

Once the Noise Reduction effect is applied, the settings panel appears:

| Setting | Recommended Value | Notes |
|---------|------------------|-------|
| **Mode** | Auto Speech Mode | Optimized for dialogue/interviews |
| **Reduction** | 6-12dB | Start conservative (6dB) |
| **Smoothing** | Medium | Balances clarity and artifacts |
| **Attack/Release** | Auto | Let Resolve handle dynamics |

### Recommended Starting Point:

```
Mode: Auto Speech Mode
Reduction: 6dB
Smoothing: Medium
Attack/Release: Auto
```

### Fine-Tuning Tips:

1. **Preview the audio** after applying settings (press Space to play)
2. If you still hear noise, increase Reduction to 9dB
3. If the voice sounds "underwater," decrease to 3-6dB
4. Maximum recommended: 12dB (higher values degrade speech quality)

**Warning:** Aggressive noise reduction can make audio sound unnatural. It's better to have some noise than distorted speech.

---

## Step 4: Render Clean Version

**Objective:** Create a new clip file with the cleaned audio.

You have two options for rendering:

### Option A: Render in Place (Recommended)

1. Right-click your clip in the **Edit page timeline**
2. Select **Render in Place**
3. Choose settings:
   - **Format:** Same as source (e.g., QuickTime, MXF)
   - **Codec:** Same as source or DNxHR/ProRes for quality
   - **Audio:** Include audio
4. Click **Start Render**

**Result:** A new clip automatically appears in your Media Pool with "_Rendered" suffix.

### Option B: Deliver Page Export

1. Switch to the **Deliver** page
2. Add your clip to the render queue
3. Choose export settings:
   - **Location:** Your preferred folder
   - **Filename:** Add "_cleaned" suffix (e.g., `interview_take1_cleaned.mov`)
4. Click **Add to Render Queue** then **Start Render**
5. After render completes, right-click in Media Pool and **Import Media**

**Naming Convention:**
Add one of these suffixes to help RoughCut identify cleaned versions:
- `_cleaned`
- `_NR` (noise reduced)
- `_processed`
- `_fixed`

---

## Step 5: Return to RoughCut

**Objective:** Select your cleaned clip and retry transcription.

1. Return to RoughCut (keep Resolve open)
2. Click the **"Retry with Cleaned Clip"** button in the error recovery dialog
3. Select your newly rendered clip from the Media Pool list
4. RoughCut will re-retrieve transcription from the cleaned audio
5. Review the new quality rating — it should now be "Good" or "Fair"

**Expected Result:**
- Before: "Um, so, like... [inaudible]... basically..."
- After: "The thing is... [clear speech]... basically stated..."

---

## Troubleshooting

### Problem: Noise reduction makes audio sound "underwater" or unnatural

**Solution:**
- Reduce the Reduction amount from 12dB to 6dB
- Try 3dB if still unnatural
- Apply more conservative settings — better to keep some noise than distort speech

### Problem: Still getting poor transcription after cleanup

**Solution:**
- Try a different take/version if available
- Check if the original recording had severe audio issues (may be unrecoverable)
- Consider professional audio restoration services for critical footage
- Re-record the content if possible

### Problem: Cannot find Fairlight FX in Effects Library

**Solution:**
1. Ensure you're in the **Edit page** (not Cut or Media pages)
2. Look under the **"Fairlight FX"** category specifically
3. If still missing, update Resolve to the latest version
4. Check that your Resolve installation includes Fairlight components

### Problem: Clip rendered but not appearing in Media Pool

**Solution:**
- **Render in Place** from the Edit page automatically adds to Media Pool
- **Deliver page** export requires manual import:
  1. Right-click in Media Pool
  2. Select **Import Media**
  3. Navigate to your rendered file
  4. Click **Open**

### Problem: Fairlight FX is grayed out or unavailable

**Solution:**
- Ensure your clip has an audio track (some proxy media is video-only)
- Check that Resolve has audio hardware enabled (Preferences → System → Video and Audio I/O)
- Restart Resolve and try again

---

## Best Practices

### General Guidelines

1. **Always work on a copy** — Never destructively edit your original footage
2. **Start conservative** — Begin with 6dB reduction and increase gradually
3. **Preview before committing** — Listen to the cleaned audio before rendering
4. **Document your settings** — Note what worked for future reference
5. **Compare takes** — If you have multiple takes, try a different take instead of heavy processing

### Workflow Tips

- **Batch processing:** If you have multiple clips with similar noise, apply settings to one, then copy/paste the effect to others
- **Save presets:** Once you find settings that work for your common recording environment, save as a preset for faster application
- **Track organization:** Consider placing cleaned clips on a dedicated timeline track for easy identification

### When to Give Up

Sometimes audio quality issues are unrecoverable:

- Severe clipping/distortion (audio "brick-walled")
- Extremely low recording levels (buried in noise floor)
- Damaged or corrupted source files
- Multiple overlapping noise sources with similar frequency ranges

In these cases, consider:
- Using a different take/version
- Professional audio restoration (Izotope RX, etc.)
- Re-recording the content if production allows

---

## Technical Details

### What Fairlight Noise Reduction Does

Resolve's Fairlight Noise Reduction uses adaptive spectral processing to:

1. Analyze the audio frequency spectrum
2. Identify consistent noise patterns (HVAC hum, electrical buzz, etc.)
3. Apply frequency-specific reduction while preserving speech frequencies
4. Smooth transitions to avoid artifacts

### Limitations

- Cannot recover clipped/distorted audio
- Cannot separate overlapping voices
- Cannot remove impulsive noise (clicks, pops) — use De-Clicker for those
- Processing adds slight latency during preview (not present in rendered output)

### Alternative Tools

If Fairlight's built-in noise reduction isn't sufficient:

- **Izotope RX** — Industry-standard audio restoration (paid)
- **Audacity** — Free noise reduction (export/import workflow)
- **Adobe Audition** — Professional audio editing (subscription)

These require exporting audio, processing externally, and re-importing to Resolve.

---

## Related RoughCut Features

This guide supports RoughCut's **Error Recovery Workflow** (Story 4.4):

- Triggered when transcription quality is Poor (<50% confidence)
- Provides path to recover from fixable audio issues
- Enables retry with cleaned audio without losing workflow context

For more information, see:
- Story 4.3: Review Transcription Quality
- Story 4.5: Validate Transcribable Media

---

**Version:** 1.0  
**Last Updated:** 2026-04-04  
**Applies to:** RoughCut v0.1+ with DaVinci Resolve 18+
