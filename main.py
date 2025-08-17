import random
import yt_dlp
import os
import logging

# --- CONFIG ---
cookies_file_path = 'cookies.txt'
m3u_output = 'output.m3u'

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


def get_live_watch_url(channel_id):
    """Return YouTube watch page URL if channel is live, otherwise None"""
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
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"Failed to get info for {channel_id}: {e}")
            return None

        if not info:
            return None

        # ✅ Live video case
        if info.get("is_live"):
            return info.get("webpage_url") or f"https://www.youtube.com/watch?v={info['id']}"

        # Sometimes in entries
        if "entries" in info:
            for entry in info["entries"]:
                if entry.get("is_live"):
                    return entry.get("webpage_url") or f"https://www.youtube.com/watch?v={entry['id']}"

    return None


def save_m3u(channels, output_file):
    """Save live channels to an M3U playlist (with watch links)"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for channel_id, meta in channels.items():
            logger.info(f"Checking {meta['channel_name']}...")
            live_url = get_live_watch_url(channel_id)

            if live_url:
                logger.info(f"✅ LIVE: {meta['channel_name']}")
                f.write(
                    f'#EXTINF:-1 tvg-id="{channel_id}" '
                    f'tvg-logo="{meta["channel_logo"]}" '
                    f'group-title="{meta["group_title"]}",'
                    f'{meta["channel_name"]}\n'
                    f'{live_url}\n'
                )
            else:
                logger.info(f"❌ Not live: {meta['channel_name']}")


# --- Example channels dictionary ---
channels = {
    'UCWVqdPTigfQ-cSNwG7O9MeA': {  # Somoy News
        'channel_number': 101,
        'group_title': 'News',
        'channel_name': 'Somoy News',
        'channel_logo': 'https://yt3.googleusercontent.com/7F-3_9yjPiMJzBAuD7niglcJmFyXCrFGSEugcEroFrIkxudmhiZ9i-Q_pW4Zrn2IiCLN5dQX8A=s160-c-k-c0x00ffffff-no-rj',
    },
    # Add more channels...
}

if __name__ == '__main__':
    save_m3u(channels, m3u_output)
    logger.info(f"✅ Playlist saved to {m3u_output}")
