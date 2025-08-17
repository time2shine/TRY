import random
import datetime
import yt_dlp
import os
import time
import logging

# --- CONFIG ---
cookies_file_path = 'cookies.txt'
MAX_API_RETRIES = 1
RETRY_WAIT_SECONDS = 3

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Check cookies file exists ---
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


def get_live_video_url(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}/live"
    ydl_opts = {
        'format': 'best',
        'cookiefile': cookies_file_path,
        'force_ipv4': True,
        'retries': 10,
        'fragment_retries': 10,
        'skip_unavailable_fragments': True,
        'extractor_args': {'youtube': {'skip': ['translated_subs']}},
        'http_headers': {
            'User-Agent': get_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com/',
            'Sec-Fetch-Mode': 'navigate',
        },
        'quiet': True,
        'no_warnings': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        # If live video is active, yt-dlp gives info about that video
        if info and 'url' in info:
            return info['url']
        # Sometimes info['entries'] contains the video list
        if info and 'entries' in info and len(info['entries']) > 0:
            return info['entries'][0]['url']
    return None


# Example channels dictionary (use your full list here)
channels = {
    'UCWVqdPTigfQ-cSNwG7O9MeA': {  # Somoy News
        'channel_number': 101,
        'group_title': 'News',
        'channel_name': 'Somoy News',
        'channel_logo': 'https://yt3.googleusercontent.com/7F-3_9yjPiMJzBAuD7niglcJmFyXCrFGSEugcEroFrIkxudmhiZ9i-Q_pW4Zrn2IiCLN5dQX8A=s160-c-k-c0x00ffffff-no-rj',
    },
    # Add other channels as needed...
}

if __name__ == '__main__':
    channel_ID = 'UCxHoBXkY88Tb8z1Ssj6CWsQ'
    print(get_live_video_url(channel_ID))
