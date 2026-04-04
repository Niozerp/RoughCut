# YouTube Interview Format Template

A format for interview-style YouTube content.

## Asset Groups

```yaml
intro_music:
    description: Upbeat attention-grabbing music for the intro
    tags: [corporate, upbeat, bright]
    duration: 0:15
    priority: high

narrative_bed:
    description: Subtle background music during narration
    tags: [subtle, background]
    required_tags: [background]
    optional_tags: [subtle, calm, corporate]
    category: music
    duration:
        min: 0:30
        max: 2:00
        flexible: true

outro_chime:
    description: Subtle sound to close the video
    tags: [chime, subtle]
    category: sfx
    duration: 0:03
    priority: medium
    fallback_groups: [intro_music]

transition_swoosh:
    description: Quick transition sound between segments
    tags: [whoosh, transition]
    category: sfx
    duration: 0:02
    priority: low
```

## Structure

1. Hook (0:00-0:10) - Grab attention
2. Intro (0:10-0:25) - Title card with music
3. Main Content (0:25-10:00) - Interview footage
4. Outro (10:00-10:15) - Call to action with chime
