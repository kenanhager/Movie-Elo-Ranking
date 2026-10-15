from collections import Counter, deque
from functools import lru_cache
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
    """Reuse distributions until films, Elo, original ratings, or overrides change."""
    movies = tuple(tuple(movie[:3]) for movie in sorted(movie_list, key=lambda movie: movie[1], reverse=True))
    original = tuple((key, tuple(values)) for key, values in sorted(ratings_map.items()))
    imported = tuple((key, tuple(values)) for key, values in sorted(AppState.imported_methods.items()))
    exact, optimal, exact_counts, optimal_counts = _cached_doc3_methods(movies, original, tuple(ratings_list), imported)

    return dict(exact), dict(optimal), list(exact_counts), list(optimal_counts)


def _minimum_deviation_sequence(old_ratings, levels, max_span):
    """Compute the same bounded L1 cutoffs in O(films × rating levels).

    Prefix costs turn each segment cost into a subtraction. A sliding minimum
    selects its predecessor without trying every possible segment length.
    Equal candidates retain the earliest predecessor, as in the original DP.
    """
    count = len(old_ratings)
    previous = [0.0] + [math.inf] * count
    parents = []
    for rating in levels:
        prefix = [0.0]
        for old in old_ratings:
            prefix.append(prefix[-1] + abs(old - rating))
        current = [math.inf] * (count + 1)
        parent = [0] * (count + 1)
        candidates = deque()
        for end in range(count + 1):
            while candidates and candidates[0][0] < end - max_span:
                candidates.popleft()
            if math.isfinite(previous[end]):
                cost = previous[end] - prefix[end]
                while candidates and candidates[-1][1] > cost:
                    candidates.pop()
                candidates.append((end, cost))
            if candidates:
                start, cost = candidates[0]
                current[end] = cost + prefix[end]
                parent[end] = start
        previous = current
        parents.append(parent)
    sequence = [0.0] * count
    end = count
    for index in range(len(levels) - 1, -1, -1):
        start = parents[index][end]
        sequence[start:end] = [levels[index]] * (end - start)
        end = start
    return sequence


@lru_cache(maxsize=2)
def _cached_doc3_methods(movies, original, ratings, imported):
    if not movies:
        return {}, {}, [0] * 10, [0] * 10
    count = len(movies)
    default_levels = [5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0, .5]
    clean = []
    for value in ratings:
        try:
            value = float(value)
            if math.isfinite(value) and value <= 5:
                clean.append(round(value * 2) / 2)
        except (ValueError, TypeError, OverflowError):
            continue
    if not clean:
        clean = (default_levels * (count // 10 + 1))[:count]
    frequencies = Counter(clean)
    exact_sequence = [rating for rating in sorted(frequencies, reverse=True) for _ in range(frequencies[rating])]
    exact = {movie[0].lower(): exact_sequence[min(index, len(exact_sequence) - 1)] for index, movie in enumerate(movies)}
    overrides = dict(imported)
    movie_overrides = []
    for movie in movies:
        base, _ = parse_title_and_year(movie[0], movie[2] if len(movie) > 2 else '')
        movie_overrides.append(overrides.get(movie[0].lower()) or overrides.get(base.lower()))
    if all(override and override[1] is not None for override in movie_overrides):

        optimal_sequence = [override[1] for override in movie_overrides]
    else:
        average = sum(clean) / len(clean)
        original_map = {key: deque(values) for key, values in original}
        old = []
        for movie in movies:
            base, _ = parse_title_and_year(movie[0], movie[2] if len(movie) > 2 else '')
            values = original_map.get(movie[0].lower()) or original_map.get(base.lower())
            old.append(values.popleft() if values else average)
        levels = sorted(set(clean), reverse=True)
        max_span = max(60, int(count * .25))


        if len(levels) * max_span < count:
            max_span = count
        optimal_sequence = _minimum_deviation_sequence(old, levels, max_span)
    optimal = {}
    for index, movie in enumerate(movies):
        key = movie[0].lower()
        optimal[key] = optimal_sequence[index]
        override = movie_overrides[index]
        if override:
            if override[0] is not None:
                exact[key] = override[0]
            if override[1] is not None:
                optimal[key] = override[1]
    exact_counts, optimal_counts = [0] * 10, [0] * 10
    for movie in movies:
        key = movie[0].lower()
        exact_counts[rating_to_bin_idx(exact[key])] += 1
        optimal_counts[rating_to_bin_idx(optimal[key])] += 1
    return exact, optimal, exact_counts, optimal_counts


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
