# Plotquake

Cinematic business history documentaries in US English. Charon narration is calibrated one semitone lower without changing timing. Episodes have roughly fifteen minutes or more of actual narration; the story determines their final length.

## Create an episode

Start the production in Codex or Antigravity. Research and write the story, select photographs and video excerpts, and generate illustrative images when useful. The agent directs the edit freely; no O Dinheiro Explica editorial contracts or repeated approval stages are required.

The source episode lives in `episodes/blackberry.json`. Its scenes contain narration, short contextual captions and media keys. `public/assets/media/catalog.json` connects those keys to the selected media and credits. Several assets may share a key to vary the edit. Generated historical reconstructions are identified on screen.

## Produce in the cloud

After saving the episode and media to GitHub, run the **Render Documentary - Plotquake** workflow with the episode path. A deliberate change under `render-trigger/` also starts this workflow. It synthesizes recoverable narration per scene, creates the score, calculates the timeline from the complete audio, renders 1920×1080 at 30 FPS, and uploads the package to the configured Plotquake Google Drive folder.

The delivery contains `documentary_final.mp4`, dedicated `thumbnail.jpg`, publication text and JSON, visual credits and a Drive receipt with links. Publication to YouTube remains manual. No YouTube upload is performed.

The existing GitHub secrets are `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, and `GOOGLE_DRIVE_FOLDER_ID`. Their values stay in GitHub. Completed voice scenes are cached so a retry can resume without regenerating everything.

## Edit locally

`npm run studio` opens the current prepared timeline. `OpeningPreview` is a short view of that same timeline; `Documentary` is the complete film. `src/episodes/renderEpisode.json` is prepared by the cloud worker from actual narration. The committed file is only an explicitly marked technical preview until production runs.

Clip trims, focus, zoom, fit, cuts/dissolves, footage sound, scene captions and occasional quote/chart overlays are supported. The production keeps only essential automatic protections against incomplete narration, missing media and incomplete delivery.
