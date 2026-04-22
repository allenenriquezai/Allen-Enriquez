"""One-time script: create the 3 intermediate Gmail folder labels.

Creates (if missing):
  1. Projects/Ongoing
  1. Projects/Completed
  1. Projects/Unknown

Gmail only renders intermediate path segments as clickable folders when those
labels exist as standalone labels. Without them, child labels like
"1. Projects/Ongoing/Deckers Cafe" display as "Ongoing/Deckers Cafe" under
"1. Projects" instead of nesting properly.
"""
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import config

FOLDERS = [
    "1. Projects/Ongoing",
    "1. Projects/Completed",
    "1. Projects/Unknown",
]


def main():
    creds = config.ryan_gmail_creds()
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    svc = build("gmail", "v1", credentials=creds, cache_discovery=False)

    existing = {l["name"] for l in svc.users().labels().list(userId="me").execute().get("labels", [])}

    for name in FOLDERS:
        if name in existing:
            print(f"Already exists: {name}")
        else:
            svc.users().labels().create(userId="me", body={
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }).execute()
            print(f"Created: {name}")


if __name__ == "__main__":
    main()
