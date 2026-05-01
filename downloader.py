import re
import os
import time
import requests

DELAY = 1.0  # seconds between downloads

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
}


def main():
    url = input("Image URL: ").strip()

    # Find the trailing number before the extension
    match = re.search(r"(\d+)(\.\w+)$", url)
    if not match:
        print("Could not detect a page number in the URL.")
        return

    pad = len(match.group(1))       # e.g. 2 for "02"
    ext = match.group(2)            # e.g. ".jpg"
    template = url[:match.start()] + "{:0" + str(pad) + "d}" + ext

    # Folder name from /manga/<name> or fallback to URL segment
    comic = re.search(r"/manga/([^/]+)", url)
    folder = comic.group(1) if comic else url.split("/")[-3]
    os.makedirs(folder, exist_ok=True)

    count = input("How many pages? ").strip()
    if not count.isdigit() or int(count) < 1:
        print("Invalid number.")
        return
    count = int(count)

    print(f"\nSaving to: {folder}/\n")

    for i in range(1, count + 1):
        page_url = template.format(i)
        filename = os.path.join(folder, f"{i:03d}{ext}")
        print(f"  [{i}/{count}] {page_url} ... ", end="", flush=True)
        try:
            r = requests.get(page_url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(r.content)
                print(f"OK ({len(r.content) // 1024} KB)")
            else:
                print(f"HTTP {r.status_code}")
        except Exception as e:
            print(f"ERROR: {e}")
        if i < count:
            time.sleep(DELAY)

    print("\nDone.")


if __name__ == "__main__":
    main()
