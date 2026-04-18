"""
One-time: create a 'PH FB Groups' sheet inside Drive folder
  1. Personal Brand > Prospects
and populate with curated FB group list for PH outreach.

Group categorized by: target type (prospect pool / hybrid / audience-only),
segment (recruitment / real_estate / VA / SME / job-seekers), and priority.
"""

import pickle
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent
TOKEN_FILE = BASE_DIR / 'projects' / 'personal' / 'token_personal.pickle'

PROSPECTS_FOLDER_ID = '1cJvLBKnSwO_zfoZhE9m_aEs70XTn1Hx2'

HEADERS = [
    'Priority', 'Group Name', 'URL', 'Segment', 'Target Type',
    'Joined', 'Join Date', 'Notes',
]

GROUPS = [
    # Real estate broker professional groups (HIGH PRIORITY — prospect pool of brokerage owners)
    ['1', 'PRC Real Estate Brokers Network Philippines',
     'https://www.facebook.com/groups/reinvestmentsphbrokers/',
     'real_estate', 'Prospect pool', '', '', 'Licensed brokers only. High-signal group.'],
    ['1', 'Philippine Licensed Real Estate Brokers Listing',
     'https://www.facebook.com/groups/balgos.barretto.realty/',
     'real_estate', 'Prospect pool', '', '', 'Licensed brokers. Direct prospects.'],
    ['1', 'REBAP National (Page, follow)',
     'https://www.facebook.com/rebapnational/',
     'real_estate', 'Prospect pool', '', '', 'Follow page + members are your targets. 49 chapters nationwide.'],
    ['2', 'REBAP Global City',
     'https://www.facebook.com/RebapGlobalCity/',
     'real_estate', 'Prospect pool', '', '', 'Young/dynamic brokers. Tech-leaning.'],
    ['2', 'REBAP LMP (Las Pinas/Muntinlupa/Paranaque)',
     'https://www.facebook.com/rebaplmp/',
     'real_estate', 'Prospect pool', '', '', 'Chapter page. Active brokerage community.'],
    ['2', 'REBAP Makati',
     'https://rebapmakati.com/',
     'real_estate', 'Prospect pool', '', '', 'Makati chapter. High-revenue brokerages.'],
    ['2', 'REBAP Rizal',
     'https://www.facebook.com/REBAPRizal',
     'real_estate', 'Prospect pool', '', '', 'Rizal chapter.'],
    ['2', 'REBAP Pampanga',
     'https://www.facebook.com/rebappampangaph/',
     'real_estate', 'Prospect pool', '', '', 'Pampanga chapter.'],

    # Recruitment / IT recruitment (HIGH — agency owners post here)
    ['1', 'IT Recruitment Hub PH',
     'https://www.facebook.com/groups/ithubph/',
     'recruitment', 'Prospect pool', '', '', 'IT recruiters/agency owners. High-intent.'],
    ['1', 'IT Recruitment Philippines',
     'https://www.facebook.com/groups/ITRecruitmentPhilippines/',
     'recruitment', 'Prospect pool', '', '', 'IT-focused recruitment agencies.'],
    ['2', 'METRO MANILA - Job Hiring Legit 2025-2026',
     'https://www.facebook.com/groups/623377844807250/',
     'recruitment', 'Hybrid', '', '', 'Mixed: agency recruiters + job seekers. Filter by company posts.'],
    ['2', 'JOB HIRING AND RECRUITMENT IN THE PHILIPPINES',
     'https://www.facebook.com/groups/382086262402663/',
     'recruitment', 'Hybrid', '', '', 'Active recruiters + seekers.'],
    ['2', 'OFFICE STAFF JOB HIRING PHILIPPINES (OFFICIAL)',
     'https://www.facebook.com/groups/officestaffjobhiringph/',
     'recruitment', 'Hybrid', '', '', 'Employers post. Recruiters monitor.'],
    ['3', 'PHILIPPINES JOB HIRING',
     'https://www.facebook.com/groups/PHILIPPINESJOBHIRING/',
     'recruitment', 'Audience-only', '', '', 'Mostly job seekers. Low-buyer intent. Skip unless time.'],
    ['3', 'Job Seekers Philippines',
     'https://www.facebook.com/groups/jobseekersph/',
     'recruitment', 'Audience-only', '', '', 'Job seekers = audience, not customers.'],
    ['3', 'Trabaho - Philippines Job Posting',
     'https://www.facebook.com/groups/ph.trabaho/',
     'recruitment', 'Audience-only', '', '', 'Job seekers.'],
    ['3', 'Looking For Jobs (Philippines)',
     'https://www.facebook.com/groups/LookingForJobsPhilippines/',
     'recruitment', 'Audience-only', '', '', 'Job seekers.'],

    # VA agencies + VAs (hybrid — some agency owners, mostly VAs as audience)
    ['1', 'Virtual Assistant Network Philippines',
     'https://www.facebook.com/groups/vanetworkph/',
     'VA', 'Hybrid', '', '', 'Top VA network. Agency owners hire here. High volume.'],
    ['1', 'Philippine Virtual Assistant Network',
     'https://www.facebook.com/groups/PhilVANetwork/',
     'VA', 'Hybrid', '', '', 'Professional VA network. Mix of owners + VAs.'],
    ['2', 'Philippines Virtual Assistant Group (Job Hiring)',
     'https://www.facebook.com/groups/Philippinesvirtualassistantgroup/',
     'VA', 'Hybrid', '', '', 'Hiring-focused. Agency owners post here.'],
    ['2', 'Virtual Assistants - Philippines',
     'https://www.facebook.com/groups/virtualassistantsphilippines/',
     'VA', 'Hybrid', '', '', 'Large community. Active agency owners.'],
    ['2', 'HireTalent.ph',
     'https://www.facebook.com/groups/Philbestvirtualassistantsjob/',
     'VA', 'Hybrid', '', '', 'Hiring hub. Both sides active.'],
    ['3', 'Philippine Home-Based Virtual Assistants (Mentor Dolores)',
     'https://www.facebook.com/groups/phbva/',
     'VA', 'Audience-only', '', '', 'Mostly VAs. Audience not buyer.'],
    ['3', 'VIRTUAL ASSISTANT PHILIPPINES (WFH)',
     'https://www.facebook.com/groups/virtualassistantphilippinesofficial/',
     'VA', 'Audience-only', '', '', 'VAs. Audience only.'],
    ['3', 'Filipino Virtual Assistants - Verified Jobs',
     'https://www.facebook.com/groups/filipinofreelancersvirtualassistant/',
     'VA', 'Audience-only', '', '', 'VAs seeking work.'],
    ['3', 'Global Virtual Assistants (Surge Marketplace)',
     'https://www.facebook.com/groups/FILIPINOVIRTUALASSISTANCE/',
     'VA', 'Audience-only', '', '', 'VAs. Marketplace-driven.'],

    # SME / entrepreneur groups (potential customers beyond niche segments)
    ['2', 'Business Owners and Entrepreneurs in Philippines',
     'https://www.facebook.com/groups/Businessownersandentrepreneursinphilippines/',
     'SME', 'Prospect pool', '', '', 'Owner community. Post value content here.'],
    ['2', 'Philippines Small Business Owners Network',
     'https://www.facebook.com/groups/1036408529770532/',
     'SME', 'Prospect pool', '', '', 'Small biz owners. Phase 2 target.'],
    ['2', 'Philippine Business and Entrepreneurs Network',
     'https://www.facebook.com/groups/pbenforgrowth/',
     'SME', 'Prospect pool', '', '', 'Growth-oriented owners.'],
    ['2', 'Small Medium Enterprise (SME) Philippines',
     'https://www.facebook.com/groups/946150258834440/',
     'SME', 'Prospect pool', '', '', 'SMEs with budget.'],
    ['3', 'Entrepreneurs Philippines',
     'https://www.facebook.com/groups/1642978475936979/',
     'SME', 'Hybrid', '', '', 'Generic entrepreneur group. Mixed quality.'],
    ['3', 'Philippines Entrepreneurship - Startups, SME',
     'https://www.facebook.com/groups/philippinesentrepreneurship/',
     'SME', 'Hybrid', '', '', 'Startups + SMEs.'],
    ['3', 'Entrepreneur Philippines Forum',
     'https://www.facebook.com/groups/226101184085034/',
     'SME', 'Hybrid', '', '', 'Forum style.'],
    ['3', 'Entrepreneurs and Startups in the Philippines',
     'https://www.facebook.com/groups/entrepreneursandstartupsinthephilippines/',
     'SME', 'Hybrid', '', '', 'Community-driven.'],
]


def get_creds():
    with open(TOKEN_FILE, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def main():
    creds = get_creds()
    drive = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)

    body = {'properties': {'title': 'PH FB Groups'},
            'sheets': [{'properties': {'title': 'Groups', 'sheetId': 0}}]}
    created = sheets.spreadsheets().create(body=body, fields='spreadsheetId').execute()
    sid = created['spreadsheetId']
    print(f"Created spreadsheet: {sid}")

    drive.files().update(
        fileId=sid,
        addParents=PROSPECTS_FOLDER_ID,
        removeParents='root',
        fields='id,parents',
    ).execute()
    print(f"Moved to folder: 1. Personal Brand > Prospects")

    all_rows = [HEADERS] + GROUPS
    sheets.spreadsheets().values().update(
        spreadsheetId=sid,
        range='Groups!A1',
        valueInputOption='RAW',
        body={'values': all_rows},
    ).execute()

    requests = [
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 1.0},
            }},
            "fields": "userEnteredFormat(textFormat,backgroundColor)",
        }},
        {"updateSheetProperties": {
            "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        {"addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": 0, "startRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 1}],
                "booleanRule": {
                    "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "1"}]},
                    "format": {"backgroundColor": {"red": 0.85, "green": 1.0, "blue": 0.85}},
                },
            },
            "index": 0,
        }},
    ]
    sheets.spreadsheets().batchUpdate(spreadsheetId=sid, body={'requests': requests}).execute()

    print(f"\n=== DONE ===")
    print(f"URL: https://docs.google.com/spreadsheets/d/{sid}/edit")
    print(f"Rows written: {len(GROUPS)}")


if __name__ == '__main__':
    main()
