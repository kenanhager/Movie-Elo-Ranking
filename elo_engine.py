from collections import Counter
import math
import random
import re
from config import NORMAL_BIN_BOUNDS
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

def normal_cdf(z):
    """Calculates Cumulative Distribution Function Φ(z) for standard normal distribution."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))


def get_normal_bin_info(z_score):
    """Returns bin index, label, lower bound, and upper bound for a given z-score."""
    for idx, (low, high, label) in enumerate(NORMAL_BIN_BOUNDS):
        if low <= z_score < high or (idx == len(NORMAL_BIN_BOUNDS) - 1 and z_score >= low):
            return idx, label, low, high
    return 0, NORMAL_BIN_BOUNDS[0][2], NORMAL_BIN_BOUNDS[0][0], NORMAL_BIN_BOUNDS[0][1]


def rating_to_bin_idx(val):
    """Maps rating values to 10 bin indices."""
    if val > 5.0:
        return max(0, min(9, int((val - 1.0) / 0.9)))
    else:
        idx = int(round((val - 0.5) * 2))
        return max(0, min(9, idx))


def compute_doc3_methods(movie_list, ratings_map, ratings_list):
    """Computes Method 1 (Preserved Count Distribution) and Method 2 (Optimal L1 DP Cutoffs)."""
    if not movie_list:
        return {}, {}, [0] * 10, [0] * 10

    sorted_movies = sorted(movie_list, key=lambda x: x[1], reverse=True)
    n_movies = len(sorted_movies)

    possible_levels = [5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5]
    clean_ratings = []
    for r in ratings_list:
        try:
            r_float = float(r)
            if r_float <= 5.0:
                clean_ratings.append(round(r_float * 2) / 2)
        except (ValueError, TypeError):
            continue

    if not clean_ratings:
        clean_ratings = possible_levels * (n_movies // 10 + 1)
        clean_ratings = clean_ratings[:n_movies]

    # --- METHOD 1: Preserved Count Distribution ---
    counts = Counter(clean_ratings)
    sorted_rating_levels = sorted(counts.keys(), reverse=True)

    exact_seq = []
    for r_lvl in sorted_rating_levels:
        exact_seq.extend([r_lvl] * counts[r_lvl])

    exact_ratings_map = {}
    for idx, movie in enumerate(sorted_movies):
        assigned = exact_seq[idx] if idx < len(exact_seq) else (exact_seq[-1] if exact_seq else 3.0)
        exact_ratings_map[movie[0].lower()] = assigned

    # --- METHOD 2: Minimum Total Rating Deviation (Optimal L1 DP) ---
    avg_r = sum(clean_ratings) / len(clean_ratings) if clean_ratings else 3.0
    old_ratings = []
    temp_map = {k: list(v) for k, v in ratings_map.items()}
    for movie in sorted_movies:
        t_full = movie[0].lower()
        base_t, _ = parse_title_and_year(movie[0], movie[2] if len(movie) > 2 else "")
        base_t_low = base_t.lower()

        if t_full in temp_map and temp_map[t_full]:
            orig = temp_map[t_full].pop(0)
        elif base_t_low in temp_map and temp_map[base_t_low]:
            orig = temp_map[base_t_low].pop(0)
        else:
            orig = avg_r

        old_ratings.append(orig)

    possible_ratings = sorted(list(set(clean_ratings)), reverse=True)
    if not possible_ratings:
        possible_ratings = possible_levels

    n_levels = len(possible_ratings)

    dp = [[float("inf")] * (n_levels + 1) for _ in range(n_movies + 1)]
    parent = [[0] * (n_levels + 1) for _ in range(n_movies + 1)]
    dp[0][0] = 0

    for j in range(n_levels):
        r_val = possible_ratings[j]
        for i in range(n_movies + 1):
            if dp[i][j] == float("inf"):
                continue
            curr_cost = dp[i][j]
            if dp[i][j + 1] > curr_cost:
                dp[i][j + 1] = curr_cost
                parent[i][j + 1] = i

            max_span = min(n_movies - i, max(60, int(n_movies * 0.25)))
            for k in range(i + 1, i + max_span + 1):
                curr_cost += abs(old_ratings[k - 1] - r_val)
                if curr_cost < dp[k][j + 1]:
                    dp[k][j + 1] = curr_cost
                    parent[k][j + 1] = i

    optimal_seq = [0.0] * n_movies
    curr_i = n_movies
    for j in range(n_levels, 0, -1):
        prev_i = parent[curr_i][j]
        for idx in range(prev_i, curr_i):
            optimal_seq[idx] = possible_ratings[j - 1]
        curr_i = prev_i

    optimal_ratings_map = {}
    for idx, movie in enumerate(sorted_movies):
        optimal_ratings_map[movie[0].lower()] = optimal_seq[idx]

    # Override with exact values directly imported from CSV columns
    for movie in sorted_movies:
        t_low = movie[0].lower()
        base_t, _ = parse_title_and_year(movie[0], movie[2] if len(movie) > 2 else "")
        base_low = base_t.lower()

        imported = AppState.imported_methods.get(t_low) or AppState.imported_methods.get(base_low)
        if imported:
            m1_val, m2_val = imported
            if m1_val is not None:
                exact_ratings_map[t_low] = m1_val
            if m2_val is not None:
                optimal_ratings_map[t_low] = m2_val

    exact_bin_counts = [0] * 10
    optimal_bin_counts = [0] * 10

    for movie in sorted_movies:
        t_low = movie[0].lower()
        r_m1 = exact_ratings_map.get(t_low, 3.0)
        r_m2 = optimal_ratings_map.get(t_low, 3.0)
        exact_bin_counts[rating_to_bin_idx(r_m1)] += 1
        optimal_bin_counts[rating_to_bin_idx(r_m2)] += 1

    return exact_ratings_map, optimal_ratings_map, exact_bin_counts, optimal_bin_counts

def get_elo_matched_pair(movie_list, target_movie=None, proximity_ratio=0.75):
    if len(movie_list) < 2:
        return None, None

    for item in movie_list:
        item[1] = AppState.elo.getPlayerRating(item[0])

    use_proximity = random.random() < proximity_ratio

    if target_movie:
        m1 = target_movie
        opponents = [m for m in movie_list if m[0] != m1[0]]
        if not opponents:
            return m1, None

        if use_proximity:
            opponents.sort(key=lambda m: abs(m[1] - m1[1]))
            pool_size = min(10, len(opponents))
            m2 = random.choice(opponents[:pool_size])
        else:
            m2 = random.choice(opponents)
        return m1, m2
    else:
        if use_proximity:
            m1 = random.choice(movie_list)
            opponents = [m for m in movie_list if m[0] != m1[0]]
            opponents.sort(key=lambda m: abs(m[1] - m1[1]))
            pool_size = min(10, len(opponents))
            m2 = random.choice(opponents[:pool_size])
            return m1, m2
        else:
            pair = random.sample(movie_list, 2)
            return pair[0], pair[1]


def select_rank10_movies(movie_list, count=10, proximity_ratio=0.40):
    if len(movie_list) <= count:
        return list(movie_list)

    for item in movie_list:
        item[1] = AppState.elo.getPlayerRating(item[0])

    if random.random() < proximity_ratio:
        seed = random.choice(movie_list)
        sorted_by_dist = sorted(movie_list, key=lambda m: abs(m[1] - seed[1]))
        cluster_size = min(18, len(sorted_by_dist))
        cluster = sorted_by_dist[:cluster_size]
        return random.sample(cluster, count)
    else:
        return random.sample(movie_list, count)