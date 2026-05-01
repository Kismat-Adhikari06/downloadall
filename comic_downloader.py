import re
import os
import time
import requests

DELAY_BETWEEN_DOWNLOADS = 1.0  # seconds, be polite to the server

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Referer": "",  # filled in per-request below
}


def parse_url(url: str):
    """
    Extract:
      - base URL with a {} placeholder where the page number goes
      - zero-pad width of the original number
      - comic folder name from the URL path
    """
    # Match a number (possibly zero-padded) just before the file extension
    match = re.search(r"(\d+)(\.\w+)$", url)
    if not match:
        raise ValueError("Could not find a page number at the end of the URL.")

    number_str = match.group(1)   # e.g. "02"
    extension  = match.group(2)   # e.g. ".jpg"
    pad_width  = len(number_str)  # e.g. 2

    # Build a template URL
    template = url[: match.start()] + "{:0" + str(pad_width) + "d}" + extension

    # Extract comic name: the segment after /manga/ (or first meaningful path segment)
    comic_match = re.search(r"/manga/([^/]+)", url)
    if comic_match:
        comic_name = comic_match.group(1)
    else:
        # Fallback: use the second-to-last path segment
        parts = [p for p in url.split("/") if p]
        comic_name = parts[-3] if len(parts) >= 3 else "comic"

    return template, pad_width, comic_name, extension


def download_pages(template: str, comic_name: str, start: int, count: int, referer: str):
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), comic_name)
    os.makedirs(folder, exist_ok=True)
    print(f"\nSaving to: {folder}\n")

    headers = {**HEADERS, "Referer": referer}
    failed = []

    for i in range(start, start + count):
        url = template.format(i)
        ext = os.path.splitext(url)[-1]
        filename = f"{i:03d}{ext}"
        filepath = os.path.join(folder, filename)

        print(f"  Downloading page {i:>3} → {filename} ... ", end="", flush=True)

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                print(f"OK ({len(resp.content) // 1024} KB)")
            else:
                print(f"FAILED (HTTP {resp.status_code})")
                failed.append(url)
        except requests.RequestException as e:
            print(f"ERROR ({e})")
            failed.append(url)

        if i < start + count - 1:
            time.sleep(DELAY_BETWEEN_DOWNLOADS)

    print(f"\nDone. {count - len(failed)}/{count} pages downloaded.")
    if failed:
        print("Failed URLs:")
        for u in failed:
            print(f"  {u}")


def main():
    print("=== Comic Page Downloader ===\n")

    url = input("Paste an image URL: ").strip()
    if not url:
        print("No URL provided. Exiting.")
        return

    try:
        template, pad_width, comic_name, extension = parse_url(url)
    except ValueError as e:
        print(f"Error: {e}")
        return

    print(f"\nDetected comic : {comic_name}")
    print(f"URL template   : {template}")
    print(f"Page number pad: {pad_width} digits")

    raw_count = input("\nHow many pages to download? ").strip()
    if not raw_count.isdigit() or int(raw_count) < 1:
        print("Invalid number. Exiting.")
        return

    count = int(raw_count)

    # Derive the base referer from the URL (scheme + host)
    from urllib.parse import urlparse
    parsed = urlparse(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"

    download_pages(template, comic_name, start=1, count=count, referer=referer)


if __name__ == "__main__":
    main()
