"""Playwright session for etsy.com.

Etsy is protected by DataDome. Automated browsers usually get a CAPTCHA, which this
tool never tries to solve. Instead it runs a visible Chrome window with a persistent
profile: when a check appears, the user solves it in that window, the tool waits, and
the cookie stays in the profile for later runs.
"""

from __future__ import annotations

import os
import random
import time
from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, sync_playwright

DEFAULT_PROFILE = Path(".browser-profile")
BLOCK_MARKERS = ("captcha-delivery.com", "geo.captcha-delivery", "DataDome")


class BlockedError(RuntimeError):
    """Etsy showed a bot check that was not cleared."""


def is_blocked(html: str) -> bool:
    head = html[:5000]
    return any(marker in head for marker in BLOCK_MARKERS)


class EtsyBrowser:
    def __init__(
        self,
        headless: bool | None = None,
        profile_dir: Path = DEFAULT_PROFILE,
        channel: str | None = None,
        human_check_timeout: float = 300,
        delay_range: tuple[float, float] = (1.5, 4.0),
        on_status: Callable[[str], None] = print,
    ):
        if headless is None:
            headless = os.getenv("HEADLESS", "false").lower() in ("1", "true", "yes")
        self.headless = headless
        self.profile_dir = profile_dir
        self.channel = channel or os.getenv("BROWSER_CHANNEL", "chrome") or None
        self.human_check_timeout = human_check_timeout
        self.delay_range = delay_range
        self.on_status = on_status
        self._pw = None
        self._ctx: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self) -> EtsyBrowser:
        self._pw = sync_playwright().start()
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._ctx = self._pw.chromium.launch_persistent_context(
            str(self.profile_dir),
            channel=self.channel,
            headless=self.headless,
            locale="en-US",
            viewport={"width": 1366, "height": 900},
        )
        self._page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        return self

    def __exit__(self, *exc) -> None:
        if self._ctx:
            self._ctx.close()
        if self._pw:
            self._pw.stop()

    def get_html(self, url: str) -> str:
        """Load `url` and return its HTML, waiting for the user if a bot check appears."""
        assert self._page is not None, "use EtsyBrowser as a context manager"
        time.sleep(random.uniform(*self.delay_range))
        self._page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        self._page.wait_for_timeout(1500)
        html = self._page.content()
        if is_blocked(html):
            html = self._wait_for_human_check(url)
        # Let lazy content (prices, badges) settle a little.
        self._page.mouse.wheel(0, 1500)
        self._page.wait_for_timeout(800)
        return self._page.content()

    def _wait_for_human_check(self, url: str) -> str:
        assert self._page is not None
        if self.headless:
            raise BlockedError(
                "Etsy showed a bot check. Rerun with --headful (or HEADLESS=false), "
                "solve it in the browser window, and the session will be remembered."
            )
        self.on_status(
            "Etsy is showing a verification check. Please solve it in the Chrome window; "
            f"waiting up to {int(self.human_check_timeout)}s..."
        )
        deadline = time.monotonic() + self.human_check_timeout
        while time.monotonic() < deadline:
            self._page.wait_for_timeout(2000)
            try:
                html = self._page.content()
            except Exception:  # page is mid-navigation after the check clears
                continue
            if not is_blocked(html):
                self.on_status("Check cleared, continuing.")
                return html
        raise BlockedError(f"Bot check was not cleared within the timeout for {url}")
