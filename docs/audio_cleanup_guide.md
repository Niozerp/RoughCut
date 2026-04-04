# Audio Cleanup Guide for RoughCut

## Overview

This guide helps you improve transcription quality when RoughCut detects poor audio quality. Following these steps will help you get better results from Resolve's speech-to-text transcription, which in turn improves RoughCut's AI-powered rough cut generation.

## When to Use This Guide

You should follow this guide when RoughCut displays a **"Quality: Poor"** warning with recommendations like:
- "Audio cleanup recommended - 12 problem areas detected"
- "Low confidence (45%) - audio issues present"
- "Very incomplete (30%) - many inaudible sections"

## Quick Start

The general workflow is:
1. **Apply noise reduction** in DaVinci Resolve
2. **Render a clean version** of the audio/video
3. **Replace the original clip** in the Media Pool
4. **Re-transcribe** in Resolve
5. **Re-run RoughCut** with the cleaned clip

---

## Step-by-Step Instructions

### Step 1: Apply Resolve's Noise Reduction

DaVinci Resolve includes powerful audio cleanup tools in the **Fairlight** page.

1. **Select the clip** in the Edit page timeline
2. **Open the Fairlight page** (click "Fairlight" at bottom of Resolve)
3. **Select the audio track** containing your dialogue
4. **Open the Effects Library** (top-left panel)
5. **Expand "Noise Reduction"** in the Audio FX section
6. **Drag "Noise Reduction" effect** onto your audio clip

**Recommended Settings:**

| Scenario | Learning Time | Threshold | Mode |
|----------|--------------|-----------|------|
| HVAC/AC noise | 3-5 seconds | -50 dB | Manual |
| Computer fan noise | 3-5 seconds | -55 dB | Manual |
| Echo/reverb | 5-10 seconds | -40 dB | Manual |
| General background | 5 seconds | -45 dB | Auto |

**Learning the Noise Profile:**
- Click "Learn" button
- Play a section with only noise (no speech)
- Let it analyze for 3-5 seconds
- Click "Learn" again to stop
- Adjust threshold if needed (-40 to -60 dB typical)

### Step 2: Render a Clean Version

After applying noise reduction, export a clean version:

1. **Go to the Deliver page** (click "Deliver" at bottom)
2. **Choose "Custom Export"**
3. **Format settings:**
   - **Video:** Same as source (e.g., H.264, ProRes)
   - **Audio:** Linear PCM (WAV) - best for transcription
   - **Resolution:** Same as original
4. **Output file:** Use a descriptive name like `interview_CLEANED.mov`
5. **Click "Add to Render Queue"**
6. **Click "Render All"**

**Pro tip:** You can export audio-only (WAV) for faster processing if video quality isn't the issue:
- In Deliver page, uncheck "Export Video"
- Check "Export Audio" with WAV format

### Step 3: Replace Clip in Media Pool

1. **Right-click the original clip** in the Media Pool
2. **Select "Replace Media"**
3. **Navigate to your cleaned file** (interview_CLEANED.mov)
4. **Click "Open"**

Resolve will now use the cleaned version throughout your project.

### Step 4: Re-transcribe in Resolve

1. **Right-click the cleaned clip** in the Media Pool
2. **Select "Generate Subtitle from Audio"**
3. **Choose speech-to-text options:**
   - Language: Select your spoken language
   - Caption preset: Select appropriate format
   - Max characters per line: 32-40
   - Max lines: 1-2
4. **Click "Create"**

Resolve will now create a new transcription based on the cleaned audio.

**Wait time:** Typical transcription takes:
- 1-2 minutes for 5-minute clips
- 5-10 minutes for 30-minute clips
- 15-30 minutes for 60+ minute clips

### Step 5: Re-run RoughCut

1. **Open RoughCut** from Resolve Scripts menu
2. **Select your cleaned clip** in the Media Browser
3. **Retrieve transcription** - should now be higher quality
4. **Review quality** - should show "Quality: Good" or "Quality: Fair"
5. **Proceed to format selection** and continue workflow

---

## Common Audio Issues and Solutions

### HVAC/AC Background Noise

**Symptoms:** Constant hum, transcription shows many [inaudible] markers

**Solution:**
1. Use Noise Reduction in Fairlight
2. Learn noise profile from clip segment with only HVAC noise
3. Set threshold to -50 dB
4. Render and re-transcribe

### Echo/Reverb (Room Reflections)

**Symptoms:** Hollow sound, words blend together

**Solution:**
1. In Fairlight, use "De-reverb" or "Noise Reduction" with 5-10 second learning
2. Record in a smaller room or use sound blankets next time
3. Consider using a shotgun mic or lav mic closer to speaker

### Distant Microphone

**Symptoms:** Quiet dialogue, lots of [inaudible], low confidence scores

**Solution:**
1. Boost audio level in Fairlight (+6 to +12 dB)
2. Apply Noise Reduction
3. Use Compressor to even out levels
4. Render and re-transcribe

### Crosstalk (Multiple Speakers)

**Symptoms:** Transcription mixes up speakers, incorrect speaker labels

**Solution:**
1. In Fairlight, use EQ to reduce bass frequencies (under 100 Hz)
2. This can help separate voices by pitch range
3. Consider using Resolve Studio's speaker detection
4. Manually correct speaker labels in transcript if needed

### Clipping/Distortion

**Symptoms:** Words sound distorted, "robotic" or "crunchy"

**Note:** This is often unfixable in post. Prevention is key:
1. Record with proper levels (-12 to -6 dB peak)
2. Use limiter during recording
3. For mild clipping, try Fairlight's "De-clipper" (Studio only)

---

## Before and After Examples

### Example 1: Warehouse Interview

**Before cleanup:**
```
Speaker 1: Um, so, like... [inaudible]... the thing is... 
[garbled]... basically... [inaudible]... company pivot.
Quality: Poor ✗ | Confidence: 45% | Problems: 12
```

**After applying noise reduction (HVAC):**
```
Speaker 1: The thing is, our company pivot happened because
we saw the market shifting toward remote work solutions.
Quality: Good ✓ | Confidence: 94% | Problems: 0
```

### Example 2: Office Meeting

**Before cleanup:**
```
Speaker 1: [inaudible] the quarterly [inaudible]?
Speaker 2: [crosstalk] [inaudible] figures [inaudible].
Quality: Poor ✗ | Confidence: 38% | Problems: 8
```

**After applying de-reverb:**
```
Speaker 1: What were the quarterly results?
Speaker 2: Revenue figures exceeded our projections by 12%.
Quality: Fair ⚠ | Confidence: 82% | Problems: 2
```

---

## Troubleshooting

### Noise Reduction Isn't Working

**Check:**
- Did you click "Learn" in a section with only noise (no speech)?
- Is threshold set appropriately (-40 to -60 dB)?
- Is the noise constant (works best) or intermittent (harder)?

### Still Getting Poor Quality After Cleanup

**Try:**
1. Multiple passes of noise reduction (light effect twice)
2. Combining noise reduction with EQ (cut 200-400 Hz for "muddy" sound)
3. Manual transcript correction (last resort for critical content)
4. Re-recording if possible (for non-critical clips)

### Can't Find "Generate Subtitle from Audio"

**Requirements:**
- DaVinci Resolve 18 or later
- Resolve Studio for advanced speaker detection
- Active internet connection (for cloud transcription)
- Sufficient storage space for subtitle files

**Alternative:**
- Manual transcription using Text+ titles
- Third-party transcription services (upload cleaned audio)
- Whisper local transcription (advanced users)

---

## Prevention Tips

**For Next Time:**

1. **Record with good levels:** -12 to -6 dB peak, never hitting 0 dB
2. **Use a lav mic or shotgun mic** close to the speaker (within 2 feet)
3. **Choose quiet locations:** Avoid HVAC, traffic, appliances
4. **Use sound blankets or foam** to reduce room echo
5. **Monitor audio** during recording with headphones
6. **Record room tone** (30 seconds of silence) for better noise reduction

---

## Related Documentation

- [RoughCut User Guide](user_guide.md)
- [Troubleshooting](troubleshooting.md)
- [Media Browser Help](media_browser.md)

---

## Feedback

If you find audio scenarios not covered by this guide, please report them:
1. Note the specific audio problem
2. Describe what you tried
3. Share the quality metrics RoughCut displayed

This helps improve RoughCut's guidance for all users.

---

*Last updated: 2026-04-04*
*Applies to: RoughCut v1.0+*
