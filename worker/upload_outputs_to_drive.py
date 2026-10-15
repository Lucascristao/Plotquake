import argparse
import os
import sys
from pathlib import Path
from drive import DriveUploader

def main():
    parser = argparse.ArgumentParser(description="Upload documentary assets to Google Drive.")
    parser.add_argument("--folder-id", default=os.getenv("GOOGLE_DRIVE_FOLDER_ID"), help="Target Drive folder ID")
    parser.add_argument("--video", required=True, help="Path to rendered MP4 video")
    parser.add_argument("--thumbnail", help="Path to thumbnail image")
    parser.add_argument("--metadata", help="Path to YouTube metadata package (txt/json)")
    parser.add_argument("--episode-name", default="Episode", help="Episode display name for subfolder")

    args = parser.parse_args()

    if not args.folder_id:
        print("ERROR: GOOGLE_DRIVE_FOLDER_ID environment variable is missing.")
        sys.exit(1)

    uploader = DriveUploader(args.folder_id)

    # Create an episode subfolder in Google Drive
    print(f"Creating episode folder: {args.episode_name}...")
    episode_folder_id = uploader.create_folder(args.episode_name)

    # Upload video
    video_path = Path(args.video)
    if video_path.exists():
        print(f"Uploading video: {video_path.name} ({video_path.stat().st_size / (1024*1024):.1f} MB)...")
        uploader.upload_file(str(video_path), folder_id=episode_folder_id)
    else:
        print(f"WARNING: Video file not found at {video_path}")

    # Upload thumbnail
    if args.thumbnail and Path(args.thumbnail).exists():
        print(f"Uploading thumbnail: {Path(args.thumbnail).name}...")
        uploader.upload_file(args.thumbnail, folder_id=episode_folder_id)

    # Upload metadata
    if args.metadata and Path(args.metadata).exists():
        print(f"Uploading metadata: {Path(args.metadata).name}...")
        uploader.upload_file(args.metadata, folder_id=episode_folder_id)

    print("SUCCESS: All documentary package files uploaded to Google Drive!")

if __name__ == "__main__":
    main()
