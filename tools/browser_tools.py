
from pathlib import Path
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "data" / "jarvis-browser-profile"

_playwright = None
_context = None
_page = None


def open_browser():
    global _playwright, _context, _page

    try:
        if _context is not None:
            pages = _context.pages
            _page = next(
                (page for page in pages if not page.is_closed()),
                None,
            )
            if _page is None:
                _page = _context.new_page()

            return {
                "success": True,
                "message": "Jarvis browser is already open.",
                "url": _page.url,
            }

        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        _playwright = sync_playwright().start()

        _context = _playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            viewport=None,
        )

        pages = _context.pages
        _page = pages[0] if pages else _context.new_page()

        return {
            "success": True,
            "message": "Jarvis's persistent Chrome profile is open.",
            "url": _page.url,
            "profile_directory": str(PROFILE_DIR),
        }

    except Exception as error:
        return {
            "success": False,
            "error": f"{type(error).__name__}: {error}",
        }



def open_website_browser(url, profile="general"):
    if not isinstance(url, str) or not url.strip():
        return {"success": False, "error": "A URL is required."}

    if not url.strip().startswith(("https://", "http://")):
        return {"success": False, "error": "Only HTTP and HTTPS URLs are allowed."}

    result = open_browser()
    if not result["success"]:
        return result

    try:
        try:
            _page.goto(
                url.strip(),
                wait_until="commit",
                timeout=30000,
            )
        except Exception as navigation_error:
            # A redirect can interrupt navigation. If the page is still alive,
            # inspect its actual URL instead of claiming navigation succeeded.
            if _page.is_closed():
                return {
                    "success": False,
                    "error": f"Browser page closed during navigation: {navigation_error}",
                }

        current_url = _page.url
        title = _page.title()

        if "accounts.google.com" in current_url.lower():
            return {
                "success": False,
                "message": "Google sign-in is required in this browser profile.",
                "url": current_url,
                "title": title,
                "profile": profile,
            }

        return {
            "success": True,
            "url": current_url,
            "title": title,
            "profile": profile,
        }

    except Exception as error:
        return {
            "success": False,
            "error": f"Navigation failed: {type(error).__name__}: {error}",
        }


def click_youtube_search(profile="general"):
    result = open_browser()
    if not result["success"]:
        return result

    try:
        if "youtube.com" not in _page.url.lower():
            return {
                "success": False,
                "error": "The Jarvis browser is not on YouTube. Open YouTube first.",
                "url": _page.url,
            }

        search_box = _page.locator(
            'input#search, input[name="search_query"]'
        ).first

        search_box.wait_for(state="visible", timeout=15000)
        search_box.click(timeout=10000)

        focused = search_box.evaluate(
            "(element) => element === document.activeElement"
        )

        return {
            "success": bool(focused),
            "clicked": True,
            "verified": bool(focused),
            "profile": profile,
            "url": _page.url,
        }

    except Exception as error:
        return {
            "success": False,
            "error": f"Click verification failed: {type(error).__name__}: {error}",
        }


def search_youtube_browser(query, profile="general"):
    if not isinstance(query, str) or not query.strip():
        return {"success": False, "error": "Enter a search query."}

    url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(query.strip())
    )

    result = open_website_browser(url, profile)
    if not result["success"]:
        return result

    try:
        videos = _page.locator("ytd-video-renderer")
        videos.first.wait_for(state="visible", timeout=20000)

        return {
            "success": True,
            "query": query,
            "url": _page.url,
            "first_result": videos.first.locator("#video-title").get_attribute("title"),
            "verified": True,
            "profile": profile,
        }

    except Exception as error:
        return {
            "success": False,
            "error": f"Search verification failed: {type(error).__name__}: {error}",
            "url": _page.url,
        }


def browser_page_info(profile="general"):
    result = open_browser()
    if not result["success"]:
        return result

    return {
        "success": True,
        "url": _page.url,
        "title": _page.title(),
        "profile": profile,
    }


def close_browser():
    global _playwright, _context, _page

    try:
        if _context is not None:
            _context.close()

        if _playwright is not None:
            _playwright.stop()

        _playwright = None
        _context = None
        _page = None

        return {"success": True, "message": "Jarvis browser closed."}

    except Exception as error:
        return {"success": False, "error": str(error)}



def click_element(selector, timeout=10000):
    """Click a page element using a CSS selector and verify it."""
    result = open_browser()
    if not result["success"]:
        return result

    if not isinstance(selector, str) or not selector.strip():
        return {"success": False, "error": "A CSS selector is required."}

    try:
        element = _page.locator(selector.strip()).first
        element.click(timeout=timeout)

        return {
            "success": True,
            "action": "click",
            "selector": selector,
            "url": _page.url,
            "verified": True,
        }
    except Exception as error:
        return {
            "success": False,
            "error": f"Browser click failed: {type(error).__name__}: {error}",
            "url": _page.url,
        }


def fill_element(selector, text, timeout=10000):
    """Fill a webpage input using a CSS selector."""
    result = open_browser()
    if not result["success"]:
        return result

    if not isinstance(selector, str) or not selector.strip():
        return {"success": False, "error": "A CSS selector is required."}

    if not isinstance(text, str):
        return {"success": False, "error": "Input text must be a string."}

    try:
        element = _page.locator(selector.strip()).first
        element.fill(text, timeout=timeout)

        actual_value = element.input_value(timeout=timeout)

        return {
            "success": True,
            "action": "fill",
            "selector": selector,
            "verified": actual_value == text,
            "url": _page.url,
        }
    except Exception as error:
        return {
            "success": False,
            "error": f"Browser fill failed: {type(error).__name__}: {error}",
            "url": _page.url,
        }


def press_element(selector, key, timeout=10000):
    """Press a key while a selected webpage element is focused."""
    result = open_browser()
    if not result["success"]:
        return result

    if not isinstance(selector, str) or not selector.strip():
        return {"success": False, "error": "A CSS selector is required."}

    if not isinstance(key, str) or not key.strip():
        return {"success": False, "error": "A key is required."}

    try:
        element = _page.locator(selector.strip()).first
        element.press(key.strip(), timeout=timeout)

        return {
            "success": True,
            "action": "press",
            "selector": selector,
            "key": key,
            "url": _page.url,
        }
    except Exception as error:
        return {
            "success": False,
            "error": f"Browser key press failed: {type(error).__name__}: {error}",
            "url": _page.url,
        }


def read_page_text(selector="body", timeout=10000):
    """Read visible text from a webpage element."""
    result = open_browser()
    if not result["success"]:
        return result

    if not isinstance(selector, str) or not selector.strip():
        return {"success": False, "error": "A CSS selector is required."}

    try:
        element = _page.locator(selector.strip()).first
        element.wait_for(state="visible", timeout=timeout)
        text = element.inner_text(timeout=timeout)

        return {
            "success": True,
            "url": _page.url,
            "title": _page.title(),
            "text": text[:12000],
        }
    except Exception as error:
        return {
            "success": False,
            "error": f"Reading page failed: {type(error).__name__}: {error}",
            "url": _page.url,
        }




def skip_video(seconds=30):
    """Skip forward or backward in the currently playing HTML video."""
    result = open_browser()
    if not result["success"]:
        return result

    if "/watch" not in _page.url:
        return {
            "success": False,
            "error": "No YouTube watch page is open. Open a video before skipping.",
            "url": _page.url,
        }

    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
        return {"success": False, "error": "Seconds must be a number."}

    try:
        video = _page.locator("video").first
        video.wait_for(state="attached", timeout=15000)

        outcome = video.evaluate(
            """(element, amount) => {
                const before = element.currentTime;
                const target = Math.max(
                    0,
                    Math.min(element.duration || Infinity, before + amount)
                );
                element.currentTime = target;
                return {
                    before: before,
                    after: element.currentTime,
                    duration: element.duration
                };
            }""",
            seconds,
        )

        return {
            "success": True,
            "seconds_requested": seconds,
            "position_before": outcome["before"],
            "position_after": outcome["after"],
            "duration": outcome["duration"],
            "verified": abs(
                outcome["after"] - max(
                    0,
                    min(
                        outcome["duration"]
                        if outcome["duration"] is not None
                        else float("inf"),
                        outcome["before"] + seconds,
                    ),
                )
            ) < 1.0,
            "url": _page.url,
        }
    except Exception as error:
        return {
            "success": False,
            "error": f"Video seek failed: {type(error).__name__}: {error}",
            "url": _page.url,
        }


def play_first_youtube_result(query, skip_seconds=30):
    """Search YouTube, open the first video, and optionally seek."""
    if not isinstance(query, str) or not query.strip():
        return {"success": False, "error": "A search query is required."}

    if (
        not isinstance(skip_seconds, (int, float))
        or isinstance(skip_seconds, bool)
        or abs(skip_seconds) > 3600
    ):
        return {"success": False, "error": "Invalid skip amount."}

    result = open_browser()
    if not result["success"]:
        return result

    try:
        search_url = (
            "https://www.youtube.com/results?search_query="
            + quote_plus(query.strip())
        )

        _page.goto(search_url, wait_until="domcontentloaded", timeout=45000)

        videos = _page.locator("ytd-video-renderer")
        videos.first.wait_for(state="visible", timeout=20000)

        first_video = videos.first.locator(
            "a#video-title"
        ).first

        first_video.wait_for(state="visible", timeout=15000)

        title = (
            first_video.get_attribute("title")
            or first_video.inner_text()
        ).strip()

        href = first_video.get_attribute("href")

        if not href or "/watch" not in href:
            return {
                "success": False,
                "error": "The first result did not provide a valid video link.",
                "title": title,
                "url": _page.url,
            }

        video_url = "https://www.youtube.com" + href if href.startswith("/") else href

        _page.goto(video_url, wait_until="domcontentloaded", timeout=45000)

        _page.wait_for_url("**/watch?**", timeout=20000)

        player = _page.locator("video.html5-main-video").first
        player.wait_for(state="attached", timeout=20000)

        _page.wait_for_function(
            """() => {
                const video = document.querySelector("video.html5-main-video");
                return video &&
                       Number.isFinite(video.duration) &&
                       video.duration > 0;
            }""",
            timeout=20000,
        )

        before = player.evaluate("(v) => v.currentTime")
        duration = player.evaluate("(v) => v.duration")

        target = min(before + skip_seconds, duration)

        player.evaluate("(v, t) => { v.currentTime = t; }", target)

        _page.wait_for_function(
            """(target) => {
                const video = document.querySelector("video.html5-main-video");
                return video && Math.abs(video.currentTime - target) < 1;
            }""",
            arg=target,
            timeout=10000,
        )

        after = player.evaluate("(v) => v.currentTime")

        verified = (
            "/watch" in _page.url
            and abs(after - target) < 1
            and duration > 0
        )

        return {
            "success": verified,
            "query": query,
            "first_result_title": title,
            "url": _page.url,
            "position_before": before,
            "position_after": after,
            "duration": duration,
            "verified": verified,
            "error": None if verified else "Playback position verification failed.",
        }

    except Exception as error:
        return {
            "success": False,
            "error": f"{type(error).__name__}: {error}",
            "url": _page.url,
        }
