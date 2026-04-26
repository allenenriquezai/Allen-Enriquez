"""
Shared Playwright browser context manager — persistent Chrome profile per platform.

Each platform gets a dedicated user_data_dir under ~/.cache/enriquez-outreach/<platform>-profile/.
Allen logs in once via interactive_login(); the profile persists cookies, cache, and browser
fingerprint across runs — looks like the same device to IG/LinkedIn/Skool.

Usage:
    from outreach_sources._browser import platform_browser

    with platform_browser('ig') as page:
        page.goto('https://instagram.com/explore/tags/businesscoach/')

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
        'logged_in_marker': 'instagram.com',
        'logged_in_path_excludes': ('login', 'accounts/login', 'challenge'),
        'profile_dir': 'ig-profile',
    },
    'linkedin': {
        'login_url': 'https://www.linkedin.com/login',
        'logged_in_marker': 'linkedin.com/feed',
        'logged_in_path_excludes': ('login', 'checkpoint'),
        'profile_dir': 'linkedin-profile',
    },
    'skool': {
        'login_url': 'https://www.skool.com/login',
        'logged_in_marker': 'skool.com',
        'logged_in_path_excludes': ('login', 'signup'),
        'profile_dir': 'skool-profile',
    },
}


def profile_path(platform):
    return STATE_DIR / PLATFORM_CONFIG[platform]['profile_dir']


@contextmanager
def platform_browser(platform, headless=True, slow_mo=0):
    """Yield a Playwright Page with persistent Chrome profile loaded."""
    from playwright.sync_api import sync_playwright

    user_data_dir = profile_path(platform)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=headless,
            slow_mo=slow_mo,
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            yield page
        finally:
            context.close()


def _is_logged_in(url, cfg):
    if cfg['logged_in_marker'] not in url:
        return False
    return not any(x in url for x in cfg['logged_in_path_excludes'])


def interactive_login(platform, timeout_sec=600):
    """Open a visible browser with persistent profile, poll URL for logged-in marker.
    Profile auto-persists — no explicit save needed."""
    from playwright.sync_api import sync_playwright

    cfg = PLATFORM_CONFIG[platform]
    user_data_dir = profile_path(platform)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    print(f"[login {platform}] opening persistent profile at {user_data_dir}")
    print(f"[login {platform}] log in — script auto-detects success (timeout {timeout_sec}s)")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={'width': 1280, 'height': 900},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(cfg['login_url'])
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                if _is_logged_in(page.url, cfg):
                    time.sleep(3)  # let session cookies settle
                    print(f"[login {platform}] detected logged-in URL: {page.url}")
                    print(f"[login {platform}] profile saved to {user_data_dir}")
                    context.close()
                    return
            except Exception:
                pass
            time.sleep(2)
        print(f"[login {platform}] timeout after {timeout_sec}s — aborted", file=sys.stderr)
        context.close()


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    li = sub.add_parser('login')
    li.add_argument('--platform', required=True, choices=['ig', 'linkedin', 'skool'])
    li.add_argument('--timeout', type=int, default=600)
    args = p.parse_args()

    if args.cmd == 'login':
        interactive_login(args.platform, timeout_sec=args.timeout)


if __name__ == '__main__':
    main()
