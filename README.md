# Plotquake ⚡

> **High-retention business, tech and historical documentaries in Remotion + AI.**  
> *"Stories with plot twists that shake empires."*

Plotquake is an automated production engine designed for high-CPM dark YouTube channels targeting global Tier-1 audiences (US, UK, Canada, Australia).

---

## 🎬 Core Architecture

- **Visual Engine**: Remotion (React + TypeScript) in **Full HD 1920x1080 (30 FPS)**.
- **Storytelling Structure**: Documentaries divided into **4 Dramatic Acts** (Conflict -> Rise -> Peak Battle -> Collapse).
- **Documentary Components**:
  - `KenBurnsImage`: Smooth cinematic zoom, pan, film grain, and documentary lower-thirds.
  - `NewspaperPop`: Vintage aged newspaper with dynamic headlines and yellow marker highlights.
  - `MarketChart`: Animated market share comparison bars.
  - `QuoteCard`: Elegant glassmorphic quote cards with source and year badges.
  - `ActMarker`: Seismic title card marking chapters and acts.
- **Cloud Cloud Rendering**: GitHub Actions (`.github/workflows/render-documentary.yml`) renders in the cloud without using your local PC.
- **Automated Delivery**: Uploads finished MP4, 1280x720 thumbnail, and YouTube packaging metadata directly to **Google Drive**.

---

## 🚀 Quick Start (Local Preview)

Open the interactive Remotion Studio player:

```bash
npm run studio
```

Render locally (Act 1 preview):

```bash
npx remotion render src/index.ts Act1 renders/act1.mp4
```

---

## ☁️ Cloud Production (GitHub Actions)

1. Set your repository secrets in GitHub:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REFRESH_TOKEN`
   - `GOOGLE_DRIVE_FOLDER_ID`
   - `GEMINI_API_KEY`
2. Go to **Actions** -> **Render Documentary - Plotquake**.
3. Select `Documentary` or `Act1` and click **Run workflow**.
4. The output will be delivered directly to your Google Drive folder!
