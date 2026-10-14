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
from elo_engine import (
    compute_doc3_methods,
    get_normal_bin_info,
    normal_cdf,
    parse_title_and_year,
)
from state import AppState
from posters import get_custom_poster, load_poster_cache, save_poster_cache, get_poster_url, prefetch_posters, reset_custom_poster

_RATINGS_CACHE = None
METHOD_CACHE_FILE = "method_ratings.json"


def load_method_cache():
    if os.path.exists(METHOD_CACHE_FILE):
        try:
            with open(METHOD_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                AppState.imported_methods = {k.lower(): (v[0], v[1]) for k, v in data.items()}
        except Exception as e:
            print(f"Error loading method cache: {e}")


def save_method_cache():
    try:
        with open(METHOD_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(AppState.imported_methods, f, indent=2)
    except Exception as e:
        print(f"Error saving method cache: {e}")


def get_movie_original_ratings():
    global _RATINGS_CACHE
    if _RATINGS_CACHE is not None:
        return _RATINGS_CACHE

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

    _RATINGS_CACHE = (ratings_map, ratings_list)
    return _RATINGS_CACHE


def get_existing_movie_identities(movie_list=None):
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
    base_title, year_str = parse_title_and_year(title, year)
    base_lower = base_title.lower()
    year_str = str(year_str).strip()

    if (base_lower, year_str) in existing_identities:
        return True

    if year_str and (base_lower, "") in existing_identities:
        return True

    if not year_str:
        for ex_title, ex_year in existing_identities:
            if ex_title == base_lower:
                return True

    return False


def disambiguate_titles(entries):
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
    load_method_cache()
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
                    raw_val = row[4].strip() if len(row) > 4 else ""
                    r_val = float(raw_val) if raw_val else 1500.0
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

    with open(".save.csv.tmp", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(AppState.movie_elo)
    os.replace('.save.csv.tmp', 'save.csv')


def append_to_ratings_csv(rows):
    global _RATINGS_CACHE
    file_exists = os.path.exists("ratings.csv")
    try:
        with open("ratings.csv", "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Date", "Name", "Year", "Letterboxd URI", "Rating"])
            for item in rows:
                title, r_val, year = item[0], item[1], item[2]
                writer.writerow(["", title, year, "", r_val])
            _RATINGS_CACHE = None
    except Exception as e:
        print(f"Error writing to ratings.csv: {e}")


def remove_movie_from_db(title):
    title_low = title.lower()
    base_t, _ = parse_title_and_year(title)
    base_low = base_t.lower()

    removed = next((movie for movie in AppState.movie_elo if movie[0].lower() == title_low), None)
    if removed and get_custom_poster(removed[0], removed[2]):
        reset_custom_poster(removed[0], removed[2])

    AppState.movie_elo = [m for m in AppState.movie_elo if m[0].lower() != title_low]


    AppState.imported_methods.pop(title_low, None)
    AppState.imported_methods.pop(base_low, None)
    save_method_cache()

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
                    if len(row) > 1 and row[1].strip().lower() in (title_low, base_low):
                        continue
                    rows.append(row)
            with open("ratings.csv", "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerows(rows)
            global _RATINGS_CACHE
            _RATINGS_CACHE = None
        except Exception as e:
            print(f"Error updating ratings.csv on delete: {e}")


def generate_export_csv(export_type="elo_data", method="norm"):
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

    if export_type == "letterboxd":
        writer.writerow(["Date", "Name", "Year", "Letterboxd URI", "Rating"])
        for item in sorted_movies:
            title = item[0]
            elo_val = item[1]
            year = item[2]
            z_score = (elo_val - mean_elo) / std_elo if std_elo else 0.0
            bin_idx, _, _, _ = get_normal_bin_info(z_score)
            bin_num = bin_idx + 1

            if method == "exact":
                r_val = exact_map.get(title.lower(), 3.0)
            elif method == "optimal":
                r_val = optimal_map.get(title.lower(), 3.0)
            else:
                r_val = bin_num * 0.5

            writer.writerow(["", title, year, "", f"{r_val:.1f}"])
    else:
        writer.writerow([
            "Rank", "Title", "Release Year", "Original Rating", "Elo Rating", "Z-Score (σ)",
            "Normal Bin Category", "Normal Bin Star Rating",
            "Method 1 Rating (Preserved Count)", "Method 2 Rating (Optimal L1 DP)"
        ])

        for rank, item in enumerate(sorted_movies, 1):
            title = item[0]
            elo_val = item[1]
            year = item[2]
            z_score = (elo_val - mean_elo) / std_elo if std_elo else 0.0
            bin_idx, bin_label, _, _ = get_normal_bin_info(z_score)
            bin_num = bin_idx + 1
            norm_star = bin_num * 0.5
            method1_val = exact_map.get(title.lower(), 3.0)
            method2_val = optimal_map.get(title.lower(), 3.0)

            orig_list = ratings_map.get(title.lower(), [])
            orig_val = f"{orig_list[0]:.1f}" if orig_list else f"{norm_star:.1f}"

            writer.writerow([
                rank,
                title,
                year,
                orig_val,
                f"{elo_val:.1f}",
                f"{z_score:+.2f}",
                f"Bin {bin_num} ({bin_label})",
                f"{norm_star:.1f}",
                f"{method1_val:.1f}",
                f"{method2_val:.1f}"
            ])

    return output.getvalue()


def sync_ratings_csv(rows_to_sync):
    global _RATINGS_CACHE

    existing_rows = []
    existing_indices = {}

    if os.path.exists("ratings.csv"):
        try:
            with open("ratings.csv", "r", newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                first = next(reader, None)
                if first:
                    existing_rows.append(first)

                for row in reader:
                    if len(row) > 1:
                        title = row[1].strip()
                        year = row[2].strip() if len(row) > 2 else ""
                        base_t, y_s = parse_title_and_year(title, year)
                        key = (base_t.lower(), str(y_s).strip())
                        existing_indices[key] = len(existing_rows)
                    existing_rows.append(row)
        except Exception as e:
            print(f"Error reading ratings.csv for sync: {e}")

    if not existing_rows:
        existing_rows.append(["Date", "Name", "Year", "Letterboxd URI", "Rating"])

    for item in rows_to_sync:
        title, r_val, year = item[0], item[1], item[2]
        base_t, y_s = parse_title_and_year(title, year)
        key = (base_t.lower(), str(y_s).strip())

        if key in existing_indices:
            idx = existing_indices[key]
            row = existing_rows[idx]
            while len(row) < 5:
                row.append("")
            row[4] = f"{r_val:.1f}"
        else:
            new_row = ["", title, str(year) if year else "", "", f"{r_val:.1f}"]
            existing_indices[key] = len(existing_rows)
            existing_rows.append(new_row)

    try:
        with open("ratings.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerows(existing_rows)
    except Exception as e:
        print(f"Error syncing ratings.csv: {e}")

    _RATINGS_CACHE = None


def process_ratings_csv_data(csv_text_data):
    global _RATINGS_CACHE

    existing_map = {}
    for idx, m in enumerate(AppState.movie_elo):
        base_t, y_s = parse_title_and_year(m[0], m[2] if len(m) > 2 else "")
        existing_map[(base_t.lower(), str(y_s).strip())] = idx

    rows_to_process = []
    star_ratings_list = []

    csv_file = io.StringIO(csv_text_data)
    reader = csv.reader(csv_file)

    first_row = next(reader, None)
    if not first_row:
        return 0, len(AppState.movie_elo)

    header_lower = [col.strip().lower() for col in first_row]

    title_idx = None
    year_idx = None
    rating_idx = None
    elo_idx = None
    orig_rating_idx = None
    m1_idx = None
    m2_idx = None
    has_header = False

    for i, col in enumerate(header_lower):
        if col in ["title", "name", "movie title", "film title"]:
            title_idx = i
            has_header = True
        elif col in ["year", "release year"]:
            year_idx = i
            has_header = True
        elif col in ["elo rating", "elo"]:
            elo_idx = i
            has_header = True
        elif "original" in col:
            orig_rating_idx = i
            has_header = True
        elif "method 1" in col:
            m1_idx = i
            has_header = True
        elif "method 2" in col:
            m2_idx = i
            has_header = True
        elif col in ["rating", "score"]:
            rating_idx = i
            has_header = True

    rows_to_check = []
    if not has_header:
        rows_to_check.append(first_row)

    rows_to_check.extend(list(reader))

    for row in rows_to_check:
        if not row:
            continue

        t_i = title_idx if title_idx is not None else (1 if len(row) >= 5 else 0)
        y_i = year_idx
        r_i = rating_idx if rating_idx is not None else (4 if len(row) >= 5 else 1)
        e_i = elo_idx

        if len(row) > t_i:
            title = row[t_i].strip()
            if not title:
                continue

            year_val = ""
            if y_i is not None and len(row) > y_i:
                year_val = row[y_i].strip()
            year = int(year_val) if year_val.isdigit() else ""

            raw_elo = None
            if e_i is not None and len(row) > e_i and row[e_i].strip():
                try:
                    raw_elo = float(row[e_i].strip().replace("+", ""))
                except ValueError:
                    pass

            raw_m1 = None
            if m1_idx is not None and len(row) > m1_idx and row[m1_idx].strip():
                try:
                    raw_m1 = float(row[m1_idx].strip().replace("+", ""))
                except ValueError:
                    pass

            raw_m2 = None
            if m2_idx is not None and len(row) > m2_idx and row[m2_idx].strip():
                try:
                    raw_m2 = float(row[m2_idx].strip().replace("+", ""))
                except ValueError:
                    pass

            raw_star = None
            if orig_rating_idx is not None and len(row) > orig_rating_idx and row[orig_rating_idx].strip():
                try:
                    raw_star = float(row[orig_rating_idx].strip().replace("+", ""))
                except ValueError:
                    pass

            if raw_star is None and raw_m1 is not None:
                raw_star = raw_m1

            if raw_star is None and r_i is not None and len(row) > r_i and row[r_i].strip():
                try:
                    val = float(row[r_i].strip().replace("+", ""))
                    if val <= 10.0:
                        raw_star = val
                    elif raw_elo is None:
                        raw_elo = val
                except ValueError:
                    pass

            if raw_elo is None and raw_star is None:
                continue

            if raw_m1 is not None or raw_m2 is not None:
                base_t, _ = parse_title_and_year(title, year)
                AppState.imported_methods[title.lower()] = (raw_m1, raw_m2)
                if base_t:
                    AppState.imported_methods[base_t.lower()] = (raw_m1, raw_m2)

            rows_to_process.append({
                "title": title,
                "year": year,
                "raw_elo": raw_elo,
                "raw_star": raw_star,
            })

            if raw_star is not None:
                star_ratings_list.append(raw_star)

    if not rows_to_process:
        return 0, len(AppState.movie_elo)

    if star_ratings_list:
        if len(star_ratings_list) > 1:
            r_mean = sum(star_ratings_list) / len(star_ratings_list)
            r_var = sum((r - r_mean) ** 2 for r in star_ratings_list) / len(star_ratings_list)
            r_std = math.sqrt(r_var) if r_var > 0 else 1.0
        else:
            r_mean, r_std = 3.0, 1.0
    else:
        r_mean, r_std = 3.0, 1.0

    added_count = 0
    synced_rows = []

    for item in rows_to_process:
        title = item["title"]
        year = item["year"]
        raw_elo = item["raw_elo"]
        raw_star = item["raw_star"]

        if raw_elo is not None:
            final_elo = raw_elo
        else:
            z = (raw_star - r_mean) / r_std if r_std else 0.0
            final_elo = DEFAULT_ELO_MEAN + (z * DEFAULT_ELO_STD)

        if raw_star is not None:
            final_star = raw_star
        else:
            z_score = (final_elo - DEFAULT_ELO_MEAN) / DEFAULT_ELO_STD if DEFAULT_ELO_STD else 0.0
            final_star = round((0.5 + 4.5 * normal_cdf(z_score)) * 2) / 2

        base_t, y_s = parse_title_and_year(title, year)
        key = (base_t.lower(), str(y_s).strip())

        if key in existing_map:
            idx = existing_map[key]
            AppState.movie_elo[idx][1] = final_elo
            if year:
                AppState.movie_elo[idx][2] = year
        else:
            AppState.movie_elo.append([title, final_elo, year])
            existing_map[key] = len(AppState.movie_elo) - 1
            added_count += 1

        synced_rows.append((title, final_star, year))

    AppState.movie_elo = disambiguate_titles(AppState.movie_elo)

    AppState.elo = Implementation()
    for m in AppState.movie_elo:
        AppState.elo.addPlayer(m[0], rating=m[1])

    save_to_csv()
    save_method_cache()
    sync_ratings_csv(synced_rows)

    _RATINGS_CACHE = None
    return added_count, len(AppState.movie_elo) - added_count
