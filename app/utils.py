import requests
from bs4 import BeautifulSoup


def clean_text(text):

    if not text:
        return ""

    # Remove excessive whitespace
    lines = []

    for line in text.splitlines():

        line = line.strip()

        if line:
            lines.append(line)

    text = "\n".join(lines)

    return text


def fetch_webpage(url):

    """
    Fetch webpage HTML and convert it to readable text.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # Remove useless elements
    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "footer",
            "nav"
        ]
    ):
        tag.decompose()

    text = soup.get_text(
        separator="\n"
    )

    return clean_text(text)