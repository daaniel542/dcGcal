import requests
import os

URL = "https://housing.ucdavis.edu/dining/menus/dining-commons/tercero/"

def fetch_menu_html(url=URL):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching menu: {e}")
        return None

if __name__ == "__main__":
    html_content = fetch_menu_html()
    if html_content:
        print("Successfully fetched HTML.")
        sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_menu.html")
        os.makedirs(os.path.dirname(sample_path), exist_ok=True)
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Saved to {sample_path}")
