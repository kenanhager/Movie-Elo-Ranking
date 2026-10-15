import json
import math
from html import escape
from urllib.parse import quote, urlencode
from uuid import uuid4

from config import NORMAL_BIN_BOUNDS, TEXT_CONTENT, TMDB_API_KEY
from data_manager import compute_doc3_methods, get_movie_original_ratings
from posters import get_poster_src, get_custom_poster
from elo_engine import get_elo_matched_pair, get_normal_bin_info, rating_to_bin_idx, select_rank10_movies
from state import AppState
from ui import empty_page, empty_state, header_nav, icon, movie_card, page as render_page, poster, safe_return_path, movie_anchor, movie_link


def generate_header_nav(active="rankings", query_val=""):
    return header_nav(active, query_val)


def _refresh_rankings():
    for item in AppState.movie_elo:
        item[1] = AppState.elo.getPlayerRating(item[0])
    AppState.movie_elo.sort(key=lambda movie: movie[1], reverse=True)


def _distribution():
    values = [movie[1] for movie in AppState.movie_elo]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return mean, math.sqrt(variance) if variance > 0 else 1.0


def _view_toggle():
    return f'<div class="view-toggle" role="group" aria-label="Collection layout"><button class="icon-button" data-view="grid" aria-label="Poster grid" aria-pressed="true">{icon("grid")}</button><button class="icon-button" data-view="list" aria-label="Film list" aria-pressed="false">{icon("list")}</button></div>'


def generate_gallery_html(api_key=TMDB_API_KEY, page=1, per_page=100):
    _refresh_rankings()
    total_movies = len(AppState.movie_elo)
    total_pages = max(1, math.ceil(total_movies / per_page))
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    page_movies = AppState.movie_elo[start_idx:start_idx + per_page]
    cards = "".join(movie_card(start_idx + i + 1, item[0], item[2], item[1], get_poster_src(item[0], api_key, item[2]), return_to=f'/?page={page}') for i, item in enumerate(page_movies))
    if not cards:
        cards = empty_state("No films in your collection", "Import your Letterboxd ratings or add a film to start ranking.")
    mean_elo = sum(movie[1] for movie in AppState.movie_elo) / total_movies if total_movies else None
    top_movie = AppState.movie_elo[0] if total_movies else None
    top_html = f'<a class="metric-value top-film-value" data-movie-link href="{escape(movie_link(top_movie[0], f'/?page={page}#' + movie_anchor(top_movie[0], top_movie[2])), quote=True)}">{escape(str(top_movie[0]))} {icon("arrow")}</a>' if top_movie else '<span class="metric-value top-film-value">No films yet</span>'
    hero_actions = f'<div class="hero-actions"><a class="button primary" href="/vote">{icon("vote")}Start a matchup</a><a class="button secondary" href="/rank10">{icon("rank")}Rank a cluster</a><a class="button secondary" href="/help">{icon("help")}How to use</a></div>'
    pagination = ""
    if total_movies:
        previous = f'<a class="button secondary" href="/?page={page - 1}">{icon("left")}Previous</a>' if page > 1 else f'<span class="button disabled" aria-disabled="true">{icon("left")}Previous</span>'
        next_link = f'<a class="button secondary" href="/?page={page + 1}">Next{icon("arrow")}</a>' if page < total_pages else f'<span class="button disabled" aria-disabled="true">Next{icon("arrow")}</span>'
        pagination = f'<nav class="pagination" aria-label="Collection pages">{previous}<span class="page-info">{start_idx + 1}–{min(start_idx + per_page, total_movies)} of {total_movies} films · Page {page} of {total_pages}</span>{next_link}</nav>'
    mean_html = f'{mean_elo:,.1f}' if mean_elo is not None else '—'
    content = f"""
    <section class="collection-summary" aria-label="Collection overview">
        <div class="collection-stat"><span class="metric-label">Films in your collection</span><span class="metric-value">{total_movies:,}</span></div>
        <div class="collection-stat"><span class="metric-label">Average Elo rating</span><span class="metric-value">{mean_html}<small>Elo</small></span></div>
        <div class="collection-stat"><span class="metric-label">At the top of your list</span>{top_html}</div>
    </section>
    <section aria-label="Film rankings"><div class="section-toolbar"><div class="section-title"><h2>Your rankings</h2><span class="count-pill">{total_movies} films</span></div><div class="toolbar-controls"><span class="sort-label">Highest Elo first ↓</span>{_view_toggle()}</div></div>
        <div class="movie-grid">{cards}</div>{pagination}
    </section>"""
    title_lead, separator, title_tail = TEXT_CONTENT['gallery_title'].partition(', ')
    heading = f'{escape(title_lead)},<br><em>{escape(title_tail)}</em>' if separator else escape(title_lead)
    return render_page(heading, TEXT_CONTENT['gallery_subtitle'], 'rankings', content, hero_extra=hero_actions)


def generate_rank10_html(api_key=TMDB_API_KEY):
    count = min(10, len(AppState.movie_elo))
    if count < 2:
        return empty_page('rank10', TEXT_CONTENT['rank10_title'], 'Add at least two films to start ranking a cluster.')
    cluster = select_rank10_movies(AppState.movie_elo, count=count, proximity_ratio=0.70)
    cluster.sort(key=lambda movie: movie[1], reverse=True)
    items = ""
    for index, movie in enumerate(cluster):
        title, rating, year = movie[:3]
        items += f"""<li class="rank-item" draggable="true" data-title="{escape(str(title), quote=True)}">
            <div class="rank-num">{index + 1:02d}</div>{poster(get_poster_src(title, api_key, year), title)}
            <div class="item-info"><div class="item-title">{escape(str(title))}<span class="item-year">{escape(str(year)) if year else ''}</span></div><div class="item-elo">{rating:,.1f} Elo</div></div>
            <div class="btn-group"><button type="button" class="btn-move" data-move="up" aria-label="Move {escape(str(title), quote=True)} up">{icon('up')}</button><button type="button" class="btn-move" data-move="down" aria-label="Move {escape(str(title), quote=True)} down">{icon('down')}</button></div></li>"""
    content = f"""<div class="rank-container"><div class="rank-intro"><span>YOUR ORDER · BEST TO WORST</span><span>{count * (count - 1) // 2} pairwise comparisons</span></div>
        <form id="ranking-form" action="/rank10" method="GET"><ol id="rank-list" class="rank-list">{items}</ol>
        <div class="submit-container"><button type="submit" class="button primary">{icon('check')}{TEXT_CONTENT['rank10_submit_btn']}</button><a class="button secondary" href="/rank10">{TEXT_CONTENT['rank10_skip_btn']}{icon('arrow')}</a></div></form></div>"""
    return render_page(TEXT_CONTENT['rank10_title'], TEXT_CONTENT['rank10_subtitle'].format(count=count), 'rank10', content)


def generate_vote_html(api_key=TMDB_API_KEY, target_title=None, pair_titles=None, message='', error=False):
    if len(AppState.movie_elo) < 2:
        return empty_page('vote', TEXT_CONTENT['vote_title'], 'Add at least two films to begin head-to-head matchups.')
    _refresh_rankings()
    target_movie = next((movie for movie in AppState.movie_elo if target_title and movie[0].lower() == target_title.lower()), None)
    pair = [next((movie for movie in AppState.movie_elo if movie[0] == title), None) for title in (pair_titles or [])]
    if len(pair) == 2 and all(pair) and pair[0][0] != pair[1][0]:
        m1, m2 = pair
    else:
        m1, m2 = get_elo_matched_pair(AppState.movie_elo, target_movie=target_movie, proximity_ratio=.75)
    if not m1 or not m2:
        return empty_page('vote', TEXT_CONTENT['vote_title'], 'Add at least two films to begin head-to-head matchups.')
    skip_query = f'/vote?target={quote(str(m1[0]), safe="")}' if target_movie else '/vote'
    spotlight = f'<div class="spotlight-banner"><span><strong>{TEXT_CONTENT["vote_spotlight_label"]}</strong> {escape(str(m1[0]))}</span><a href="/vote" class="exit-spotlight">Exit focused mode ×</a></div>' if target_movie else ''
    vote_id = uuid4().hex
    shared = ''.join(f'<input type="hidden" name="{name}" value="{escape(str(value), quote=True)}">' for name, value in {'m1': m1[0], 'm2': m2[0], 'vote_id': vote_id, 'target': target_title or ''}.items())
    def vote_form(option, label, css_class, symbol=''):
        return f'<form action="/vote" method="POST">{shared}<input type="hidden" name="winner" value="{option}"><button type="submit" class="button {css_class}">{label}{symbol}</button></form>'
    cards = []
    for option, movie in enumerate([m1, m2], 1):
        title, rating, year = movie[:3]
        cards.append(f"""<article class="vote-card">{'<span class="target-tag">IN FOCUS</span>' if target_movie and option == 1 else ''}
            {poster(get_poster_src(title, api_key, year), title, lazy=False)}<div class="vote-title">{escape(str(title))}</div>
            <div class="vote-meta"><span>{escape(str(year)) if year else 'Year unlisted'}</span><span>{rating:,.1f} Elo</span></div>
            {vote_form(option, 'Choose this film', 'primary full-width', icon('arrow'))}</article>""")
    latest = AppState.vote_history[-1] if AppState.vote_history else None
    undo_form = f'<form action="/vote/undo" method="POST"><input type="hidden" name="vote_id" value="{escape(latest["id"], quote=True) if latest else ""}"><button type="submit" class="button secondary" {"disabled" if not latest else ""}>{icon("undo")}Undo last vote</button></form>'
    status = f'<div class="status-msg {"error" if error else ""}" role="status">{escape(message)}</div>' if message else ''
    content = f"""{status}{spotlight}<div class="matchup-container">{cards[0]}<div class="vs" aria-hidden="true">vs.</div>{cards[1]}</div>
        <div class="controls">{vote_form(3, "It's a tie", 'secondary')}<a href="{skip_query}" class="button secondary">Skip this pair{icon('arrow')}</a>{undo_form}</div>"""
    return render_page(TEXT_CONTENT['vote_title'], 'Choose your favorite, mark a tie, or skip. Use Undo last vote to correct a choice.', 'vote', content)


def generate_bin_view_html(api_key=TMDB_API_KEY, bin_idx=0, method='norm'):
    _refresh_rankings()
    if not AppState.movie_elo:
        return empty_page('stats', 'Distribution bins', 'Add films to explore the ten rating distribution bins.')
    mean, std = _distribution()
    bin_idx = max(0, min(9, bin_idx))
    bin_num = bin_idx + 1
    ratings_map, ratings_list = get_movie_original_ratings()
    exact_map, optimal_map, _, _ = compute_doc3_methods(AppState.movie_elo, ratings_map, ratings_list)
    methods = {'norm': 'Standard normal', 'exact': 'Method 1 · Preserved counts', 'optimal': 'Method 2 · Optimal L1 cutoffs'}
    method = method if method in methods else 'norm'
    bin_label = NORMAL_BIN_BOUNDS[bin_idx][2].strip() if method == 'norm' else f'{0.5 + bin_idx * 0.5:.1f}★ level'
    selected = []
    for rank, movie in enumerate(AppState.movie_elo, 1):
        title, rating, year = movie[:3]
        z_score = (rating - mean) / std
        if method in ('exact', 'optimal'):
            assigned = (exact_map if method == 'exact' else optimal_map).get(title.lower(), 3.0)
            assigned_bin = rating_to_bin_idx(assigned)
            rating_text = f'{assigned:.1f}★ · {rating:,.1f} Elo'
        else:
            assigned_bin, _, _, _ = get_normal_bin_info(z_score)
            rating_text = f'{rating:,.1f} · {z_score:+.2f}σ'
        if assigned_bin == bin_idx:
            selected.append((rank, movie, rating_text))
    cards = ''.join(movie_card(rank, movie[0], movie[2], movie[1], get_poster_src(movie[0], api_key, movie[2]), rating_text, return_to=f'/bin?bin={bin_num}&method={method}') for rank, movie, rating_text in selected)
    if not cards:
        cards = empty_state('No films in this bin', 'No films are in this bin yet. Try another bin or refine your rankings.', actions=False)
    method_links = ''.join(f'<a href="/bin?bin={bin_num}&method={key}" class="dist-btn {"active-" + key if method == key else ""}" {"aria-current=page" if method == key else ""}>{label}</a>' for key, label in methods.items())
    bin_links = ''.join(f'<a href="/bin?bin={index + 1}&method={method}" class="bin-btn {"active" if bin_idx == index else ""}" {"aria-current=page" if bin_idx == index else ""}>Bin {index + 1}</a>' for index in range(10))
    content = f'<div class="bin-controls"><nav class="dist-toggle" aria-label="Distribution method">{method_links}</nav><nav class="bin-selector" aria-label="Rating bins">{bin_links}</nav></div><div class="section-toolbar"><div class="section-title"><h2>Films in this bin</h2><span class="count-pill">{len(selected)}</span></div>{_view_toggle()}</div><div class="movie-grid">{cards}</div>'
    return render_page(f'Bin {bin_num} <em>· {escape(bin_label)}</em>', f'{methods[method]} distribution · {len(selected)} films. Rankings reflect their position in your full collection.', 'stats', content, eyebrow='DISTRIBUTION EXPLORER')


def generate_search_html(api_key=TMDB_API_KEY, query=''):
    _refresh_rankings()
    matches = [(index + 1, movie) for index, movie in enumerate(AppState.movie_elo) if query.strip().lower() in movie[0].lower()]
    cards = ''.join(movie_card(rank, movie[0], movie[2], movie[1], get_poster_src(movie[0], api_key, movie[2]), return_to='/search?' + urlencode({'q': query})) for rank, movie in matches)
    if not matches:
        cards = empty_state('No matching films', f'No titles match “{query}”. Try a different search or add the film to your collection.')
    content = f'<div class="section-toolbar"><div class="section-title"><h2>Matching films</h2><span class="count-pill">{len(matches)}</span></div>{_view_toggle()}</div><div class="movie-grid">{cards}</div>'
    return render_page('Search results', f'{len(matches)} results for “{query}” in your collection.', 'search', content, query=query)


def _poster_editor(title, year, show_error=False, return_to='/'):
    custom = get_custom_poster(title, year)
    image_link = custom if custom and custom.startswith(('http://', 'https://')) else ''
    safe_title = escape(str(title), quote=True)
    return_field = f'<input type="hidden" name="return_to" value="{escape(safe_return_path(return_to), quote=True)}">'
    reset_form = f'<form action="/poster" method="POST" class="poster-reset">{return_field}<input type="hidden" name="title" value="{safe_title}"><input type="hidden" name="action" value="reset"><button type="submit" class="button secondary full-width">Use automatic poster</button></form>' if custom else ''
    return f"""<details class="poster-editor" {'open' if show_error else ''}><summary>{icon('film')}Change poster{icon('down')}</summary>
        <div class="poster-editor-body">
        <form action="/poster" method="POST" enctype="multipart/form-data" id="poster-form">{return_field}
            <input type="hidden" name="title" value="{safe_title}"><input type="hidden" name="action" value="save">
            <label for="poster-file">Upload an image</label><input type="file" id="poster-file" name="poster_file" accept="image/png,image/jpeg,image/gif,image/webp" aria-describedby="poster-help">
            <p class="poster-help" id="poster-help">PNG, JPEG, GIF, or WebP · up to 8 MB</p>
            <div class="poster-divider">or use an image link</div><label for="poster-url" class="sr-only">Direct image link</label><input type="url" id="poster-url" name="poster_url" placeholder="https://…/poster.jpg" value="{escape(image_link, quote=True)}">
            <div class="poster-preview" hidden><img id="poster-preview" alt="Custom poster preview"><span>Preview</span></div><p class="poster-feedback" id="poster-feedback" role="status"></p>
            <button type="submit" class="button primary full-width">{icon('check')}Save poster</button>
        </form>{reset_form}<p class="poster-help">Your choice applies everywhere in your collection.</p></div></details>"""


def generate_movie_detail_html(api_key=TMDB_API_KEY, title_query='', message='', poster_error=False, return_to='/'):
    _refresh_rankings()
    return_to = safe_return_path(return_to)
    back = f'<a href="{escape(return_to, quote=True)}" class="button secondary gallery-back" data-gallery-back>{icon("left")}Back to rankings</a>'
    target_movie = next((movie for movie in AppState.movie_elo if movie[0].lower() == title_query.lower()), None)
    if not target_movie:
        return render_page('Film not found', 'This film is not in your current collection.', 'detail', back + empty_state('Film not found', f'No film matches “{title_query}”.'))
    index = AppState.movie_elo.index(target_movie)
    rank, total = index + 1, len(AppState.movie_elo)
    title, elo_val, year = target_movie[:3]
    title_enc = quote(str(title), safe='')
    below = sum(movie[1] < elo_val for movie in AppState.movie_elo)
    tied = sum(movie[1] == elo_val for movie in AppState.movie_elo) - 1
    placement = 'Only film in collection' if total == 1 else 'Top 10% of your ranking' if rank / total <= .1 else 'Upper half of your ranking' if rank / total <= .5 else 'Lower half of your ranking'
    tie_note = f'<p class="profile-note">Shares its score with {tied} other {"film" if tied == 1 else "films"}.</p>' if tied else ''
    neighbors = ''
    for neighbor_index, label in [(index - 1, 'One place above'), (index + 1, 'One place below')]:
        if 0 <= neighbor_index < total:
            neighbor = AppState.movie_elo[neighbor_index]
            neighbors += f'<a class="neighbor-film" href="{escape(movie_link(neighbor[0], return_to), quote=True)}">{poster(get_poster_src(neighbor[0], api_key, neighbor[2]), neighbor[0])}<span><small>{label} · #{neighbor_index + 1}</small><strong>{escape(str(neighbor[0]))}</strong><span>{escape(str(neighbor[2])) if neighbor[2] else "Year unlisted"}</span></span>{icon("arrow")}</a>'
    nearby = f'<section class="nearby-section"><h2>Nearby in your ranking</h2><div class="neighbor-list">{neighbors}</div></section>' if neighbors else ''
    confirmation = escape(json.dumps(f'Remove “{title}” from your collection?'), quote=True)
    status = f'<div class="status-msg {"error" if poster_error else ""}" role="status">{escape(message)}</div>' if message else ''
    content = f"""{back}{status}<article class="detail-card"><div class="detail-poster">{poster(get_poster_src(title, api_key, year), title, lazy=False)}{_poster_editor(title, year, poster_error, return_to)}</div>
    <div class="detail-content"><h2 class="movie-title">{escape(str(title))}</h2><div class="movie-year">{f'Released in {escape(str(year))}' if year else 'Release year unlisted'}</div><span class="placement-label">{placement}</span>
    <section class="profile-insights" aria-label="Film ranking insights">
        <div class="profile-insight"><span>Collection rank</span><strong>#{rank:,}</strong><small>of {total:,} films</small></div>
        <div class="profile-insight"><span>Ranked above</span><strong>{below:,}</strong><small>{'other film' if below == 1 else 'other films'} in your collection</small></div>
        <div class="profile-insight"><span>Ranking score</span><strong>{elo_val:,.1f}</strong><small>Higher scores rank higher</small></div>
    </section>{tie_note}{nearby}
    <div class="action-buttons"><a href="/vote?target={title_enc}" class="button primary">{icon('vote')}Compare this film</a><a href="/delete?title={title_enc}" class="button danger" data-confirm="{confirmation}">{icon('trash')}Remove film</a></div></div></article>"""
    return render_page(TEXT_CONTENT['detail_title'], '', 'detail', content)


def generate_add_html():
    content = f"""<div class="panel form-container"><div class="panel-heading">{icon('plus')}<h2>Film details</h2></div>
    <form action="/add" method="GET"><div class="form-group"><label for="title">Film title <span>· Required</span></label><input type="text" id="title" name="title" placeholder="e.g. Inception" required></div>
    <div class="form-group"><label for="year">Release year <span>· Optional</span></label><input type="number" id="year" name="year" placeholder="e.g. 2000" min="1880" max="2030"></div>
    <div class="form-group"><label for="rating">Your initial rating <span>· Scale 1–10</span></label><div class="rating-box"><input type="number" id="rating" name="rating" min="0" max="100" step="0.1" value="7.0" required><output class="rating-val" id="val-disp" for="rating">7.0/10</output></div></div>
    <button type="submit" class="button primary full-width">{icon('plus')}{TEXT_CONTENT['add_btn']}</button><p class="form-note">Your rating becomes an initial Elo score. Matchups refine it over time.</p></form></div>"""
    return render_page(TEXT_CONTENT['add_title'], TEXT_CONTENT['add_subtitle'], 'add', content)


def generate_import_html(message=''):
    status = f'<div class="status-msg {"error" if message.startswith("Error") else ""}" role="status">{escape(message)}</div>' if message else ''
    content = f"""{status}<div class="data-layout"><section class="panel"><div class="panel-heading">{icon('data')}<h2>Import your films</h2></div>
    <p>Upload your Letterboxd ratings or a CSV of movie titles and ratings.</p>
    <form action="/import" method="post" enctype="multipart/form-data"><div class="upload-area">{icon('film')}<label for="csv_file">Choose your ratings CSV</label><input type="file" id="csv_file" name="csv_file" accept=".csv" required></div>
    <button type="submit" class="button primary full-width">{icon('data')}Upload & import</button><p class="form-note">New films are merged into your collection. Existing titles are retained.</p></form></section>
    <section class="panel"><div class="panel-heading">{icon('arrow')}<h2>Export your films</h2></div>
    <div class="export-box"><h3>Your complete film database</h3><p>Includes Elo, z-scores, and ratings for all three distribution methods.</p><form action="/export" method="GET"><input type="hidden" name="type" value="elo_data"><button type="submit" class="button secondary full-width">{icon('data')}Download elo_data.csv</button></form></div>
    <div class="export-box"><h3>Letterboxd ratings</h3><p>Format: <code>Date, Name, Year, Letterboxd URI, Rating</code>. Choose the distribution used for star ratings.</p>
    <form action="/export" method="GET"><input type="hidden" name="type" value="letterboxd"><label for="method">Rating method</label><select id="method" name="method"><option value="norm">Standard normal bin scale</option><option value="exact">Method 1: Preserved count distribution</option><option value="optimal">Method 2: Optimal L1 DP cutoffs</option></select><button type="submit" class="button secondary full-width">{icon('data')}Download Letterboxd_data.csv</button></form></div></section></div>"""
    return render_page(TEXT_CONTENT['import_title'], TEXT_CONTENT['import_subtitle'], 'import', content)


def generate_stats_html():
    _refresh_rankings()
    total = len(AppState.movie_elo)
    if not total:
        return empty_page('stats', TEXT_CONTENT['stats_title'], 'Your ratings tell a story. Add films to see their distribution here.')
    mean, std = _distribution()
    norm_counts = [0] * 10
    samples = [[] for _ in range(10)]
    for movie in AppState.movie_elo:
        index, _, _, _ = get_normal_bin_info((movie[1] - mean) / std)
        norm_counts[index] += 1
        if len(samples[index]) < 3:
            samples[index].append(movie[0])
    ratings_map, ratings_list = get_movie_original_ratings()
    _, _, exact_counts, optimal_counts = compute_doc3_methods(AppState.movie_elo, ratings_map, ratings_list)
    theoretical = [0.0228, 0.0440, 0.0918, 0.1498, 0.1916, 0.1916, 0.1498, 0.0918, 0.0440, 0.0228]
    expected = [fraction * total for fraction in theoretical]
    max_count = max(*norm_counts, *exact_counts, *optimal_counts, *expected, 1)
    bars, rows = '', ''
    for index in range(10):
        number = index + 1
        bar_links = ''
        table_links = ''
        for method, counts in [('norm', norm_counts), ('exact', exact_counts), ('optimal', optimal_counts)]:
            count = counts[index]
            height = max(4, int(count / max_count * 220))
            bar_links += f'<a class="bar bar-{method}" style="height:{height}px" href="/bin?bin={number}&method={method}" aria-label="{method}, bin {number}: {count} films" title="{method}, bin {number}: {count} films"><span class="bar-count">{count if count else ""}</span></a>'
            table_links += f'<td><a class="{method}" href="/bin?bin={number}&method={method}">{count} ({count / total * 100:.1f}%)</a></td>'
        bars += f'<div class="bar-column"><div class="bar-wrapper"><div class="ideal-line" style="bottom:{int(expected[index] / max_count * 220)}px" title="Expected: {expected[index]:.1f} films"></div>{bar_links}</div><a class="bar-label" href="/bin?bin={number}&method=norm">Bin {number} ↗</a><div class="bar-sublabel">{escape(NORMAL_BIN_BOUNDS[index][2].strip())}</div></div>'
        sample_text = ', '.join(escape(str(title)) for title in samples[index]) if samples[index] else '<em>No films</em>'
        rows += f'<tr><td><a href="/bin?bin={number}&method=norm">Bin {number} ↗</a><div class="stat-caption">{escape(NORMAL_BIN_BOUNDS[index][2].strip())}</div></td>{table_links}<td>{expected[index]:.1f} ({theoretical[index] * 100:.1f}%)</td><td class="sample-movies">{sample_text}<br><a href="/bin?bin={number}&method=norm">Explore films →</a></td></tr>'
    content = f"""<section class="stats-summary" aria-label="Collection statistics"><div class="stat-card"><div class="label">Films in collection</div><div class="val">{total:,}</div></div><div class="stat-card"><div class="label">Mean Elo</div><div class="val">{mean:,.1f}</div></div><div class="stat-card"><div class="label">Standard deviation · σ</div><div class="val">{std:,.1f}</div></div></section>
    <section class="panel chart-card"><div class="chart-title">{TEXT_CONTENT['stats_chart_title']}</div><p class="chart-desc">{TEXT_CONTENT['stats_chart_desc']}</p><div class="legend"><span class="legend-item"><i class="legend-box"></i>Standard normal · σ</span><span class="legend-item"><i class="legend-box exact"></i>Method 1 · Preserved counts</span><span class="legend-item"><i class="legend-box optimal"></i>Method 2 · Optimal L1 cutoffs</span></div><div class="chart-scroll" tabindex="0" role="region" aria-label="Rating distribution chart; scroll horizontally on small screens"><div class="histogram">{bars}</div></div></section>
    <section class="panel table-card" tabindex="0" aria-label="Bin breakdown; scroll horizontally on small screens"><h2>The details, bin by bin</h2><table><caption class="sr-only">Film counts for each distribution method and expected normal distribution</caption><thead><tr><th scope="col">Rating bin</th><th scope="col">Standard normal</th><th scope="col">Preserved counts</th><th scope="col">Optimal L1</th><th scope="col">Expected</th><th scope="col">A few films</th></tr></thead><tbody>{rows}</tbody></table></section>"""
    return render_page(TEXT_CONTENT['stats_title'], TEXT_CONTENT['stats_subtitle'], 'stats', content)


def generate_help_html():
    steps = [
        ('Import or add films', 'Open Import & export and upload your Letterboxd ratings.csv or a CSV with title, year, and rating columns. You can also add individual films from Add a film.', '/import', 'Import ratings'),
        ('Refine rankings with match voting', 'Choose the better of two films. Both scores update after each choice. Mark a tie if you like them equally, or skip to leave both scores unchanged. Undo last vote restores both previous scores and shows the same pair again.', '/vote', 'Start voting'),
        ('Order several films at once', 'Rank a cluster selects up to ten films with similar scores. Drag them or use the arrows, with your favorite first. Save ranking updates their scores from your chosen order.', '/rank10', 'Rank a cluster'),
        ('Browse and compare your collection', 'Rankings shows films from highest to lowest score. Switch between posters and a list, or search for a title. A film profile shows its rank, the films it outranks, and nearby titles. Back to rankings returns to the same page, layout, and scroll position.', '/', 'View rankings'),
        ('Choose a custom poster', 'Open a film profile and expand Change poster. Upload a PNG, JPEG, GIF, or WebP up to 8 MB, or enter a direct image link. Save poster applies it across the app. Use automatic poster restores the default artwork.', '/', 'Choose a film'),
        ('Export or explore your ratings', 'Import & export downloads your full ranking data or Letterboxd star ratings. Analytics contains the detailed distribution methods and filters; these calculations stay out of individual film profiles.', '/import', 'Export ratings'),
    ]
    items = ''.join(f'<li class="guide-step"><span class="guide-number">{index:02d}</span><div><h2>{heading}</h2><p>{description}</p><a class="guide-link" href="{url}">{label}{icon("arrow")}</a></div></li>' for index, (heading, description, url, label) in enumerate(steps, 1))
    content = f'<ol class="guide-steps">{items}</ol><section class="panel guide-notes"><h2>About scores and undo</h2><p>Ranking scores are relative to your collection. Use the rank and nearby titles to judge whether a film is placed correctly. Your imported ratings provide a starting point; comparisons refine the order.</p><p>You can undo the last 100 match votes, newest first, including after restarting the app. Importing data, adding or removing films, or saving a cluster starts a new undo history.</p><p>Your rankings and uploaded posters are saved on this device.</p></section>'
    return render_page('How to use', 'Set up your collection, refine the order, and manage your films.', 'help', content)
