from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
import math
import os
import re
from elopy import Implementation
import requests
from collections import Counter

from config import CACHE_FILE, DEFAULT_ELO_MEAN, DEFAULT_ELO_STD, TMDB_API_KEY
from elo_engine import compute_doc3_methods, get_normal_bin_info, normal_cdf
from state import AppState



def parse_title_and_year(title, year=None):
    """
    Extracts the base title and release year from a title string or explicit year parameter.
    Handles titles formatted as 'Movie Title (YYYY)' as well as standalone year inputs.
    """
    title_str = str(title).strip()
    year_str = str(year).strip() if year is not None and str(year).strip() else ""

    match = re.search(r"^(.*?)\s*\((\d{4})\)$", title_str)
    if match:
        base_title = match.group(1).strip()
        if not year_str:
            year_str = match.group(2)
    else:
        base_title = title_str

    return base_title, year_str

def load_poster_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                AppState.poster_cache = {tuple(k.split("|||")): v for k, v in data.items()}
        except Exception as e:
            print(f"Error loading poster cache: {e}")

def get_existing_movie_identities(movie_list=None):
    """
    Returns a set of (base_title_lower, year_str) tuples representing existing movies in the DB.
    """
    if movie_list is None:
        movie_list = AppState.movie_elo

    identities = set()
    for m in movie_list:
        m_title = m[0]
        m_year = m[2] if len(m) > 2 else ""
        base_title, year_str = parse_title_and_year(m_title, m_year)
        identities.add((base_title.lower(), str(year_str).strip()))
    return identities

def is_duplicate_movie(title, year, existing_identities):
    """
    Checks whether a movie title/year combination already exists in the database.
    """
    base_title, year_str = parse_title_and_year(title, year)
    base_lower = base_title.lower()
    year_str = str(year_str).strip()

    # 1. Exact match on (base_title, year)
    if (base_lower, year_str) in existing_identities:
        return True

    # 2. If incoming has a year, check if existing entry has base_title without a year
    if year_str and (base_lower, "") in existing_identities:
        return True

    # 3. If incoming has no year, check if base_title exists under any year
    if not year_str:
        for ex_title, ex_year in existing_identities:
            if ex_title == base_lower:
                return True

    return False

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

def disambiguate_titles(entries):
    """
    Appends '(Year)' to movie names ONLY if there are multiple movies 
    sharing the same base title. Single/unique titles remain unchanged.
    """
    base_counts = Counter()
    parsed_entries = []

    for item in entries:
        title = item[0].strip()
        val = item[1]
        year = item[2] if len(item) > 2 else ""
        base_title, year_str = parse_title_and_year(title, year)
        if base_title:
            base_counts[base_title.lower()] += 1
        parsed_entries.append((title, val, year_str, base_title))

    result = []
    for title, val, year_str, base_title in parsed_entries:
        if base_counts[base_title.lower()] > 1 and year_str:
            new_title = f"{base_title} ({year_str})"
        else:
            new_title = base_title

        result.append([new_title, val, year_str])
    return result


def load_initial_data():
    AppState.movie_elo = []
    raw_entries = []

    if os.path.exists("save.csv"):
        print("Loading saved ELO ratings from save.csv...")
        with open("save.csv", "r", newline="", encoding="utf-8") as file:
            read = csv.reader(file)
            for row in read:
                if len(row) >= 2:
                    title = row[0].strip()
                    rating = float(row[1]) if row[1] else DEFAULT_ELO_MEAN
                    date = int(row[2]) if len(row) > 2 and row[2] else ""
                    raw_entries.append([title, rating, date])

    if os.path.exists("ratings.csv"):
        print("Syncing ratings.csv via standard normal distribution scaling...")
        existing_keys = {m[0].lower() for m in raw_entries}
        rows_to_process = []
        ratings_list = []
        with open("ratings.csv", "r", newline="", encoding="utf-8") as file:
            read = csv.reader(file)
            next(read, None)
            for row in read:
                if len(row) > 4:
                    title = row[1].strip()
                    # Replace line 119 with:
                    raw_val = row[4].strip() if len(row) > 4 else ""
                    r_val = float(raw_val) if raw_val else 1500.0  # Replace 1500.0 with your default initial Elo
                    date = int(row[2]) if row[2] else ""
                    if title.lower() not in existing_keys:
                        rows_to_process.append([title, r_val, date])
                        ratings_list.append(r_val)

        if ratings_list:
            r_mean = sum(ratings_list) / len(ratings_list)
            r_var = sum((r - r_mean) ** 2 for r in ratings_list) / len(ratings_list)
            r_std = math.sqrt(r_var) if r_var > 0 else 1.0

            for title, r_val, date in rows_to_process:
                z = (r_val - r_mean) / r_std
                scaled_rating = DEFAULT_ELO_MEAN + (z * DEFAULT_ELO_STD)
                raw_entries.append([title, scaled_rating, date])

    AppState.movie_elo = disambiguate_titles(raw_entries)

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
    existing_identities = get_existing_movie_identities(AppState.movie_elo)
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
            if t_title and not is_duplicate_movie(t_title, y_val, existing_identities):
                rows_to_process.append((t_title, r_val, y_val))
                ratings_list.append(r_val)
                base_t, y_s = parse_title_and_year(t_title, y_val)
                existing_identities.add((base_t.lower(), str(y_s).strip()))
        except ValueError:
            pass

    for row in reader:
        if len(row) > 4:
            title = row[1].strip()
            if not title:
                continue
            year = int(row[2]) if row[2].isdigit() else ""
            if not is_duplicate_movie(title, year, existing_identities):
                try:
                    r_val = float(row[4])
                    rows_to_process.append((title, r_val, year))
                    ratings_list.append(r_val)
                    base_t, y_s = parse_title_and_year(title, year)
                    existing_identities.add((base_t.lower(), str(y_s).strip()))
                except ValueError:
                    continue

    if not rows_to_process:
        return 0, len(AppState.movie_elo)

    if len(ratings_list) > 1:
        r_mean = sum(ratings_list) / len(ratings_list)
        r_var = sum((r - r_mean) ** 2 for r in ratings_list) / len(ratings_list)
        r_std = math.sqrt(r_var) if r_var > 0 else 1.0
    else:
        r_mean, r_std = 3.0, 1.0

    added_count = 0
    for title, r_val, date in rows_to_process:
        z = (r_val - r_mean) / r_std if r_std else 0.0
        scaled_rating = DEFAULT_ELO_MEAN + (z * DEFAULT_ELO_STD)

        AppState.movie_elo.append([title, scaled_rating, date])
        added_count += 1

    AppState.movie_elo = disambiguate_titles(AppState.movie_elo)

    AppState.elo = Implementation()
    for item in AppState.movie_elo:
        AppState.elo.addPlayer(item[0], rating=item[1])

    save_to_csv()
    append_to_ratings_csv(rows_to_process)
    return added_count, len(AppState.movie_elo) - added_count