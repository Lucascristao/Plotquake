# Publication and film credits for new episodes

The new behavior is explicit per episode. Existing episodes without these fields
keep the previous package and timeline. It does not reopen BlackBerry or ITT.

```json
{
  "publication": {
    "standard": "cinematic-v1",
    "description": "The complete authored public description, written in US English.",
    "hashtags": ["SpaceHistory", "NASA"]
  },
  "endCredits": {
    "enabled": true,
    "heading": "ARCHIVAL FILM AND PHOTOGRAPHY",
    "secondsPerCard": 9,
    "assets": [
      {
        "src": "assets/video/mission/selected-excerpt.mp4",
        "author": "NASA",
        "title": "The exact work title and item identifier from the source",
        "origin": "The verified source item URL",
        "license": "The rights statement verified for this particular work",
        "licenseUrl": "The applicable verified rights-policy URL",
        "changes": "The actual excerpt, trim, crop, color or other changes",
        "screenCredit": ["NASA", "The exact work title and item identifier"]
      },
      {
        "src": "assets/audio/episode-id-score-directed.wav",
        "author": "Plotquake",
        "title": "The episode's original score title",
        "license": "Original production music; no external samples",
        "changes": "Original composition and final documentary mix",
        "screenCredit": false
      }
    ]
  },
  "score": {
    "endCredits": {"profile": "personal_finance", "gain": 0.5, "pluck": 0.2}
  }
}
```

This is a schema example, not a rights determination or a source record for any
mission. Enter the actual verified item details. Names of institutions alone do
not establish rights. All NASA exceptions and third-party contributions still
need the normal authorial source check.

`publication.description` is the public text. The canonical authoring requirement
is 80–150 words, at most two relevant hashtags, no timestamps, bibliography,
licensing or production details. The builder preserves the author's prose,
limits the separately supplied hashtags to two and records the word count in the
internal document. It does not add an editorial approval or blocking word-count
test. Tags remain a distinct field.

`endCredits.assets` enriches existing catalog records. `author`, `title`, `origin`,
`sourceUrl`, `license`, `licenseVersion`, `licenseUrl`, `changes` and any other
supplied fields remain in the internal JSON. `screenCredit` can be a string or an
array of exact display lines; `false` records a work without adding a screen
attribution, appropriate when attribution is not required and the author chooses
to omit it. Without `screenCredit`, author plus work title are shown, falling
back to the catalog's credit text. Supply concrete authors and work identifiers;
the code does not invent them or declare them legally sufficient.

Only `src` values selected in the derived timeline's shots, document overlays,
music and effects become film records or end-credit entries. Unused catalog
items, research-only references and cover artwork do not become film credits.
Repeated identical display entries appear once. Each distinct work must remain
identifiable in the supplied lines even when the author groups material.

Cards contain up to three entries on pure black, white regular-weight text and
one-second fades. They last at least `secondsPerCard` and extend for longer text
at approximately 2.7 words per second plus transition time. The author must still
inspect the rendered cards for layout and reading comfort. Optional
`endCredits.fullCreditsUrl` adds a final card with a real, author-verified short
address; it is never generated or guessed and does not replace required direct
attribution.

The builder adds `endCredits.startFrame`, its cards and duration after the final
story frame. `metadata.narrationSeconds`, acts, source voice WAVs and the existing
minimum-spoken-time check remain intact. Credits never count as narration.
`metadata.storyDurationInFrames` and `metadata.endCreditsDurationInFrames` expose
the separate clocks. Applying the helper again is idempotent.

For the procedural score, scene-anchored segments still cover the story. The
explicit `score.endCredits` tail then covers the credit frames on the same
continuous 48 kHz sample clock, with smooth transitions and the final fade. Its
default gain is zero when no tail is authored. Pause detection stops at the
story end, so a credit tail is not amplified as a long speech pause. The directed
WAV and final master retain the full duration including credits. For an opted-in
episode with a procedural score, the builder anticipates the final
`assets/audio/<episode-id>-score-directed.wav` path when selecting its credit,
before audio generation; this prevents a new music attribution from extending
the film after the WAV was written.

Delivery files for `cinematic-v1`:

- `youtube_package.txt`: title, public description and separate tags, ready for
  the user's manual YouTube publication.
- `youtube_package.json`: only title, description and tags.
- `internal_documentation.txt` and `internal_documentation.json`: historical
  research separated from actual film media, usage locations, supplied rights
  information, cover credits and the derived credit cards.

The production record reflects the derived timeline and does not claim a full
watch/listen of the delivered MP4, verify an address, or grant rights. The final
audiovisual review and the actual source conditions remain authorial work.
