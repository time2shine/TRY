import random
import yt_dlp
import os
import logging

cookies_file_path = 'cookies.txt'

if not os.path.exists(cookies_file_path):
    raise FileNotFoundError(f"Missing cookies file: {cookies_file_path}")

def get_user_agent():
    versions = [
        (122, 6267, 70), (121, 6167, 131), (120, 6099, 109)
    ]
    major, build, patch = random.choice(versions)
    return (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{major}.0.{build}.{patch} Safari/537.36"
    )

def get_live_watch_url(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}/live"
    ydl_opts = {
        'cookiefile': cookies_file_path,
        'force_ipv4': True,
        'http_headers': {
            'User-Agent': get_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com/',
            'Sec-Fetch-Mode': 'navigate',
        },
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            return None

        if info.get("is_live"):
            return info.get("webpage_url") or f"https://www.youtube.com/watch?v={info['id']}"

        if "entries" in info:
            for entry in info["entries"]:
                if entry.get("is_live"):
                    return entry.get("webpage_url") or f"https://www.youtube.com/watch?v={entry['id']}"

    return None


if __name__ == '__main__':
    channel_ID = "UCWVqdPTigfQ-cSNwG7O9MeA"  # Somoy News
    live_url = get_live_watch_url(channel_ID)
    print(live_url if live_url else "Channel is not live")
