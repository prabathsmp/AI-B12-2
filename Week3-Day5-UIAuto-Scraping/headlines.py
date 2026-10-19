import requests
from bs4 import BeautifulSoup

URL = "https://www.dailythanthi.com/"

HEADERS = {
"User-Agent": (
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
"AppleWebKit/537.36 (KHTML, like Gecko) "
"Chrome/131.0.0.0 Safari/537.36"
)
}

def main():
    try:
        # Fetch the webpage
        response = requests.get(URL, headers=HEADERS, timeout=10)

        # Check HTTP status before parsing
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Find headline elements using the inspected HTML structure
        items = soup.select('a[aria-label="headline"] h3')

        headlines = []
        seen = set()

        for item in items:
            headline = item.get_text(" ", strip=True)

            # Skip empty or duplicate headlines
            if not headline or headline in seen:
                continue

            seen.add(headline)
            headlines.append(headline)

            if len(headlines) == 5:
                break

        # Print results
        if not headlines:
            print("No headlines found in the fetched HTML.")
            return

        for number, headline in enumerate(headlines, start=1):
            print(f"{number}. {headline}")

        if len(headlines) < 5:
            print(
                f"Only {len(headlines)} unique headlines found "
                f"instead of 5."
            )

    except requests.RequestException as error:
        print(f"Failed to fetch the webpage: {error}")

if __name__ == "__main__":
    main()
