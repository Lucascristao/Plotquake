import argparse
import os
import sys
import re
from datetime import datetime, timezone
from pathlib import Path
from drive import uploader_from_env

def safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._ -]+", "", value).strip()
    return value[:120] or "episode"

def main():
    parser = argparse.ArgumentParser(description="Upload documentary assets to Google Drive.")
    parser.add_argument("--video", required=True, help="Path to rendered MP4 video")
    parser.add_argument("--thumbnail", help="Path to thumbnail image")
    parser.add_argument("--metadata", help="Path to YouTube metadata package (txt/json)")
    parser.add_argument("--episode-name", default="Episode", help="Episode display name for subfolder")

    args = parser.parse_args()

    uploader = uploader_from_env()
    if uploader is None:
        print("ERROR: Google Drive credentials or GOOGLE_DRIVE_FOLDER_ID missing from environment.")
        sys.exit(1)

    clean_name = safe_name(args.episode_name)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    folder_name = f"{clean_name}_{stamp}"
    
    print(f"Creating episode folder in Google Drive: {folder_name}...")
    episode_folder_id = uploader.create_folder(folder_name)

    # 1. Upload video
    video_path = Path(args.video)
    if video_path.exists():
        print(f"Uploading video: {video_path.name} ({video_path.stat().st_size / (1024*1024):.1f} MB)...", flush=True)
        uploader.upload(video_path, name=video_path.name, folder_id=episode_folder_id)
        print("Video upload complete!")
    else:
        print(f"WARNING: Video file not found at {video_path}")

    # 2. Upload thumbnail
    if args.thumbnail and Path(args.thumbnail).exists():
        thumb_path = Path(args.thumbnail)
        print(f"Uploading thumbnail: {thumb_path.name}...", flush=True)
        uploader.upload(thumb_path, name=thumb_path.name, folder_id=episode_folder_id)
        print("Thumbnail upload complete!")

    # 3. Upload metadata
    if args.metadata and Path(args.metadata).exists():
        meta_path = Path(args.metadata)
        print(f"Uploading metadata: {meta_path.name}...", flush=True)
        uploader.upload(meta_path, name=meta_path.name, folder_id=episode_folder_id)
        print("Metadata upload complete!")

    print(f"\nSUCCESS! All assets uploaded to Google Drive in folder: {folder_name}")

if __name__ == "__main__":
    main()
