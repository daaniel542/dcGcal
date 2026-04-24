"""
Fetch the UC Davis dining commons menu page HTML.

Includes retry logic and proper logging.
"""

import requests
import os
import logging
import time

logger = logging.getLogger(__name__)

DEFAULT_URL = "https://housing.ucdavis.edu/dining/menus/dining-commons/tercero/"

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def fetch_menu_html(url=DEFAULT_URL, retries=MAX_RETRIES):
    """
    Fetch the menu HTML from the given URL with retry logic.

    Args:
        url: The dining commons menu page URL.
        retries: Number of retry attempts on failure.

    Returns:
        The HTML content as a string, or None on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Fetching {url} (attempt {attempt}/{retries})")
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'AggieMealNotifier/1.0'
            })
            response.raise_for_status()

            html = response.text
            if len(html) < 500:
                logger.warning(f"Response suspiciously short ({len(html)} bytes). Menu may be empty.")

            return html

        except requests.Timeout:
            logger.warning(f"Timeout on attempt {attempt}/{retries}")
        except requests.ConnectionError as e:
            logger.warning(f"Connection error on attempt {attempt}/{retries}: {e}")
        except requests.HTTPError as e:
            logger.error(f"HTTP error {response.status_code}: {e}")
            return None  # Don't retry on 4xx/5xx
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")

        if attempt < retries:
            logger.info(f"Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)

    logger.error(f"All {retries} attempts failed for {url}")
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    html_content = fetch_menu_html()
    if html_content:
        print(f"Successfully fetched HTML ({len(html_content)} bytes).")
        sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_menu.html")
        os.makedirs(os.path.dirname(sample_path), exist_ok=True)
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Saved to {sample_path}")
    else:
        print("Failed to fetch menu.")
