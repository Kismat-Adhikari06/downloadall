import os
import re
import requests
import yt_dlp

DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
}

# Instaloader session username — change this if you log in with a different account
INSTALOADER_USER = "testingforscraping2006"

# Video URL patterns to look for when scraping HTML
VIDEO_PATTERNS = [
    r'<(?:video|source)[^>]+src=["\']([^"\']+\.(?:mp4|webm|ogg|mov|m3u8)[^"\']*)["\']',
    r'<meta[^>]+(?:property=["\']og:video["\']|name=["\']og:video["\'])[^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+\.(?:mp4|webm|ogg|mov|m3u8)[^"\']*)["\'][^>]+(?:property|name)=["\']og:video["\']',
    r'["\']?(https?://[^"\'<>\s]+\.(?:mp4|webm|ogg|mov)[^"\'<>\s]*)["\']?',
    r'["\']?(https?://[^"\'<>\s]+\.m3u8[^"\'<>\s]*)["\']?',
]


def main():
    url = input("Video URL: ").strip()
    if not url:
        print("No URL provided.")
        return

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    # --- Attempt 1: yt-dlp (handles ~1800 sites) ---
    if try_ytdlp(url):
        return

    # --- Attempt 2: Instaloader (Instagram-specific) ---
    if is_instagram(url):
        print("\nTrying Instaloader for Instagram...\n")
        if try_instaloader(url):
            return
        print("Instaloader failed.")

    # --- Attempt 3: HTML scrape fallback ---
    if not is_instagram(url):
        print("\nyt-dlp couldn't handle this URL, trying HTML scrape fallback...\n")
        if try_scrape(url):
            return

    print("\nCould not find any video on this page.")


def is_instagram(url):
    return "instagram.com" in url


# ---------------------------------------------------------------------------
# Attempt 1 — yt-dlp
# ---------------------------------------------------------------------------

def try_ytdlp(url):
    """Try downloading with yt-dlp. Returns True if successful."""
    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "no_warnings": False,
        "quiet": False,
        "progress_hooks": [progress_hook],
        "overwrites": False,
        "continuedl": True,       # resume partial downloads
        "retries": 10,            # retry up to 10 times on failure
        "fragment_retries": 10,   # retry individual fragments (HLS/DASH)
        "retry_sleep_functions": {"http": lambda n: 2 ** n},  # exponential backoff
        "socket_timeout": 30,     # timeout per connection attempt
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"\nFetching info for: {url}\n")
            info = ydl.extract_info(url, download=False)

            if not info:
                return False

            # If it's a playlist/multi-video page, grab only the first entry
            if "entries" in info:
                entries = [e for e in info["entries"] if e]
                if not entries:
                    return False
                info = entries[0]
                print(f"Multiple videos found — downloading first: {info.get('title', 'unknown')}\n")

            filename = ydl.prepare_filename(info)
            if os.path.exists(filename):
                print(f"Already exists, skipping: {os.path.basename(filename)}")
                return True

            ydl.download([info.get("webpage_url") or url])
            return True

    except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError):
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Attempt 2 — Instaloader (Instagram only)
# ---------------------------------------------------------------------------

def try_instaloader(url):
    """Use Instaloader to download an Instagram video. Returns True if successful."""
    try:
        import instaloader
    except ImportError:
        print("Instaloader not installed. Run: python -m pip install instaloader")
        return False

    # Extract shortcode from URL
    # Handles /p/CODE/, /reel/CODE/, /tv/CODE/
    match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
    if not match:
        print("Could not parse Instagram URL.")
        return False

    shortcode = match.group(1)

    L = instaloader.Instaloader(
        dirname_pattern=DOWNLOADS_DIR,
        filename_pattern="{shortcode}",
        download_pictures=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
    )

    # Load saved session
    try:
        L.load_session_from_file(INSTALOADER_USER)
    except FileNotFoundError:
        print(f"No Instaloader session found for '{INSTALOADER_USER}'.")
        print(f"Run this once to log in: python -m instaloader --login {INSTALOADER_USER}")
        return False
    except Exception as e:
        print(f"Could not load session: {e}")
        return False

    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        if not post.is_video:
            print("This Instagram post doesn't contain a video.")
            return False
        print(f"Downloading: {post.title or shortcode}")
        L.download_post(post, target=DOWNLOADS_DIR)
        return True
    except instaloader.exceptions.LoginRequiredException:
        print("Instagram requires login for this post.")
        return False
    except Exception as e:
        print(f"Instaloader error: {e}")
        return False


# ---------------------------------------------------------------------------
# Attempt 3 — Static HTML scrape
# ---------------------------------------------------------------------------

def try_scrape(url):
    """Fetch raw HTML and look for video URLs. Returns True if a video was downloaded."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"Could not fetch page (HTTP {resp.status_code}).")
            return False
        html = resp.text
    except Exception as e:
        print(f"Could not fetch page: {e}")
        return False

    video_url = find_video_in_html(html, base_url=url)
    if not video_url:
        return False

    print(f"Found video URL: {video_url}\n")
    return download_direct(video_url)


def find_video_in_html(html, base_url=""):
    """Search HTML for the first video URL using known patterns."""
    for pattern in VIDEO_PATTERNS:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches:
            candidate = match.strip()
            if candidate.startswith("//"):
                candidate = "https:" + candidate
            elif candidate.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                candidate = f"{parsed.scheme}://{parsed.netloc}{candidate}"
            if candidate.startswith("http"):
                return candidate
    return None


# ---------------------------------------------------------------------------
# Direct download (requests)
# ---------------------------------------------------------------------------

def download_direct(url):
    """Download a direct video URL with requests and show progress."""
    try:
        resp = requests.get(url, headers=HEADERS, stream=True, timeout=30)
        if resp.status_code != 200:
            print(f"Could not download video (HTTP {resp.status_code}).")
            return False

        filename = url.split("?")[0].split("/")[-1] or "video.mp4"
        filepath = os.path.join(DOWNLOADS_DIR, filename)

        if os.path.exists(filepath):
            print(f"Already exists, skipping: {filename}")
            return True

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        chunk_size = 1024 * 64  # 64 KB

        print(f"Downloading: {filename}")
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r  {pct:.1f}%  ({downloaded // 1024} KB / {total // 1024} KB)   ", end="", flush=True)

        print(f"\n  Done: {filename}")
        return True

    except Exception as e:
        print(f"\nError downloading video: {e}")
        return False


# ---------------------------------------------------------------------------
# yt-dlp progress hook
# ---------------------------------------------------------------------------

def progress_hook(d):
    if d["status"] == "downloading":
        percent  = d.get("_percent_str", "?%").strip()
        speed    = d.get("_speed_str", "?").strip()
        eta      = d.get("_eta_str", "?").strip()
        filename = os.path.basename(d.get("filename", ""))
        print(f"\r  {filename}  {percent}  {speed}  ETA {eta}   ", end="", flush=True)
    elif d["status"] == "finished":
        print(f"\n  Done: {os.path.basename(d['filename'])}")
    elif d["status"] == "error":
        print(f"\n  Error downloading: {d.get('filename', '')}")


if __name__ == "__main__":
    main()
