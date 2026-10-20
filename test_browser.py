
import time

from tools.browser_tools import (
    open_website_browser,
    click_youtube_search,
)

print("Opening YouTube...")
print(open_website_browser("https://www.youtube.com"))

print("\nClicking and verifying the search box...")
print(click_youtube_search())

print("\nBrowser will remain open for 60 seconds.")
print("You can manually check the search box.")

try:
    time.sleep(60)
finally:
    print("Test finished. Closing browser...")
    from tools.browser_tools import close_browser
    print(close_browser())
