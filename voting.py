import json
import math
from pathlib import Path
from uuid import uuid4

from config import VOTE_HISTORY_FILE
from data_manager import save_to_csv
from state import AppState


def load_vote_history():
    AppState.vote_history = []
    AppState.processed_vote_ids = []
    path = Path(VOTE_HISTORY_FILE)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        history = data.get('history', [])[-100:]
        for entry in history:
            if not isinstance(entry['id'], str) or len(entry['before']) != 2 or set(entry['before']) != set(entry['after']):
                return
            if entry['m1'] == entry['m2'] or set((entry['m1'], entry['m2'])) != set(entry['before']):
                return
            if not all(isinstance(value, (float, int)) and math.isfinite(value) for values in (entry['before'], entry['after']) for value in values.values()):
                return
        if history and any(AppState.elo.players.get(title) != rating for title, rating in history[-1]['after'].items()):
            return
        AppState.vote_history = history
        AppState.processed_vote_ids = [value for value in data.get('processed', [])[-1000:] if isinstance(value, str)]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass


def _write_history(history, processed):
    path = Path(VOTE_HISTORY_FILE)
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps({'history': history, 'processed': processed}), encoding='utf-8')
    temporary.replace(path)


def clear_vote_history():
    if AppState.vote_history:
        _write_history([], AppState.processed_vote_ids)
        AppState.vote_history = []


def _commit(history, processed, previous_ratings):
    try:
        save_to_csv()
        _write_history(history, processed)
    except OSError:
        AppState.elo.players.update(previous_ratings)
        save_to_csv()
        raise
    AppState.vote_history = history
    AppState.processed_vote_ids = processed


def record_vote(first, second, winner, target=None, vote_id=None):
    if first == second or first not in AppState.elo.players or second not in AppState.elo.players or winner not in ('1', '2', '3'):
        raise ValueError('Choose two different films from your collection.')
    vote_id = vote_id or uuid4().hex
    if vote_id in AppState.processed_vote_ids:
        return False
    before = {title: AppState.elo.players[title] for title in (first, second)}
    AppState.elo.recordMatch(first, second, winner=first if winner == '1' else second if winner == '2' else None, draw=winner == '3')
    entry = {'id': vote_id, 'm1': first, 'm2': second, 'target': target, 'before': before, 'after': {title: AppState.elo.players[title] for title in (first, second)}}
    _commit((AppState.vote_history + [entry])[-100:], (AppState.processed_vote_ids + [vote_id])[-1000:], before)
    return True


def undo_vote(vote_id):
    if not AppState.vote_history:
        raise ValueError('There are no match votes to undo.')
    latest = AppState.vote_history[-1]
    if latest['id'] != vote_id:
        raise ValueError('That vote has already been undone, or a newer vote has been saved.')
    if any(AppState.elo.players.get(title) != rating for title, rating in latest['after'].items()):
        clear_vote_history()
        raise ValueError('These ratings have changed since the vote. Undo is no longer available.')
    AppState.elo.players.update(latest['before'])
    _commit(AppState.vote_history[:-1], AppState.processed_vote_ids, latest['after'])
    return latest
