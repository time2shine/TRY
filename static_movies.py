import json
import requests
from datetime import datetime

# Load your JSON file
with open("static_movies.json", "r", encoding="utf-8") as f:
    movies = json.load(f)

updated_movies = {}
log_entries = []
summary = {
    "total_movies": 0,
    "total_links": 0,
    "online": 0,
    "offline": 0
}

current_date = datetime.today().strftime("%Y-%m-%d")

for movie_name in sorted(movies.keys()):  # sort alphabetically
    movie = movies[movie_name]
    summary["total_movies"] += 1
    for link in movie.get("links", []):
        summary["total_links"] += 1
        url = link["url"]
        try:
            response = requests.head(url, timeout=10)
            if response.status_code == 200:
                link["status"] = "online"
                link["last_online"] = current_date
                summary["online"] += 1
                log_entries.append(f"[ONLINE] {movie_name} -> {url}")
            else:
                link["status"] = "offline"
                link["last_offline"] = current_date
                summary["offline"] += 1
                log_entries.append(f"[OFFLINE] {movie_name} -> {url} (HTTP {response.status_code})")
        except requests.RequestException as e:
            link["status"] = "offline"
            link["last_offline"] = current_date
            summary["offline"] += 1
            log_entries.append(f"[ERROR] {movie_name} -> {url} ({e})")

    updated_movies[movie_name] = movie

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
