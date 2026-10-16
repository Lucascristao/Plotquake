# Plotquake

Cinematic business history documentaries in US English. Charon narration is calibrated one semitone lower without changing timing. Episodes have roughly fifteen minutes or more of actual narration; the story determines their final length.

## Create an episode

Start the production in Codex or Antigravity. Research and write the story, select photographs and video excerpts, and generate illustrative images when useful. The agent directs the edit freely; no O Dinheiro Explica editorial contracts or repeated approval stages are required.

Each source episode lives in `episodes/<episode>.json`; `episodes/blackberry.json` is the first example. Its scenes contain narration, short contextual captions and media keys. `public/assets/media/catalog.json` connects those keys to the selected media and credits. Several assets may share a key to vary the edit. Generated historical reconstructions are identified on screen.

## Produce in the cloud

After saving the episode and media to GitHub, run the **Render Documentary - Plotquake** workflow with the episode path. A deliberate change under `render-trigger/` also starts this workflow. It synthesizes recoverable narration per scene, creates the score, calculates the timeline from the complete audio, renders 1920×1080 at 30 FPS, and uploads the package to the configured Plotquake Google Drive folder.

Set `episode_title` to a recognizable episode name or video title when dispatching, such as `ITT — The Phone Company That Offered the CIA $1 Million`. The Actions list displays `Plotquake · <episode_title> · #<run number>`. If omitted, the episode path is displayed, so every future run still identifies its source. This label does not change the episode, cache, concurrency or delivery.

Explicitly choose the intended `episode_path` when starting a run; its default is `episodes/blackberry.json`, including the push trigger. Different episode paths can run in parallel on independent cloud runners. Runs for the same path are serialized, with automatic cancellation disabled. Starting another episode does not update the code, narration or edit of a run already in progress. A run started before this episode-specific grouping keeps its original concurrency group; do not start that same episode again while its older run is still active.

Future runs prepare the episode once, then split its full visual timeline into as many balanced chunks as needed. Up to four workers render those chunks concurrently. Five minutes is a target chunk size, not a limit on the story or its four narrative acts. Longer episodes get more chunks; their complete duration is preserved. Each worker processes a list, avoiding a separate GitHub matrix job for every chunk.

The complete audio mix is rendered continuously to temporary lossless WAV and encoded once into a real M4A container. Video chunks have no audio. Assembly copies the video streams and that single audio master, with exact frame coverage and duration checks. Completed chunks are cached with content hashes and can be recovered when rerunning failed jobs. Ordinary source changes do not start a render or interrupt an existing run; each run uses its original Git commit, with automatic cancellation disabled.

Elapsed time depends on the episode, runner availability, preparation and transfers; there is no fixed completion-time promise. Standard runner minutes are free for this public repository, while artifact/cache storage has allowances and voice synthesis has its own costs. Temporary artifacts are retained for one day; the finished package remains in Drive. GitHub's runner time and disk limits still apply to individual jobs, rather than imposing a maximum episode duration in the editor.

The delivery contains `documentary_final.mp4`, dedicated `thumbnail.jpg`, publication text and JSON, visual credits and a Drive receipt with links. Publication to YouTube remains manual. No YouTube upload is performed.

The existing GitHub secrets are `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, and `GOOGLE_DRIVE_FOLDER_ID`. Their values stay in GitHub. Completed voice scenes are cached under the selected episode ID, so a retry can resume without regenerating everything. When no episode-specific v3 cache exists, the workflow can import existing v2 narration; each scene is still checked against its script, voice and audio hash. Only the selected episode's directory is saved into the v3 cache and passed to rendering. Narration from other episodes does not change that episode's video-chunk fingerprint.

## Edit locally

`npm run studio` opens the current prepared timeline. `OpeningPreview` is a short view of that same timeline; `Documentary` is the complete film. `src/episodes/renderEpisode.json` is prepared by the cloud worker from actual narration. The committed file is only an explicitly marked technical preview until production runs.

Clip trims, focus, zoom, fit, cuts/dissolves, footage sound, scene captions and occasional quote/chart overlays are supported. The production keeps only essential automatic protections against incomplete narration, missing media and incomplete delivery.

## Optional newspaper and document overlays

Add `newspaper` to an individual source scene when it supports the narration. It is a timed layer above the existing shots, so it does not replace charts, quotes or footage. `atSeconds` is relative to the scene; defaults are zero and eight seconds for `durationSeconds`, limited to the scene's remaining duration. Choose the moment and reading time freely.

For an authentic clipping, use `mode: "clipping"` and a `mediaKey` pointing to its original image in the catalog. Record the publication, date, source URL and license there. `highlightBoxes` uses normalized coordinates over the complete, uncropped image:

```json
"newspaper": {
  "mode": "clipping",
  "mediaKey": "verified-clipping-in-your-catalog",
  "atSeconds": 12,
  "durationSeconds": 10,
  "highlightBoxes": [{"x": 0.1, "y": 0.2, "width": 0.65, "height": 0.08}]
}
```

For original editorial text, use `mode: "reconstruction"`, `headline`, optional `subheadline` and `highlightWords` (words or phrases). `source` and `sourceUrl` identify the research. Reconstructions always display **EDITORIAL RECONSTRUCTION**, without a fabricated newspaper masthead. Generated assets retain that label. Clipping sources and reconstruction credits flow into the Drive package automatically. These overlays are optional; no fixed cadence or additional approval stage is introduced.
