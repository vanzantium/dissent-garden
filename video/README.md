# Demo Video Source

The final Build Week explainer is reproducible from authentic local application
captures and synthetic Windows narration.

```powershell
.\scripts\synthesize_narration.ps1
python .\scripts\build_demo_video.py
```

Outputs:

- `video/dissent-garden-build-week.mp4` — 2:39, 1280×720 H.264/AAC upload master
- `video/dissent-garden-build-week.srt` — sidecar English captions

The MP4, work directory, and raw browser captures are intentionally ignored by
Git. The narration source and build scripts are committed. No music is used.
