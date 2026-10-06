from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
import math
import os
import re
from elopy import Implementation
import requests

from config import CACHE_FILE, DEFAULT_ELO_MEAN, DEFAULT_ELO_STD, TMDB_API_KEY
from elo_engine import compute_doc3_methods, get_normal_bin_info, normal_cdf
from state import AppState


def load_poster_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                AppState.poster_cache = {tuple(k.split("|||")): v for k, v in data.items()}
        except Exception as e:
            print(f"Error loading poster cache: {e}")


def save_poster_cache():
    try:
        data = {f"{k[0]}|||{k[1]}": v for k, v in AppState.poster_cache.items()}
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving poster cache: {e}")


def get_movie_original_ratings():
    ratings_map = {}
    ratings_list = []
    if os.path.exists("ratings.csv"):
        try:
            with open("ratings.csv", "r", newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                first_row = next(reader, None)
                if first_row and len(first_row) > 4:
                    try:
                        r_val = float(first_row[4])
                        t_title = first_row[1].strip()
                        if t_title:
                            ratings_map[t_title.lower()] = [r_val]
                            ratings_list.append(r_val)
                    except ValueError:
                        pass
                for row in reader:
                    if len(row) > 4:
                        try:
                            title = row[1].strip()
                            r_val = float(row[4])
                            if title:
                                if title.lower() not in ratings_map:
                                    ratings_map[title.lower()] = []
                                ratings_map[title.lower()].append(r_val)
                                ratings_list.append(r_val)
                        except ValueError:
                            continue
        except Exception as e:
            print(f"Error reading original ratings: {e}")
    return ratings_map, ratings_list


def load_initial_data():
    AppState.movie_elo = []
    existing_titles = set()

    if os.path.exists("save.csv"):
        print("Loading saved ELO ratings from save.csv...")
        with open("save.csv", "r", newline="", encoding="utf-8") as file:
            read = csv.reader(file)
            for row in read:
                if len(row) >= 2:
                    title = row[0]
                    rating = float(row[1]) if row[1] else DEFAULT_ELO_MEAN
                    date = int(row[2]) if len(row) > 2 and row[2] else ""
                    AppState.movie_elo.append([title, rating, date])
                    existing_titles.add(title)

    if os.path.exists("ratings.csv"):
        print("Syncing ratings.csv via standard normal distribution scaling...")
        rows_to_process = []
        ratings_list = []
        with open("ratings.csv", "r", newline="", encoding="utf-8") as file:
            read = csv.reader(file)
            next(read, None)
            for row in read:
                if len(row) > 4:
                    title = row[1]
                    if title not in existing_titles:
                        try:
                            r_val = float(row[4])
                            date = int(row[2]) if row[2] else ""
                            rows_to_process.append((title, r_val, date))
                            ratings_list.append(r_val)
                        except ValueError:
                            continue

        if ratings_list:
            r_mean = sum(ratings_list) / len(ratings_list)
            r_var = sum((r - r_mean) ** 2 for r in ratings_list) / len(ratings_list)
            r_std = math.sqrt(r_var) if r_var > 0 else 1.0

            for title, r_val, date in rows_to_process:
                z = (r_val - r_mean) / r_std
                scaled_rating = DEFAULT_ELO_MEAN + (z * DEFAULT_ELO_STD)
                AppState.movie_elo.append([title, scaled_rating, date])
                existing_titles.add(title)

    AppState.elo = Implementation()
    for item in AppState.movie_elo:
        AppState.elo.addPlayer(item[0], rating=item[1])


def save_to_csv():
    for item in AppState.movie_elo:
        try:
            item[1] = AppState.elo.getPlayerRating(item[0])
        except Exception:
            pass

    AppState.movie_elo.sort(key=lambda x: x[1], reverse=True)

    with open("save.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(AppState.movie_elo)


def append_to_ratings_csv(rows):
    file_exists = os.path.exists("ratings.csv")
    try:
        with open("ratings.csv", "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Date", "Name", "Year", "Letterboxd URI", "Rating"])
            for item in rows:
                title, r_val, year = item[0], item[1], item[2]
                writer.writerow(["", title, year, "", r_val])
    except Exception as e:
        print(f"Error writing to ratings.csv: {e}")


def remove_movie_from_db(title):
    AppState.movie_elo = [m for m in AppState.movie_elo if m[0].lower() != title.lower()]

    new_elo = Implementation()
    for item in AppState.movie_elo:
        new_elo.addPlayer(item[0], rating=item[1])
    AppState.elo = new_elo

    save_to_csv()
    if os.path.exists("ratings.csv"):
        try:
            rows = []
            with open("ratings.csv", "r", newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    if len(row) > 1 and row[1].strip().lower() == title.lower():
                        continue
                    rows.append(row)
            with open("ratings.csv", "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerows(rows)
        except Exception as e:
            print(f"Error updating ratings.csv on delete: {e}")


def get_poster_url(movie_title, api_key, release_year=None):
    title = str(movie_title).strip()
    year_str = str(release_year)[:4] if release_year and str(release_year).strip() else None

    match = re.search(r"^(.*?)\s*\((\d{4})\)$", title)
    if match:
        extracted_title = match.group(1).strip()
        extracted_year = match.group(2)
        if extracted_title:
            title = extracted_title
        if not year_str:
            year_str = extracted_year

    cache_key = (title.lower(), year_str)
    if cache_key in AppState.poster_cache:
        return AppState.poster_cache[cache_key]

    url = "https://api.themoviedb.org/3/search/movie"
    params = {"api_key": api_key, "query": title}
    if year_str:
        params["primary_release_year"] = year_str

    fallback_url = "https://via.placeholder.com/185x278?text=No+Poster"

    try:
        if api_key:
            res = requests.get(url, params=params, timeout=3).json()
            results = res.get("results", [])
            target_clean = title.lower().strip()

            for movie in results:
                m_title = movie.get("title", "").lower().strip()
                m_orig = movie.get("original_title", "").lower().strip()
                if (m_title == target_clean or m_orig == target_clean) and movie.get("poster_path"):
                    poster_url = f"https://image.tmdb.org/t/p/w185{movie['poster_path']}"
                    AppState.poster_cache[cache_key] = poster_url
                    return poster_url

            for movie in results:
                if movie.get("poster_path"):
                    poster_url = f"https://image.tmdb.org/t/p/w185{movie['poster_path']}"
                    AppState.poster_cache[cache_key] = poster_url
                    return poster_url
    except Exception as e:
        print(f"Error fetching {title} ({year_str}): {e}")

    AppState.poster_cache[cache_key] = fallback_url
    return fallback_url


def prefetch_posters(movie_list, api_key):
    if not api_key:
        return
    uncached = []
    for item in movie_list:
        title = str(item[0]).strip()
        year_str = str(item[2])[:4] if len(item) > 2 and item[2] else None
        match = re.search(r"^(.*?)\s*\((\d{4})\)$", title)
        if match:
            title = match.group(1).strip() or title
            year_str = year_str or match.group(2)

        if (title.lower(), year_str) not in AppState.poster_cache:
            uncached.append((item[0], item[2] if len(item) > 2 else None))

    if uncached:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_poster_url, m[0], api_key, m[1]) for m in uncached]
            for future in futures:
                future.result()
        save_poster_cache()


def generate_export_csv(scale="elo"):
    for item in AppState.movie_elo:
        item[1] = AppState.elo.getPlayerRating(item[0])
    sorted_movies = sorted(AppState.movie_elo, key=lambda x: x[1], reverse=True)

    total_movies = len(sorted_movies)
    if total_movies > 0:
        elo_vals = [m[1] for m in sorted_movies]
        mean_elo = sum(elo_vals) / total_movies
        var_elo = sum((e - mean_elo) ** 2 for e in elo_vals) / total_movies
        std_elo = math.sqrt(var_elo) if var_elo > 0 else 1.0
    else:
        mean_elo, std_elo = DEFAULT_ELO_MEAN, DEFAULT_ELO_STD

    ratings_map, ratings_list = get_movie_original_ratings()
    exact_map, optimal_map, _, _ = compute_doc3_methods(sorted_movies, ratings_map, ratings_list)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Rank", "Title", "Release Year", "Exported Rating",
        "Rating Scale Format", "Elo Rating", "Z-Score (σ)", "Normal Bin Category",
    ])

    for rank, item in enumerate(sorted_movies, 1):
        title = item[0]
        elo_val = item[1]
        year = item[2]
        z_score = (elo_val - mean_elo) / std_elo if std_elo else 0.0
        bin_idx, bin_label, _, _ = get_normal_bin_info(z_score)

        if scale == "zscore":
            exported_val = f"{z_score:+.3f}"
            scale_desc = "Standard Normal Z-Score (σ)"
        elif scale == "exact":
            exported_val = f"{exact_map.get(title.lower(), 3.0):.1f}"
            scale_desc = "5-Star Scale (Method 1: Preserved Count Distribution)"
        elif scale == "optimal":
            exported_val = f"{optimal_map.get(title.lower(), 3.0):.1f}"
            scale_desc = "5-Star Scale (Method 2: Optimal L1 DP Cutoffs)"
        elif scale == "scale10":
            score_10 = 1.0 + 9.0 * normal_cdf(z_score)
            exported_val = f"{score_10:.2f}"
            scale_desc = "10-Point Percentile Scale (1.0 - 10.0)"
        elif scale == "star5":
            score_5 = 0.5 + 4.5 * normal_cdf(z_score)
            exported_val = f"{score_5:.2f}"
            scale_desc = "5-Star Percentile Scale (0.5 - 5.0)"
        else:
            exported_val = f"{elo_val:.1f}"
            scale_desc = "Raw Elo Rating Scale"

        writer.writerow([
            rank, title, year, exported_val, scale_desc,
            f"{elo_val:.1f}", f"{z_score:+.2f}", f"Bin {bin_idx + 1} ({bin_label})",
        ])

    return output.getvalue()


def process_ratings_csv_data(csv_text_data):
    existing_titles = {m[0].lower() for m in AppState.movie_elo}
    rows_to_process = []
    ratings_list = []

    csv_file = io.StringIO(csv_text_data)
    reader = csv.reader(csv_file)

    first_row = next(reader, None)
    if first_row and not (len(first_row) > 4 and first_row[4].replace(".", "", 1).isdigit()):
        pass
    elif first_row and len(first_row) > 4:
        try:
            r_val = float(first_row[4])
            t_title = first_row[1].strip()
            y_val = int(first_row[2]) if first_row[2].isdigit() else ""
            if t_title.lower() not in existing_titles:
                rows_to_process.append((t_title, r_val, y_val))
                ratings_list.append(r_val)
        except ValueError:
            pass

    for row in reader:
        if len(row) > 4:
            title = row[1].strip()
            if not title:
                continue
            if title.lower() not in existing_titles:
                try:
                    r_val = float(row[4])
                    year = int(row[2]) if row[2].isdigit() else ""
                    rows_to_process.append((title, r_val, year))
                    ratings_list.append(r_val)
                except ValueError:
                    continue

    if not rows_to_process:
        return 0, len(existing_titles)

    if len(ratings_list) > 1:
        r_mean = sum(ratings_list) / len(ratings_list)
        r_var = sum((r - r_mean) ** 2 for r in ratings_list) / len(ratings_list)
        r_std = math.sqrt(r_var) if r_var > 0 else 1.0
    else:
        r_mean, r_std = 3.0, 1.0

    added_count = 0
    for title, r_val, date in rows_to_process:
        if title.lower() not in existing_titles:
            z = (r_val - r_mean) / r_std
            scaled_rating = DEFAULT_ELO_MEAN + (z * DEFAULT_ELO_STD)

            AppState.movie_elo.append([title, scaled_rating, date])
            AppState.elo.addPlayer(title, rating=scaled_rating)
            existing_titles.add(title.lower())
            added_count += 1

    save_to_csv()
    append_to_ratings_csv(rows_to_process)
    return added_count, len(existing_titles) - added_count