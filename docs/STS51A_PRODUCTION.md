# STS-51A — production record

The user selected this episode on October 17, 2026 and asked to continue on
October 21. The other three proposed subjects are saved in [IDEA_BANK.md](IDEA_BANK.md)
as reserves; this production does not start those films.

## Authored material

- Source episode: [sts51a.json](../episodes/sts51a.json), in US English, with
  Charon and the canonical minus-one-semitone calibration.
- Historical evidence: [research dossier](../episodes/sts51a-research.md).
- Archive research: [media catalogue](../episodes/sts51a-media-research.json),
  including exact source URLs, clip intervals, known duplicates and uncertainty.
- Original explanatory vectors: [graphics](../episodes/sts51a-graphics.json).
- Dedicated cover: `public/assets/images/sts51a-thumbnail.png`. Its authentic
  NASA photograph, compositing prompt and Anton Regular typography are recorded
  in [thumbnail prompts](../episodes/sts51a-thumbnail-prompts.json).

The selection of images and footage is authored for each passage. A different
crop or a different excerpt file does not erase the identity of its underlying
photograph or continuous take. Figures on the wrong orbit, the recovery payment,
the two capture methods and the 1990 relaunches retain their factual distinctions.

## Production mechanics

The new clean publication and end-credit behavior is explicit in this episode.
Its schema is described in [PUBLICATION_STANDARD.md](PUBLICATION_STANDARD.md).
The new narration style has its own cache fingerprint; episodes without that
field keep their prior fingerprints. The voice, model and pitch remain canonical.

Media preparation, speech synthesis, the continuous soundtrack and video render
run in GitHub Actions. Prepared media and valid speech can be recovered from
caches. Existing BlackBerry and ITT films are not reopened by this production.

The new work is isolated on `codex/sts51a-documentary`. Existing local changes to
AGENTS.md, CHANNEL_BIBLE.md, PRODUCTION_LESSONS.md and the channel banner were
present before this episode's production and are not included in its commit.

## Verification and delivery status — October 21, 2026

The authored script, graphic previews, dedicated cover and selected source-PDF
pages have been inspected. Code checks cover the new publication, timing,
credits, narration cache and archive preparation paths. These checks do not
constitute an audiovisual review.

No NASA production run or delivered final MP4 was found at resumption.

The completed source and montage were saved in commit `2c8d899` on
`codex/sts51a-documentary`. Cloud preparation was dispatched on October 21:
[run 39678557851](https://github.com/Lucascristao/Plotquake/actions/runs/39678557851).
This preparation-only execution measures the actual speech, prepares the selected
media and produces representative audiovisual samples. It does not deliver the
full film. Its result is still pending at dispatch.

Final runtime, effective credits, final-file inspection and a Drive delivery
receipt remain pending. The user publishes to YouTube manually.

For the final execution, this episode also requests a descriptive observation of
the actual completed MP4 through the existing Google production connection. The
report is supplementary: it uses the audio and sampled video, reports its exact
input/sampling scope, and does not issue an editorial score or approval. It is
not a claim of human listening or continuous full-frame-rate viewing. The report
is kept with internal documentation; failures must remain explicitly unavailable.
This does not modify or restart the preparation run already in progress.
