import json
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load JSON
with open("static_movies.json", "r", encoding="utf-8") as f:
    movies = json.load(f)

updated_movies = {}
log_entries = []
summary = {
    "total_movies": len(movies),
    "total_links": 0,
    "online": 0,
    "offline": 0
}

current_date = datetime.today().strftime("%Y-%m-%d")

# Function to check a single link
def check_link(movie_name, link):
    url = link["url"]
    result = {}
    try:
        response = requests.head(url, timeout=10)
        if response.status_code == 200:
            link["status"] = "online"
            link["last_online"] = current_date
            result["status"] = "online"
            log_entries.append(f"[ONLINE] {movie_name} -> {url}")
        else:
            link["status"] = "offline"
            link["last_offline"] = current_date
            result["status"] = "offline"
            log_entries.append(f"[OFFLINE] {movie_name} -> {url} (HTTP {response.status_code})")
    except requests.RequestException as e:
        link["status"] = "offline"
        link["last_offline"] = current_date
        result["status"] = "offline"
        log_entries.append(f"[ERROR] {movie_name} -> {url} ({e})")
    result["movie_name"] = movie_name
    result["link"] = link
    return result

# Prepare all links
tasks = []
for movie_name in sorted(movies.keys()):  # sort alphabetically
    movie = movies[movie_name]
    for link in movie.get("links", []):
        summary["total_links"] += 1
        tasks.append((movie_name, link))

# Run in parallel
with ThreadPoolExecutor(max_workers=100) as executor:
    futures = [executor.submit(check_link, m, l) for m, l in tasks]
    for future in as_completed(futures):
        res = future.result()
        updated_movies.setdefault(res["movie_name"], {"links": []})
        # preserve other movie info
        movie_info = movies[res["movie_name"]].copy()
        movie_info["links"] = []  # we'll fill links separately
        updated_movies[res["movie_name"]] = movie_info
        updated_movies[res["movie_name"]]["links"].append(res["link"])
        if res["status"] == "online":
            summary["online"] += 1
        else:
            summary["offline"] += 1

# Save updated JSON
with open("static_movies.json", "w", encoding="utf-8") as f:
    json.dump(updated_movies, f, indent=2)

# Save log to file
with open("movies_check_log.txt", "w", encoding="utf-8") as log_file:
    for entry in log_entries:
        log_file.write(entry + "\n")

# Print summary
print("===== CHECK SUMMARY =====")
print(f"Total Movies: {summary['total_movies']}")
print(f"Total Links: {summary['total_links']}")
print(f"Online Links: {summary['online']}")
print(f"Offline Links: {summary['offline']}")
print("=========================")
