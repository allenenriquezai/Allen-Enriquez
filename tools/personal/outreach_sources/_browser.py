"""
Shared Playwright browser context manager.

Persists login state per platform under ~/.cache/enriquez-outreach/<platform>-state.json.
Allen logs in once interactively; subsequent runs reuse the session.

Usage:
    from outreach_sources._browser import platform_browser

    with platform_browser('ig') as page:
        page.goto('https://instagram.com/explore/tags/businesscoach/')
        ...

    # First run interactively to capture login:
    python3 tools/personal/outreach_sources/_browser.py login --platform ig
"""

import argparse
import sys
import time
from contextlib import contextmanager
from pathlib import Path

STATE_DIR = Path.home() / '.cache' / 'enriquez-outreach'
STATE_DIR.mkdir(parents=True, exist_ok=True)

PLATFORM_CONFIG = {
    'ig': {
        'login_url': 'https://www.instagram.com/accounts/login/',
        'logged_in_marker': 'https://www.instagram.com/',
        'state_file': 'ig-state.json',
    },
    'linkedin': {
        'login_url': 'https://www.linkedin.com/login',
        'logged_in_marker': 'https://www.linkedin.com/feed',
        'state_file': 'linkedin-state.json',
    },
    'skool': {
        'login_url': 'https://www.skool.com/login',
        'logged_in_marker': 'https://www.skool.com/',
        'state_file': 'skool-state.json',
    },
}


def state_path(platform):
    return STATE_DIR / PLATFORM_CONFIG[platform]['state_file']


@contextmanager
def platform_browser(platform, headless=True, slow_mo=0):
    """Yield a Playwright Page with the platform's logged-in session loaded."""
    from playwright.sync_api import sync_playwright

    cfg = PLATFORM_CONFIG[platform]
    storage_state = state_path(platform)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo)
        kwargs = {
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'viewport': {'width': 1280, 'height': 900},
        }
        if storage_state.exists():
            kwargs['storage_state'] = str(storage_state)
        context = browser.new_context(**kwargs)
        page = context.new_page()
        try:
            yield page
        finally:
            try:
                context.storage_state(path=str(storage_state))
            except Exception:
                pass
            context.close()
            browser.close()


def interactive_login(platform):
    """Open a visible browser, navigate to login, wait for Allen to log in,
    then save storage state."""
    from playwright.sync_api import sync_playwright

    cfg = PLATFORM_CONFIG[platform]
    storage_state = state_path(platform)

    print(f"[login {platform}] opening browser. Log in, then press Enter here.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = context.new_page()
        page.goto(cfg['login_url'])
        input(f"  -> Once you've logged in fully (and see {cfg['logged_in_marker']}), press Enter to save session...")
        context.storage_state(path=str(storage_state))
        print(f"[login {platform}] session saved to {storage_state}")
        browser.close()


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    li = sub.add_parser('login')
    li.add_argument('--platform', required=True, choices=['ig', 'linkedin', 'skool'])
    args = p.parse_args()

    if args.cmd == 'login':
        interactive_login(args.platform)


if __name__ == '__main__':
    main()
