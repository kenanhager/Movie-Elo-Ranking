from elopy import Implementation
from threading import RLock


class AppState:
    movie_elo = []
    elo = Implementation()
    poster_cache = {}
    custom_posters = {}
    vote_history = []
    processed_vote_ids = []
    lock = RLock()
    imported_methods = {}
