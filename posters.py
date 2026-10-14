"""Poster overrides and on-demand metadata lookups, kept out of page rendering."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
from threading import BoundedSemaphore, Lock, RLock, Timer
from urllib.parse import urlencode, urlsplit

import requests

from config import CACHE_FILE, CUSTOM_POSTER_FILE, MAX_POSTER_BYTES, POSTER_UPLOAD_DIR
from elo_engine import parse_title_and_year
from state import AppState

FALLBACK_POSTER = '/static/poster-fallback.svg'
_store_lock = RLock()
_lookup_slots = BoundedSemaphore(8)
_lookup_locks = {}
_save_timer = None
UPLOAD_NAME = re.compile(r'^[a-f0-9]{64}\.(?:png|jpg|gif|webp)$')


def poster_key(title, year=None):
    base, year = parse_title_and_year(title, year)
    return base.casefold(), year[:4] if year else ''


def _read_mapping(filename):
    path = Path(filename)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return {(base.casefold(), '' if year in ('None', '') else year): value
                for key, value in data.items()
                if isinstance(value, str) and '|||' in key
                for base, year in [key.rsplit('|||', 1)]}
    except (OSError, ValueError, AttributeError):
        return {}


def _write_mapping(filename, mapping):
    path = Path(filename)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps({f'{base}|||{year}': url for (base, year), url in mapping.items()}, indent=2), encoding='utf-8')
    temporary.replace(path)


def load_poster_cache():
    with _store_lock:
        AppState.poster_cache = _read_mapping(CACHE_FILE)
        AppState.custom_posters = _read_mapping(CUSTOM_POSTER_FILE)


def save_poster_cache():
    global _save_timer
    with _store_lock:
        if _save_timer is not None:
            _save_timer.cancel()
            _save_timer = None
        try:
            _write_mapping(CACHE_FILE, AppState.poster_cache)
        except OSError as error:
            print(f'Could not save poster cache: {error}')


def _queue_cache_save():
    global _save_timer
    with _store_lock:
        if _save_timer is None:
            _save_timer = Timer(.5, save_poster_cache)
            _save_timer.daemon = True
            _save_timer.start()


def get_custom_poster(title, year=None):
    with _store_lock:
        return AppState.custom_posters.get(poster_key(title, year))


def _cached_poster(key):
    custom = AppState.custom_posters.get(key)
    if custom:
        return custom
    cached = AppState.poster_cache.get(key)
    if cached and 'via.placeholder.com' in cached:
        return FALLBACK_POSTER
    return cached


def get_poster_src(movie_title, api_key, release_year=None):
    """Return an image source immediately; the browser resolves uncached posters."""
    key = poster_key(movie_title, release_year)
    with _store_lock:
        cached = _cached_poster(key)
    if cached:
        return cached
    if not api_key:
        return FALLBACK_POSTER
    return '/poster?' + urlencode({'title': movie_title})


def get_poster_url(movie_title, api_key, release_year=None):
    key = poster_key(movie_title, release_year)
    with _store_lock:
        cached = _cached_poster(key)
        if cached:
            return cached
        lookup_lock = _lookup_locks.setdefault(key, Lock())
    with lookup_lock:
        with _store_lock:
            cached = _cached_poster(key)
            if cached:
                return cached
        result = FALLBACK_POSTER
        base, _ = parse_title_and_year(movie_title, release_year)
        params = {'api_key': api_key, 'query': base}
        if key[1]:
            params['primary_release_year'] = key[1]
        if api_key:
            try:
                with _lookup_slots:
                    response = requests.get('https://api.themoviedb.org/3/search/movie', params=params, timeout=(1.5, 3))
                    response.raise_for_status()
                    matches = response.json().get('results', [])
                with_posters = [movie for movie in matches if movie.get('poster_path')]
                exact = next((movie for movie in with_posters if key[0] in (movie.get('title', '').casefold(), movie.get('original_title', '').casefold())), None)
                chosen = exact or (with_posters[0] if with_posters else None)
                if chosen:
                    result = 'https://image.tmdb.org/t/p/w342' + chosen['poster_path']
            except (requests.RequestException, ValueError, TypeError, AttributeError):
                pass
        with _store_lock:
            AppState.poster_cache[key] = result

            result = _cached_poster(key)
        _queue_cache_save()
        return result


def prefetch_posters(movie_list, api_key):
    """Compatibility helper for callers that explicitly want a synchronous prefetch."""
    if not api_key:
        return
    missing = []
    with _store_lock:
        for movie in movie_list:
            if not _cached_poster(poster_key(movie[0], movie[2])):
                missing.append(movie)
    if missing:
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(lambda movie: get_poster_url(movie[0], api_key, movie[2]), missing))
        save_poster_cache()


def _image_extension(content):
    if len(content) >= 33 and content.startswith(b'\x89PNG\r\n\x1a\n') and content[12:16] == b'IHDR':
        return 'png'
    if len(content) >= 12 and content.startswith(b'\xff\xd8\xff') and content.endswith(b'\xff\xd9'):
        return 'jpg'
    if len(content) >= 14 and content[:6] in (b'GIF87a', b'GIF89a') and content.endswith(b';'):
        return 'gif'
    if len(content) >= 20 and content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return 'webp'
    raise ValueError('Choose a PNG, JPEG, GIF, or WebP image.')


def save_custom_poster(title, year=None, *, content=None, url=''):
    key = poster_key(title, year)
    if content:
        if len(content) > MAX_POSTER_BYTES:
            raise ValueError('Choose an image smaller than 8 MB.')
        extension = _image_extension(content)
        filename = hashlib.sha256(content).hexdigest() + '.' + extension
        directory = Path(POSTER_UPLOAD_DIR)
        directory.mkdir(parents=True, exist_ok=True)
        image_path = directory / filename
        if not image_path.exists():
            image_path.write_bytes(content)
        selected = f'/posters/{filename}'
    else:
        selected = url.strip()
        try:
            parsed = urlsplit(selected)
            valid = parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password
        except ValueError:
            valid = False
        if not valid or any(character.isspace() for character in selected):
            raise ValueError('Enter a direct http:// or https:// image link, or upload a file.')
    with _store_lock:
        updated = dict(AppState.custom_posters)
        updated[key] = selected
        _write_mapping(CUSTOM_POSTER_FILE, updated)
        old = AppState.custom_posters.get(key)
        AppState.custom_posters = updated
        _remove_unused_upload(old)
    return selected


def _remove_unused_upload(url):
    if url and url.startswith('/posters/') and url not in AppState.custom_posters.values():
        filename = url.removeprefix('/posters/')
        if UPLOAD_NAME.fullmatch(filename):
            (Path(POSTER_UPLOAD_DIR) / filename).unlink(missing_ok=True)


def reset_custom_poster(title, year=None):
    with _store_lock:
        key = poster_key(title, year)
        updated = dict(AppState.custom_posters)
        old = updated.pop(key, None)
        _write_mapping(CUSTOM_POSTER_FILE, updated)
        AppState.custom_posters = updated
        _remove_unused_upload(old)
