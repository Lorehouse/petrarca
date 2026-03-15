#!/usr/bin/env python3
"""
Download Kindle book attachments from Gmail.

Searches for emails sent to brightkindle@kindle.com with file attachments
(EPUB, MOBI, AZW, PDF) and downloads them.

Usage:
  python3 gmail_kindle_attachments.py --list      # list matching emails
  python3 gmail_kindle_attachments.py --download   # download all attachments
  python3 gmail_kindle_attachments.py --upload     # download + upload to server

First run opens a browser for OAuth consent.
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CLIENT_SECRET = Path.home() / ".config/gws/client_secret.json"
TOKEN_PATH = Path.home() / ".config/gws/kindle_gmail_token.json"
DOWNLOAD_DIR = Path.home() / "src/petrarca/kindle-email-attachments"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
KINDLE_EMAIL = "brightkindle@kindle.com"

BOOK_EXTENSIONS = {".epub", ".mobi", ".azw", ".azw3", ".pdf", ".kfx", ".doc", ".docx"}


def get_gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET.exists():
                print(f"Error: OAuth client secret not found at {CLIENT_SECRET}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json())
        print(f"Token saved to {TOKEN_PATH}")

    return build("gmail", "v1", credentials=creds)


def search_kindle_emails(service):
    """Find all emails sent to the Kindle address with attachments."""
    query = f"to:{KINDLE_EMAIL} has:attachment"
    messages = []
    page_token = None

    while True:
        result = service.users().messages().list(
            userId="me", q=query, pageToken=page_token, maxResults=100
        ).execute()

        msgs = result.get("messages", [])
        messages.extend(msgs)
        print(f"  Found {len(messages)} messages so far...")

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return messages


def get_message_details(service, msg_id):
    """Get message subject, date, and attachment info."""
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()

    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    subject = headers.get("Subject", "(no subject)")
    date = headers.get("Date", "")

    attachments = []
    parts = msg["payload"].get("parts", [])
    # Also check nested parts
    all_parts = list(parts)
    for part in parts:
        if "parts" in part:
            all_parts.extend(part["parts"])

    for part in all_parts:
        filename = part.get("filename", "")
        if not filename:
            continue
        ext = Path(filename).suffix.lower()
        if ext in BOOK_EXTENSIONS:
            attachments.append({
                "filename": filename,
                "size": int(part["body"].get("size", 0)),
                "attachment_id": part["body"].get("attachmentId", ""),
                "mime_type": part.get("mimeType", ""),
            })

    return {
        "id": msg_id,
        "subject": subject,
        "date": date,
        "attachments": attachments,
    }


def download_attachment(service, msg_id, attachment_id, filename, dest_dir):
    """Download a single attachment."""
    dest = dest_dir / filename

    # Skip if already downloaded
    if dest.exists():
        return False

    att = service.users().messages().attachments().get(
        userId="me", messageId=msg_id, id=attachment_id
    ).execute()

    data = base64.urlsafe_b64decode(att["data"])
    dest.write_bytes(data)
    return True


def main():
    parser = argparse.ArgumentParser(description="Download Kindle attachments from Gmail")
    parser.add_argument("--list", action="store_true", help="List matching emails")
    parser.add_argument("--download", action="store_true", help="Download attachments")
    parser.add_argument("--upload", action="store_true", help="Download + upload to server")
    args = parser.parse_args()

    if not args.list and not args.download and not args.upload:
        args.list = True

    service = get_gmail_service()
    print(f"Searching Gmail for emails to {KINDLE_EMAIL}...")
    messages = search_kindle_emails(service)
    print(f"Found {len(messages)} emails\n")

    all_attachments = []
    for i, msg in enumerate(messages):
        details = get_message_details(service, msg["id"])
        if details["attachments"]:
            for att in details["attachments"]:
                all_attachments.append({**att, "msg_id": msg["id"], "subject": details["subject"], "date": details["date"]})
                if args.list:
                    size_kb = att["size"] // 1024
                    print(f"  {details['date'][:16]:16s}  {size_kb:5d}KB  {att['filename'][:60]}")

    print(f"\nTotal: {len(all_attachments)} book attachments across {len(messages)} emails")

    if args.download or args.upload:
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        downloaded = 0
        skipped = 0

        for att in all_attachments:
            if download_attachment(service, att["msg_id"], att["attachment_id"], att["filename"], DOWNLOAD_DIR):
                downloaded += 1
                print(f"  Downloaded: {att['filename']}")
            else:
                skipped += 1

        print(f"\nDownloaded {downloaded}, skipped {skipped} (already exist)")
        print(f"Files in: {DOWNLOAD_DIR}")

    if args.upload:
        import subprocess
        print(f"\nUploading to server...")
        result = subprocess.run(
            ["rsync", "-av", f"{DOWNLOAD_DIR}/", "alif:/opt/petrarca/data/epubs/"],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"Upload error: {result.stderr}")


if __name__ == "__main__":
    main()
