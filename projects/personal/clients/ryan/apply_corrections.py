#!/usr/bin/env python3
"""
Apply Ryan's Apr 22 label correction feedback to his Gmail.
Run once: python3 projects/personal/clients/ryan/apply_corrections.py
"""
import pickle
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

TOKEN = 'projects/personal/clients/ryan/token_ryan.pickle'

with open(TOKEN, 'rb') as f:
    creds = pickle.load(f)
service = build('gmail', 'v1', credentials=creds)

# --- Build label map ---
labels_resp = service.users().labels().list(userId='me').execute()
label_by_name = {l['name']: l['id'] for l in labels_resp['labels']}
label_by_id = {l['id']: l['name'] for l in labels_resp['labels']}


def get_or_create(name):
    if name in label_by_name:
        return label_by_name[name]
    print(f"  [create] {name}")
    result = service.users().labels().create(userId='me', body={
        'name': name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show',
    }).execute()
    label_by_name[name] = result['id']
    label_by_id[result['id']] = name
    return result['id']


def move_by_label(from_names, to_name, also_remove=None):
    """Move all messages from source labels to target label."""
    to_id = get_or_create(to_name)
    total = 0
    for from_name in from_names:
        from_id = label_by_name.get(from_name)
        if not from_id:
            print(f"  [skip] label not found: {from_name}")
            continue
        count = 0
        page_token = None
        while True:
            resp = service.users().messages().list(
                userId='me', labelIds=[from_id], maxResults=500, pageToken=page_token
            ).execute()
            msgs = resp.get('messages', [])
            if not msgs:
                break
            remove_ids = [from_id] + ([label_by_name[l] for l in (also_remove or []) if l in label_by_name])
            for msg in msgs:
                service.users().messages().modify(
                    userId='me', id=msg['id'],
                    body={'addLabelIds': [to_id], 'removeLabelIds': remove_ids}
                ).execute()
                count += 1
            page_token = resp.get('nextPageToken')
            if not page_token:
                break
        print(f"  {count:3d} msgs: {from_name.split('/')[-1]!r} → {to_name.split('/')[-1]!r}")
        total += count
    return total


def move_by_query(query, to_name):
    """Move messages matching Gmail query to target label."""
    to_id = get_or_create(to_name)
    count = 0
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId='me', q=query, maxResults=500, pageToken=page_token
        ).execute()
        msgs = resp.get('messages', [])
        if not msgs:
            break
        for msg in msgs:
            service.users().messages().modify(
                userId='me', id=msg['id'],
                body={'addLabelIds': [to_id]}
            ).execute()
            count += 1
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    print(f"  {count:3d} msgs via query [{query}] → {to_name.split('/')[-1]!r}")
    return count


# ── CORRECTIONS ──────────────────────────────────────────────────────────────

print("\n=== 1. Project Building #1 → Team/Office ===")
move_by_label(
    ['1. Projects/B. Ongoing/Project building #1'],
    '2. Team/Office'
)

print("\n=== 2. 915 Goodman → Completed/Colony Parc II, Ventura CA ===")
move_by_label(
    ['1. Projects/D. Unknown/915 Goodman'],
    '1. Projects/C. Completed/Colony Parc II, Ventura CA'
)

print("\n=== 3. 2607 → Ongoing/Deckers Cafe ===")
move_by_label(
    ['1. Projects/D. Unknown/2607'],
    '1. Projects/B. Ongoing/Deckers Cafe'
)

print("\n=== 4. 8901 Melrose — compile variants ===")
move_by_label(
    ['1. Projects/D. Unknown/8901 Melrose T.I. - West Hollywood, CA'],
    '1. Projects/D. Unknown/8901 Melrose - West Hollywood, CA'
)

print("\n=== 5. Anaheim 2A/2B → Completed ===")
move_by_label(
    [
        '1. Projects/D. Unknown/Anaheim 2A / 2B',
        '1. Projects/D. Unknown/Anaheim Plaza 2A/2B',
    ],
    '1. Projects/C. Completed/Anaheim 2A-2B, Long Beach CA'
)

print("\n=== 6. Angel City FC TI → Ongoing ===")
move_by_label(
    ['1. Projects/D. Unknown/Angel City FC TI'],
    '1. Projects/B. Ongoing/Angel City FC, Santa Monica CA'
)

print("\n=== 7. Backsplash/Breakroom → Completed/IMI Critical Engineering ===")
move_by_label(
    [
        '1. Projects/D. Unknown/Backsplash Tile @ Break Room 132 - IMI Critical Engineering',
        '1. Projects/D. Unknown/Breakroom Backsplash - Lake Forest, CA',
    ],
    '1. Projects/C. Completed/IMI Critical Engineering, Lake Forest CA'
)

print("\n=== 8. Cafe Refresh → Ongoing/Deckers Cafe ===")
move_by_label(
    ['1. Projects/D. Unknown/Cafe Refresh - Goleta, CA'],
    '1. Projects/B. Ongoing/Deckers Cafe'
)

print("\n=== 9. Colony Parc II variants → Completed ===")
move_by_label(
    [
        '1. Projects/D. Unknown/Colony Parc II',
        '1. Projects/D. Unknown/CP II - Ventura',
        '1. Projects/D. Unknown/CP II - Phase 2',
        '1. Projects/D. Unknown/CP II - Unit B3',
        '1. Projects/D. Unknown/Ventura, CA - Backsplash Repair',
    ],
    '1. Projects/C. Completed/Colony Parc II, Ventura CA'
)

print("\n=== 10. IMI Critical + IMI Lake Forest → Completed ===")
move_by_label(
    [
        '1. Projects/D. Unknown/IMI Critical Engineering - Lake Forest, CA',
        '1. Projects/D. Unknown/IMI Lake Forest',
    ],
    '1. Projects/C. Completed/IMI Critical Engineering, Lake Forest CA'
)

print("\n=== 11. Intuit Dome → Ongoing/Lounge 1888 ===")
move_by_label(
    ['1. Projects/D. Unknown/Intuit Dome'],
    '1. Projects/B. Ongoing/Lounge 1888'
)

print("\n=== 12. Long Beach plaza + Long Beach CA → Ongoing/Poly Plaza ===")
move_by_label(
    [
        '1. Projects/D. Unknown/Long Beach plaza',
        '1. Projects/D. Unknown/Long Beach, CA',
    ],
    '1. Projects/B. Ongoing/Poly Plaza'
)

print("\n=== 13. Mahdavi TI → Completed ===")
move_by_label(
    ['1. Projects/D. Unknown/MAHDAVI TI'],
    '1. Projects/C. Completed/Mahdavi TI, Thousand Oaks CA'
)

print("\n=== 14. OMP variants → compile into OMP Gardena ===")
move_by_label(
    [
        '1. Projects/D. Unknown/OMP - 223rd St Carson',
        '1. Projects/D. Unknown/OMP 233rd St',
    ],
    '1. Projects/D. Unknown/OMP Gardena'
)

print("\n=== 15. Osteria variants → Ongoing/Osteria Mozza ===")
move_by_label(
    [
        '1. Projects/D. Unknown/Osteria LA',
        '1. Projects/D. Unknown/Osteria Mozza (Bar Countertop Replacement) - Los Angeles, CA',
        '1. Projects/D. Unknown/Osteria Mozza LA - Bar Countertop',
    ],
    '1. Projects/B. Ongoing/Osteria Mozza, Los Angeles CA'
)

print("\n=== 16. Pavilions #1911 — fix spelling duplicate ===")
move_by_label(
    ['1. Projects/D. Unknown/Pavillions #1911 - Newport Beach, CA'],
    '1. Projects/D. Unknown/Pavilions #1911 - Newport Beach, CA'
)

print("\n=== 17. Pura Vida Miami → Ongoing ===")
move_by_label(
    ['1. Projects/D. Unknown/Pura Vida Miami'],
    '1. Projects/B. Ongoing/Pura Vida Miami, Long Beach CA'
)

print("\n=== 18. Suite 200/210 TI — compile ===")
move_by_label(
    [
        '1. Projects/D. Unknown/Suite 210 T.I',
        '1. Projects/D. Unknown/Suite 210 TI',
    ],
    '1. Projects/D. Unknown/Suite 200 T.I (Musik Peeler) - Westlake Village, CA'
)

print("\n=== 19. The Bar Method → Completed ===")
move_by_label(
    [
        '1. Projects/D. Unknown/The Bar Method - Burbank, CA',
        '1. Projects/D. Unknown/The Bar Method - Glenoaks Plaza',
        '1. Projects/D. Unknown/The Bar Method, Geleonoaks Plaza - Burbank, CA',
    ],
    '1. Projects/C. Completed/The Bar Method, Burbank CA'
)

print("\n=== 20. Archive/Review — Admin Shop Drawing → Deckers Cafe ===")
move_by_query(
    'from:admin@sc-incorporated.com subject:"Shop Drawing" label:"5. Archive/Review"',
    '1. Projects/B. Ongoing/Deckers Cafe'
)

print("\n=== 21. Archive/Review — Fr-Prime → Team/Office ===")
move_by_query(
    'from:prime label:"5. Archive/Review"',
    '2. Team/Office'
)

print("\n=== 22. Archive/Review — Fr-Ramiro → Team/Office ===")
move_by_query(
    'from:ramiro label:"5. Archive/Review"',
    '2. Team/Office'
)

print("\n=== Done ===")
