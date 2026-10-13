from elopy import Implementation


class AppState:
    movie_elo = []
    elo = Implementation()
    poster_cache = {}
    imported_methods = {}  # {title_lower: (method1_rating, method2_rating)}