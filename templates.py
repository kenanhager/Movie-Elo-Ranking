import math
import urllib.parse

from config import (
    NORMAL_BIN_BOUNDS,
    TEXT_CONTENT,
    TMDB_API_KEY,
    get_color_css,
)
from data_manager import (
    compute_doc3_methods,
    get_movie_original_ratings,
    get_poster_url,
    prefetch_posters,
)
from elo_engine import (
    get_elo_matched_pair,
    get_normal_bin_info,
    normal_cdf,
    rating_to_bin_idx,
    select_rank10_movies,
)
from state import AppState


def generate_header_nav(active="rankings", query_val=""):
    return f"""
    <div class="nav-bar">
        <a href="/" class="nav-link {'active' if active == 'rankings' else ''}">Rankings Gallery</a>
        <a href="/vote" class="nav-link {'active' if active == 'vote' else ''}">Match Voting</a>
        <a href="/rank10" class="nav-link {'active' if active == 'rank10' else ''}">Rank 10 Cluster</a>
        <a href="/add" class="nav-link {'active' if active == 'add' else ''}">+ Add Movie</a>
        <a href="/stats" class="nav-link {'active' if active == 'stats' else ''}">Distribution Analytics</a>
        <a href="/import" class="nav-link {'active' if active == 'import' else ''}">CSV Management</a>
        <form action="/search" method="GET" class="search-form">
            <input type="text" name="q" placeholder="{TEXT_CONTENT['search_placeholder']}" value="{query_val}" required class="search-input">
            <button type="submit" class="search-btn">{TEXT_CONTENT['search_btn']}</button>
        </form>
    </div>
    """


def generate_gallery_html(api_key=TMDB_API_KEY, page=1, per_page=100):
    for item in AppState.movie_elo:
        item[1] = AppState.elo.getPlayerRating(item[0])
    AppState.movie_elo.sort(key=lambda x: x[1], reverse=True)

    total_movies = len(AppState.movie_elo)
    total_pages = max(1, math.ceil(total_movies / per_page))
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_movies)
    page_movies = AppState.movie_elo[start_idx:end_idx]

    prefetch_posters(page_movies, api_key)

    cards_html = ""
    for i, item in enumerate(page_movies):
        rank = start_idx + i + 1
        title = item[0]
        rating = item[1]
        date = item[2]
        poster_url = get_poster_url(title, api_key, date)
        date_html = f'<div class="year">({date})</div>' if date else ""
        title_enc = urllib.parse.quote(str(title))

        cards_html += f"""
        <div class="card">
            <div class="badge">#{rank}</div>
            <a href="/movie?title={title_enc}">
                <img src="{poster_url}" alt="{title}" loading="lazy">
            </a>
            <div class="title">{title}</div>
            {date_html}
            <div class="rating">Elo: {rating:.1f}</div>
            <div class="card-actions">
                <a href="/vote?target={title_enc}" class="card-btn btn-sub" title="Vote Matchup">🎯</a>
                <a href="/movie?title={title_enc}" class="card-btn btn-stats" title="View Stats">📊</a>
                <a href="/delete?title={title_enc}" class="card-btn btn-danger" onclick="return confirm('Are you sure you want to delete {title}?');" title="Delete">🗑️</a>
            </div>
        </div>
        """

    prev_btn = f'<a href="/?page={page - 1}" class="btn">← Previous</a>' if page > 1 else '<span class="btn disabled">← Previous</span>'
    next_btn = f'<a href="/?page={page + 1}" class="btn">Next →</a>' if page < total_pages else '<span class="btn disabled">Next →</span>'

    pagination_html = f"""
    <div class="pagination">
        {prev_btn}
        <span class="page-info">Page {page} of {total_pages} ({total_movies} Movies Total)</span>
        {next_btn}
    </div>
    """

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{TEXT_CONTENT['gallery_title']}</title>
    <style>
        {get_color_css()}
        .grid {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; margin-top: 20px; }}
        .card {{ 
            position: relative; background: var(--bg-card); padding: 10px; border-radius: 12px; 
            width: 185px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.5); 
            transition: transform 0.2s ease, border-color 0.2s ease; border: 1px solid var(--border-color);
            display: flex; flex-direction: column; justify-content: space-between;
        }}
        .card:hover {{ transform: translateY(-4px); border-color: var(--accent-magenta); }}
        .badge {{ position: absolute; top: 15px; left: 15px; background: rgba(15, 6, 23, 0.85); color: var(--accent-pink); font-weight: bold; font-size: 13px; padding: 4px 8px; border-radius: 6px; border: 1px solid var(--accent-pink); z-index: 2; }}
        .card img {{ width: 100%; height: 278px; object-fit: cover; border-radius: 8px; background: var(--bg-input); cursor: pointer; }}
        .title {{ font-size: 14px; font-weight: bold; margin-top: 8px; word-wrap: break-word; color: var(--text-primary); }}
        .year {{ font-size: 12px; color: var(--text-secondary); margin-top: 2px; }}
        .rating {{ font-size: 13px; color: var(--accent-pink); font-weight: bold; margin-top: 4px; }}
        .card-actions {{ display: flex; gap: 5px; margin-top: 10px; justify-content: center; }}
        .card-btn {{ font-size: 13px; font-weight: bold; padding: 5px 8px; border-radius: 6px; text-decoration: none; flex: 1; text-align: center; }}
        .btn-sub {{ background: var(--accent-dark-plum); color: var(--accent-pink); border: 1px solid var(--accent-pink); }}
        .btn-sub:hover {{ background: var(--accent-pink); color: #000; }}
        .btn-stats {{ background: var(--bg-input); color: var(--text-secondary); border: 1px solid var(--border-color); }}
        .btn-stats:hover {{ background: var(--accent-plum); color: #fff; }}
        .btn-danger {{ background: var(--btn-danger-bg); color: #ff6b81; border: 1px solid var(--btn-danger); }}
        .btn-danger:hover {{ background: var(--btn-danger); color: white; }}
        .pagination {{ display: flex; justify-content: center; align-items: center; gap: 15px; margin: 25px 0; }}
        .btn {{ padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: bold; background-color: var(--accent-magenta); color: white; transition: background 0.2s; }}
        .btn:hover {{ background-color: var(--accent-pink); color: #000; }}
        .btn.disabled {{ background-color: var(--bg-input); color: #777; cursor: not-allowed; }}
        .page-info {{ font-size: 15px; color: var(--text-secondary); }}
    </style>
</head>
<body>
    <h1>{TEXT_CONTENT['gallery_title']}</h1>
    <p class="subtitle">{TEXT_CONTENT['gallery_subtitle']}</p>
    {generate_header_nav("rankings")}
    {pagination_html}
    <div class="grid">{cards_html}</div>
    {pagination_html}
</body>
</html>
"""


def generate_rank10_html(api_key=TMDB_API_KEY):
    count = min(10, len(AppState.movie_elo))
    if count < 2:
        return "<h1>Not enough movies to rank!</h1>"

    cluster_sample = select_rank10_movies(AppState.movie_elo, count=count, proximity_ratio=0.70)
    cluster_sample.sort(key=lambda x: x[1], reverse=True)

    prefetch_posters(cluster_sample, api_key)

    list_items_html = ""
    for idx, movie in enumerate(cluster_sample):
        title = movie[0]
        rating = movie[1]
        date = movie[2]
        poster_url = get_poster_url(title, api_key, date)
        date_html = f'<span class="item-year">({date})</span>' if date else ""

        list_items_html += f"""
        <li class="rank-item" draggable="true" data-title="{title}">
            <div class="rank-num">#{idx + 1}</div>
            <img src="{poster_url}" alt="{title}">
            <div class="item-info">
                <div class="item-title">{title} {date_html}</div>
                <div class="item-elo">Elo: {rating:.1f}</div>
            </div>
            <div class="btn-group">
                <button type="button" class="btn-move" onclick="moveItem(this, -1)">▲</button>
                <button type="button" class="btn-move" onclick="moveItem(this, 1)">▼</button>
            </div>
        </li>
        """

    title_text = TEXT_CONTENT['rank10_title'].format(count=count)
    subtitle_text = TEXT_CONTENT['rank10_subtitle'].format(count=count)

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title_text}</title>
    <style>
        {get_color_css()}
        .rank-container {{ max-width: 650px; margin: 0 auto; }}
        .rank-list {{ list-style: none; padding: 0; margin: 0; }}
        .rank-item {{ 
            display: flex; align-items: center; background: var(--bg-card); border: 1px solid var(--border-color); 
            margin-bottom: 10px; border-radius: 8px; padding: 10px 15px; cursor: grab;
            user-select: none; transition: background 0.2s;
        }}
        .rank-item:hover {{ background: var(--bg-input); border-color: var(--accent-pink); }}
        .rank-num {{ font-size: 20px; font-weight: bold; color: var(--accent-pink); width: 45px; flex-shrink: 0; }}
        .rank-item img {{ width: 50px; height: 75px; object-fit: cover; border-radius: 6px; margin-right: 15px; background: var(--bg-input); }}
        .item-info {{ flex-grow: 1; }}
        .item-title {{ font-size: 16px; font-weight: bold; color: var(--text-primary); }}
        .item-year {{ font-size: 13px; color: var(--text-secondary); font-weight: normal; margin-left: 6px; }}
        .item-elo {{ font-size: 13px; color: var(--accent-pink); margin-top: 4px; }}
        .btn-group {{ display: flex; flex-direction: column; gap: 4px; }}
        .btn-move {{ background: var(--bg-input); color: white; border: 1px solid var(--border-color); padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }}
        .btn-move:hover {{ background: var(--accent-magenta); }}
        .submit-container {{ text-align: center; margin-top: 25px; display: flex; justify-content: center; gap: 15px; }}
        .btn-submit {{ padding: 12px 24px; font-size: 16px; font-weight: bold; background-color: var(--accent-magenta); color: white; border: none; border-radius: 8px; cursor: pointer; transition: background 0.2s; }}
        .btn-submit:hover {{ background-color: var(--accent-pink); color: #000; }}
        .btn-skip {{ padding: 12px 24px; font-size: 16px; font-weight: bold; background-color: var(--bg-input); color: var(--text-secondary); border: 1px solid var(--border-color); border-radius: 8px; cursor: pointer; text-decoration: none; }}
        .btn-skip:hover {{ background-color: var(--accent-plum); color: white; }}
    </style>
</head>
<body>
    <h1>{title_text}</h1>
    <p class="subtitle">{subtitle_text}</p>
    {generate_header_nav("rank10")}

    <div class="rank-container">
        <form id="ranking-form" action="/rank10" method="GET">
            <ul id="rank-list" class="rank-list">
                {list_items_html}
            </ul>
            <div class="submit-container">
                <button type="button" class="btn-submit" onclick="submitRanking()">{TEXT_CONTENT['rank10_submit_btn']}</button>
                <a href="/rank10" class="btn-skip">{TEXT_CONTENT['rank10_skip_btn']}</a>
            </div>
        </form>
    </div>

    <script>
        let dragItem = null;
        document.querySelectorAll('.rank-item').forEach(item => {{
            item.addEventListener('dragstart', (e) => {{ dragItem = item; e.dataTransfer.effectAllowed = 'move'; }});
            item.addEventListener('dragover', (e) => {{ e.preventDefault(); }});
            item.addEventListener('drop', (e) => {{
                e.preventDefault();
                if (dragItem && dragItem !== item) {{
                    let list = item.parentNode;
                    let items = Array.from(list.children);
                    if (items.indexOf(dragItem) < items.indexOf(item)) {{
                        list.insertBefore(dragItem, item.nextSibling);
                    }} else {{
                        list.insertBefore(dragItem, item);
                    }}
                    updateRankNumbers();
                }}
            }});
        }});
        function moveItem(btn, direction) {{
            let item = btn.closest('.rank-item');
            let list = item.parentNode;
            if (direction === -1 && item.previousElementSibling) {{
                list.insertBefore(item, item.previousElementSibling);
            }} else if (direction === 1 && item.nextElementSibling) {{
                list.insertBefore(item.nextElementSibling, item);
            }}
            updateRankNumbers();
        }}
        function updateRankNumbers() {{
            document.querySelectorAll('.rank-item').forEach((item, index) => {{
                item.querySelector('.rank-num').innerText = '#' + (index + 1);
            }});
        }}
        function submitRanking() {{
            const items = document.querySelectorAll('.rank-item');
            const form = document.getElementById('ranking-form');
            items.forEach(item => {{
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'ranked';
                input.value = item.getAttribute('data-title');
                form.appendChild(input);
            }});
            form.submit();
        }}
    </script>
</body>
</html>
"""


def generate_vote_html(api_key=TMDB_API_KEY, target_title=None):
    if len(AppState.movie_elo) < 2:
        return "<h1>Not enough movies loaded to compare!</h1>"

    target_movie = None
    if target_title:
        for item in AppState.movie_elo:
            if item[0].lower() == target_title.lower():
                target_movie = item
                break

    m1, m2 = get_elo_matched_pair(AppState.movie_elo, target_movie=target_movie, proximity_ratio=0.75)
    if not m1 or not m2:
        return "<h1>Not enough movies to compare!</h1>"

    prefetch_posters([m1, m2], api_key)

    p1_poster = get_poster_url(m1[0], api_key, m1[2])
    p2_poster = get_poster_url(m2[0], api_key, m2[2])

    m1_year_html = f'<div class="vote-year">({m1[2]})</div>' if m1[2] else ""
    m2_year_html = f'<div class="vote-year">({m2[2]})</div>' if m2[2] else ""

    m1_enc = urllib.parse.quote(str(m1[0]))
    m2_enc = urllib.parse.quote(str(m2[0]))

    target_query = f"&target={m1_enc}" if target_movie else ""
    skip_query = f"/vote?target={m1_enc}" if target_movie else "/vote"

    elo_diff = abs(m1[1] - m2[1])

    spotlight_header = ""
    if target_movie:
        spotlight_header = f"""
        <div class="spotlight-banner">
             <strong>{TEXT_CONTENT['vote_spotlight_label']}</strong> Ranking <span>"{m1[0]}"</span> (Elo: {m1[1]:.1f})
            <a href="/vote" class="exit-spotlight">✕ Exit Subcategory</a>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{TEXT_CONTENT['vote_title']}</title>
    <style>
        {get_color_css()}
        .match-info {{ text-align: center; color: var(--accent-pink); font-size: 13px; font-weight: bold; margin-bottom: 15px; }}
        .spotlight-banner {{ text-align: center; background: var(--bg-card); border: 1px solid var(--accent-magenta); color: white; padding: 10px 20px; border-radius: 8px; max-width: 600px; margin: 0 auto 20px auto; font-size: 15px; }}
        .spotlight-banner span {{ color: var(--accent-pink); font-weight: bold; }}
        .exit-spotlight {{ margin-left: 15px; color: #ff6b81; text-decoration: none; font-weight: bold; background: rgba(255, 71, 87, 0.15); padding: 4px 10px; border-radius: 6px; border: 1px solid #ff4757; }}
        .exit-spotlight:hover {{ background: #ff4757; color: white; }}
        .matchup-container {{ display: flex; justify-content: center; align-items: center; gap: 40px; margin-top: 20px; flex-wrap: wrap; }}
        .vote-card {{ background: var(--bg-card); padding: 20px; border-radius: 12px; width: 220px; text-align: center; box-shadow: 0 6px 18px rgba(0,0,0,0.6); position: relative; border: 1px solid var(--border-color); }}
        .target-tag {{ position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: var(--accent-magenta); color: white; font-weight: bold; font-size: 11px; padding: 3px 10px; border-radius: 12px; border: 1px solid var(--accent-pink); }}
        .vote-card img {{ width: 100%; height: 320px; object-fit: cover; border-radius: 8px; background: var(--bg-input); }}
        .vote-title {{ font-size: 16px; font-weight: bold; margin: 12px 0 2px 0; color: var(--text-primary); }}
        .vote-year {{ font-size: 13px; color: var(--text-secondary); margin-bottom: 6px; }}
        .vote-elo {{ font-size: 14px; color: var(--accent-pink); font-weight: bold; margin-bottom: 15px; }}
        .vs {{ font-size: 28px; font-weight: bold; color: var(--accent-pink); }}
        .vote-btn {{ display: block; width: 100%; padding: 12px; border: none; border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; text-decoration: none; box-sizing: border-box; transition: background 0.2s; }}
        .btn-left {{ background-color: var(--accent-magenta); color: white; }}
        .btn-left:hover {{ background-color: var(--accent-pink); color: #000; }}
        .btn-right {{ background-color: var(--accent-blue); color: white; }}
        .btn-right:hover {{ background-color: var(--accent-pink); color: #000; }}
        .btn-tie {{ background-color: var(--accent-plum); color: white; padding: 10px 20px; text-decoration: none; font-weight: bold; border-radius: 8px; border: 1px solid var(--border-color); }}
        .btn-tie:hover {{ background-color: var(--accent-pink); color: #000; }}
        .btn-skip {{ background-color: var(--bg-input); color: var(--text-secondary); padding: 10px 20px; text-decoration: none; font-weight: bold; border-radius: 8px; border: 1px solid var(--border-color); }}
        .btn-skip:hover {{ background-color: var(--accent-plum); color: #fff; }}
        .controls {{ display: flex; justify-content: center; gap: 15px; margin-top: 30px; }}
    </style>
</head>
<body>
    <h1>{TEXT_CONTENT['vote_title']}</h1>
    <div class="match-info">⚡ Matchup Rating Gap: Δ {elo_diff:.1f} Elo</div>
    {generate_header_nav("vote")}
    {spotlight_header}
    
    <div class="matchup-container">
        <div class="vote-card">
            {"<div class='target-tag'>TARGET MOVIE</div>" if target_movie else ""}
            <img src="{p1_poster}" alt="{m1[0]}">
            <div class="vote-title">{m1[0]}</div>
            {m1_year_html}
            <div class="vote-elo">Elo: {m1[1]:.1f}</div>
            <a href="/vote?winner=1&m1={m1_enc}&m2={m2_enc}{target_query}" class="vote-btn btn-left">Vote Option 1</a>
        </div>

        <div class="vs">VS</div>

        <div class="vote-card">
            <img src="{p2_poster}" alt="{m2[0]}">
            <div class="vote-title">{m2[0]}</div>
            {m2_year_html}
            <div class="vote-elo">Elo: {m2[1]:.1f}</div>
            <a href="/vote?winner=2&m1={m1_enc}&m2={m2_enc}{target_query}" class="vote-btn btn-right">Vote Option 2</a>
        </div>
    </div>

    <div class="controls">
        <a href="/vote?winner=3&m1={m1_enc}&m2={m2_enc}{target_query}" class="btn-tie">🤝 Tie / Draw</a>
        <a href="{skip_query}" class="btn-skip">➡ Skip Matchup</a>
    </div>
</body>
</html>
"""


def generate_bin_view_html(api_key=TMDB_API_KEY, bin_idx=0, method="norm"):
    for item in AppState.movie_elo:
        item[1] = AppState.elo.getPlayerRating(item[0])
    AppState.movie_elo.sort(key=lambda x: x[1], reverse=True)

    total_movies = len(AppState.movie_elo)
    if total_movies == 0:
        return "<h1>No movies loaded!</h1>"

    elo_vals = [m[1] for m in AppState.movie_elo]
    mean_elo = sum(elo_vals) / total_movies
    variance = sum((e - mean_elo) ** 2 for e in elo_vals) / total_movies
    std_dev = math.sqrt(variance) if variance > 0 else 1.0

    bin_idx = max(0, min(9, bin_idx))
    bin_num = bin_idx + 1

    ratings_map, ratings_list = get_movie_original_ratings()
    exact_map, optimal_map, _, _ = compute_doc3_methods(AppState.movie_elo, ratings_map, ratings_list)

    if method == "exact":
        method_title = "Method 1: Preserved Count Distribution"
        theme_color = "#3a7ecc"
        bin_label = f"Bin {bin_num} ({0.5 + bin_idx * 0.5:.1f}★ Level)"
    elif method == "optimal":
        method_title = "Method 2: Optimal L1 DP Cutoffs"
        theme_color = "#c61f99"
        bin_label = f"Bin {bin_num} ({0.5 + bin_idx * 0.5:.1f}★ Level)"
    else:
        method = "norm"
        method_title = "Standard Normal Z-Score (σ)"
        theme_color = "#e893d2"
        bin_label = NORMAL_BIN_BOUNDS[bin_idx][2]

    bin_movies = []
    for rank, item in enumerate(AppState.movie_elo, 1):
        title = item[0]
        rating = item[1]
        z = (rating - mean_elo) / std_dev

        if method == "exact":
            assigned_r = exact_map.get(title.lower(), 3.0)
            b_idx = rating_to_bin_idx(assigned_r)
            rating_disp = f"Method 1: {assigned_r:.1f}★ ({rating:.1f} Elo)"
        elif method == "optimal":
            assigned_r = optimal_map.get(title.lower(), 3.0)
            b_idx = rating_to_bin_idx(assigned_r)
            rating_disp = f"Method 2: {assigned_r:.1f}★ ({rating:.1f} Elo)"
        else:
            b_idx, _, _, _ = get_normal_bin_info(z)
            rating_disp = f"Elo: {rating:.1f} ({z:+.2f}σ)"

        if b_idx == bin_idx:
            bin_movies.append((rank, item, z, rating_disp))

    prefetch_posters([m[1] for m in bin_movies], api_key)

    dist_toggle_html = f"""
    <div class="dist-toggle">
        <a href="/bin?bin={bin_num}&method=norm" class="dist-btn {'active-norm' if method == 'norm' else ''}">Standard Normal Z-Score (σ)</a>
        <a href="/bin?bin={bin_num}&method=exact" class="dist-btn {'active-exact' if method == 'exact' else ''}">Method 1: Preserved Count Dist.</a>
        <a href="/bin?bin={bin_num}&method=optimal" class="dist-btn {'active-optimal' if method == 'optimal' else ''}">Method 2: Optimal L1 DP Cutoffs</a>
    </div>
    """

    bin_nav_html = '<div class="bin-selector">'
    for i in range(10):
        active_cls = "active" if i == bin_idx else ""
        bin_nav_html += f'<a href="/bin?bin={i + 1}&method={method}" class="bin-btn {active_cls}">Bin {i + 1}</a>'
    bin_nav_html += "</div>"

    cards_html = ""
    if bin_movies:
        for rank, item, z, rating_disp in bin_movies:
            title = item[0]
            date = item[2]
            poster_url = get_poster_url(title, api_key, date)
            date_html = f'<div class="year">({date})</div>' if date else ""
            title_enc = urllib.parse.quote(str(title))

            cards_html += f"""
            <div class="card" style="border-color: {theme_color}aa;">
                <div class="badge">#{rank}</div>
                <a href="/movie?title={title_enc}">
                    <img src="{poster_url}" alt="{title}" loading="lazy">
                </a>
                <div class="title">{title}</div>
                {date_html}
                <div class="rating" style="color: {theme_color};">{rating_disp}</div>
                <div class="card-actions">
                    <a href="/vote?target={title_enc}" class="card-btn btn-sub" title="Vote Matchup">🎯</a>
                    <a href="/movie?title={title_enc}" class="card-btn btn-stats" title="View Stats">📊</a>
                    <a href="/delete?title={title_enc}" class="card-btn btn-danger" onclick="return confirm('Are you sure you want to delete {title}?');" title="Delete">🗑️</a>
                </div>
            </div>
            """
    else:
        cards_html = f"""
        <div class="no-results">
            <h2>No movies currently in Bin {bin_num} for {method_title}</h2>
            <p>Rank or add more movies to populate this bucket.</p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Bin {bin_num} - {method_title}</title>
    <style>
        {get_color_css()}
        h1 {{ color: {theme_color}; }}
        .dist-toggle {{ display: flex; justify-content: center; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
        .dist-btn {{ padding: 8px 16px; border-radius: 20px; font-size: 13px; font-weight: bold; text-decoration: none; color: var(--text-secondary); background: var(--bg-card); border: 1px solid var(--border-color); }}
        .dist-btn.active-norm {{ background: rgba(232, 147, 210, 0.25); color: #e893d2; border-color: #e893d2; }}
        .dist-btn.active-exact {{ background: rgba(58, 126, 204, 0.25); color: #3a7ecc; border-color: #3a7ecc; }}
        .dist-btn.active-optimal {{ background: rgba(198, 31, 153, 0.25); color: #c61f99; border-color: #c61f99; }}
        
        .bin-selector {{ display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; margin-bottom: 25px; max-width: 900px; margin-left: auto; margin-right: auto; }}
        .bin-btn {{ padding: 8px 12px; background: var(--bg-card); border: 1px solid var(--border-color); color: var(--text-secondary); text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 13px; }}
        .bin-btn.active, .bin-btn:hover {{ background: {theme_color}; color: white; border-color: {theme_color}; }}

        .grid {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; margin-top: 20px; }}
        .card {{ 
            position: relative; background: var(--bg-card); padding: 10px; border-radius: 12px; 
            width: 185px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.5); 
            transition: transform 0.2s ease, border-color 0.2s ease; border: 1px solid var(--border-color);
            display: flex; flex-direction: column; justify-content: space-between;
        }}
        .card:hover {{ transform: translateY(-4px); border-color: {theme_color}; }}
        .badge {{ position: absolute; top: 15px; left: 15px; background: rgba(15, 6, 23, 0.85); color: var(--accent-pink); font-weight: bold; font-size: 13px; padding: 4px 8px; border-radius: 6px; border: 1px solid var(--accent-pink); z-index: 2; }}
        .card img {{ width: 100%; height: 278px; object-fit: cover; border-radius: 8px; background: var(--bg-input); cursor: pointer; }}
        .title {{ font-size: 14px; font-weight: bold; margin-top: 8px; word-wrap: break-word; color: var(--text-primary); }}
        .year {{ font-size: 12px; color: var(--text-secondary); margin-top: 2px; }}
        .rating {{ font-size: 13px; font-weight: bold; margin-top: 4px; }}
        .card-actions {{ display: flex; gap: 5px; margin-top: 10px; justify-content: center; }}
        .card-btn {{ font-size: 13px; font-weight: bold; padding: 5px 8px; border-radius: 6px; text-decoration: none; flex: 1; text-align: center; }}
        .btn-sub {{ background: var(--accent-dark-plum); color: var(--accent-pink); border: 1px solid var(--accent-pink); }}
        .btn-sub:hover {{ background: var(--accent-pink); color: #000; }}
        .btn-stats {{ background: var(--bg-input); color: var(--text-secondary); border: 1px solid var(--border-color); }}
        .btn-stats:hover {{ background: var(--accent-plum); color: #fff; }}
        .btn-danger {{ background: var(--btn-danger-bg); color: #ff6b81; border: 1px solid var(--btn-danger); }}
        .btn-danger:hover {{ background: var(--btn-danger); color: white; }}
        .no-results {{ text-align: center; margin-top: 40px; background: var(--bg-card); padding: 40px; border-radius: 12px; border: 1px solid var(--border-color); max-width: 500px; margin: 40px auto; }}
    </style>
</head>
<body>
    <h1>Bin {bin_num} Movies ({bin_label})</h1>
    <p class="subtitle">{method_title} — Showing {len(bin_movies)} movie(s)</p>
    {generate_header_nav("stats")}
    {dist_toggle_html}
    {bin_nav_html}

    <div class="grid">
        {cards_html}
    </div>
</body>
</html>
"""


def generate_search_html(api_key=TMDB_API_KEY, query=""):
    for item in AppState.movie_elo:
        item[1] = AppState.elo.getPlayerRating(item[0])
    AppState.movie_elo.sort(key=lambda x: x[1], reverse=True)

    query_clean = query.strip().lower()
    matches = []

    for idx, item in enumerate(AppState.movie_elo):
        title = item[0]
        if query_clean in title.lower():
            rank = idx + 1
            matches.append((rank, item))

    prefetch_posters([m[1] for m in matches], api_key)

    results_html = ""
    if matches:
        for rank, item in matches:
            title = item[0]
            rating = item[1]
            date = item[2]
            poster_url = get_poster_url(title, api_key, date)
            date_html = f'<div class="year">({date})</div>' if date else ""
            title_enc = urllib.parse.quote(str(title))

            results_html += f"""
            <div class="card">
                <div class="badge">#{rank}</div>
                <a href="/movie?title={title_enc}">
                    <img src="{poster_url}" alt="{title}">
                </a>
                <div class="title">{title}</div>
                {date_html}
                <div class="rating">Elo: {rating:.1f}</div>
                <div class="card-actions">
                    <a href="/vote?target={title_enc}" class="card-btn btn-sub" title="Vote Matchup">🎯</a>
                    <a href="/movie?title={title_enc}" class="card-btn btn-stats" title="View Stats">📊</a>
                    <a href="/delete?title={title_enc}" class="card-btn btn-danger" onclick="return confirm('Are you sure you want to delete {title}?');" title="Delete">🗑️</a>
                </div>
            </div>
            """
    else:
        results_html = f"""
        <div class="no-results">
            <h2>No movies found matching "{query}"</h2>
            <p>Try searching for a different title or add a new movie to the collection.</p>
            <a href="/add" class="btn-add-new">+ Add "{query}" to Database</a>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{TEXT_CONTENT['search_title']} - {query}</title>
    <style>
        {get_color_css()}
        .grid {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; margin-top: 20px; }}
        .card {{ 
            position: relative; background: var(--bg-card); padding: 10px; border-radius: 12px; 
            width: 185px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.5); 
            border: 1px solid var(--border-color); display: flex; flex-direction: column; justify-content: space-between;
        }}
        .badge {{ position: absolute; top: 15px; left: 15px; background: rgba(15, 6, 23, 0.85); color: var(--accent-pink); font-weight: bold; font-size: 13px; padding: 4px 8px; border-radius: 6px; border: 1px solid var(--accent-pink); z-index: 2; }}
        .card img {{ width: 100%; height: 278px; object-fit: cover; border-radius: 8px; background: var(--bg-input); cursor: pointer; }}
        .title {{ font-size: 14px; font-weight: bold; margin-top: 8px; word-wrap: break-word; color: var(--text-primary); }}
        .year {{ font-size: 12px; color: var(--text-secondary); margin-top: 2px; }}
        .rating {{ font-size: 13px; color: var(--accent-pink); font-weight: bold; margin-top: 4px; }}
        .card-actions {{ display: flex; gap: 5px; margin-top: 10px; justify-content: center; }}
        .card-btn {{ font-size: 13px; font-weight: bold; padding: 5px 8px; border-radius: 6px; text-decoration: none; flex: 1; text-align: center; }}
        .btn-sub {{ background: var(--accent-dark-plum); color: var(--accent-pink); border: 1px solid var(--accent-pink); }}
        .btn-stats {{ background: var(--bg-input); color: var(--text-secondary); border: 1px solid var(--border-color); }}
        .btn-danger {{ background: var(--btn-danger-bg); color: #ff6b81; border: 1px solid var(--btn-danger); }}
        .btn-danger:hover {{ background: var(--btn-danger); color: white; }}
        .no-results {{ text-align: center; margin-top: 50px; background: var(--bg-card); padding: 40px; border-radius: 12px; border: 1px solid var(--border-color); max-width: 500px; margin: 50px auto 0 auto; }}
        .btn-add-new {{ display: inline-block; margin-top: 15px; padding: 10px 20px; background: var(--accent-magenta); color: white; font-weight: bold; border-radius: 8px; text-decoration: none; }}
    </style>
</head>
<body>
    <h1>{TEXT_CONTENT['search_title']}</h1>
    <p class="subtitle">Found {len(matches)} movie match(es) for "{query}"</p>
    {generate_header_nav("", query)}

    <div class="grid">
        {results_html}
    </div>
</body>
</html>
"""


def generate_movie_detail_html(api_key=TMDB_API_KEY, title_query=""):
    for item in AppState.movie_elo:
        item[1] = AppState.elo.getPlayerRating(item[0])
    AppState.movie_elo.sort(key=lambda x: x[1], reverse=True)

    total_movies = len(AppState.movie_elo)
    target_movie = None
    rank = -1

    for idx, item in enumerate(AppState.movie_elo):
        if item[0].lower() == title_query.lower():
            target_movie = item
            rank = idx + 1
            break

    if not target_movie:
        return f"""<!DOCTYPE html>
<html>
<head><title>Movie Not Found</title></head>
<body style="background:#0f0617; color:#ede5f6; font-family:'Segoe UI', Arial, sans-serif; text-align:center; padding:50px;">
    <h1>Movie "{title_query}" Not Found</h1>
    <p><a href="/" style="color:#e893d2;">Return to Rankings Gallery</a></p>
</body>
</html>"""

    title = target_movie[0]
    elo_val = target_movie[1]
    date = target_movie[2]
    title_enc = urllib.parse.quote(str(title))

    prefetch_posters([target_movie], api_key)
    poster_url = get_poster_url(title, api_key, date)

    elo_vals = [m[1] for m in AppState.movie_elo]
    mean_elo = sum(elo_vals) / total_movies
    variance = sum((e - mean_elo) ** 2 for e in elo_vals) / total_movies
    std_dev = math.sqrt(variance) if variance > 0 else 1.0

    z_score = (elo_val - mean_elo) / std_dev

    ratings_map, ratings_list = get_movie_original_ratings()
    exact_map, optimal_map, _, _ = compute_doc3_methods(AppState.movie_elo, ratings_map, ratings_list)
    exact_rating = exact_map.get(title.lower(), 3.0)
    optimal_rating = optimal_map.get(title.lower(), 3.0)

    norm_bin_idx, norm_bin_label, _, _ = get_normal_bin_info(z_score)
    norm_bin_num = norm_bin_idx + 1

    percentile = normal_cdf(z_score) * 100.0

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{TEXT_CONTENT['detail_title']} - {title}</title>
    <style>
        {get_color_css()}
        .detail-card {{ max-width: 820px; margin: 0 auto; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 30px; display: flex; gap: 30px; box-shadow: 0 6px 18px rgba(0,0,0,0.6); flex-wrap: wrap; }}
        .detail-poster {{ width: 220px; text-align: center; }}
        .detail-poster img {{ width: 100%; height: 330px; object-fit: cover; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-input); }}
        .detail-content {{ flex: 1; min-width: 280px; }}
        .movie-title {{ font-size: 26px; font-weight: bold; margin: 0 0 5px 0; color: var(--text-primary); text-align: left; }}
        .movie-year {{ font-size: 16px; color: var(--text-secondary); margin-bottom: 20px; }}
        
        .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px; }}
        .stat-box {{ background: var(--bg-input); border: 1px solid var(--border-color); padding: 12px 15px; border-radius: 8px; }}
        .stat-val {{ font-size: 18px; font-weight: bold; color: var(--accent-pink); margin-top: 4px; }}
        .stat-label {{ font-size: 11px; color: var(--text-secondary); font-weight: bold; text-transform: uppercase; }}

        .gauge-container {{ background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 8px; padding: 15px; margin-bottom: 25px; }}
        .gauge-title {{ font-size: 13px; font-weight: bold; color: var(--text-secondary); margin-bottom: 10px; }}
        .gauge-bar {{ height: 16px; background: var(--bg-main); border-radius: 8px; position: relative; overflow: hidden; border: 1px solid var(--border-color); }}
        .gauge-fill {{ height: 100%; background: linear-gradient(90deg, var(--accent-blue), var(--accent-magenta), var(--accent-pink)); border-radius: 8px; }}
        .gauge-markers {{ display: flex; justify-content: space-between; font-size: 11px; color: var(--text-secondary); margin-top: 6px; }}

        .action-buttons {{ display: flex; gap: 15px; flex-wrap: wrap; }}
        .btn-action {{ padding: 12px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 14px; text-align: center; flex: 1; transition: background 0.2s; }}
        .btn-vote {{ background: var(--accent-magenta); color: white; }}
        .btn-vote:hover {{ background: var(--accent-pink); color: #000; }}
        .btn-back {{ background: var(--bg-input); color: white; border: 1px solid var(--border-color); }}
        .btn-back:hover {{ background: var(--accent-plum); }}
        .btn-delete {{ background: var(--btn-danger-bg); color: #ff6b81; border: 1px solid var(--btn-danger); }}
        .btn-delete:hover {{ background: var(--btn-danger); color: white; }}
    </style>
</head>
<body>
    <h1>{TEXT_CONTENT['detail_title']}</h1>
    <p class="subtitle">{TEXT_CONTENT['detail_subtitle']}</p>
    {generate_header_nav("")}

    <div class="detail-card">
        <div class="detail-poster">
            <img src="{poster_url}" alt="{title}">
            <div style="margin-top: 12px; font-size: 15px; color: var(--accent-pink); font-weight: bold;">Overall Rank: #{rank} / {total_movies}</div>
        </div>

        <div class="detail-content">
            <div class="movie-title">{title}</div>
            <div class="movie-year">{f'Released in {date}' if date else 'Release year unlisted'}</div>

            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-label">ELO RATING</div>
                    <div class="stat-val">{elo_val:.1f} Elo</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Z-SCORE / STDEV</div>
                    <div class="stat-val">{z_score:+.2f} σ</div>
                    <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Percentile: {percentile:.1f}%</div>
                </div>
                <a href="/bin?bin={norm_bin_num}" style="text-decoration: none;">
                    <div class="stat-box" style="border-color: var(--accent-pink);">
                        <div class="stat-label" style="color: var(--text-secondary);">STANDARD NORMAL BIN</div>
                        <div class="stat-val" style="color: var(--accent-pink);">Bin {norm_bin_num} / 10 ↗</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">{norm_bin_label}</div>
                    </div>
                </a>
                <div class="stat-box" style="border-color: var(--accent-blue);">
                    <div class="stat-label" style="color: var(--accent-blue);">METHOD 1 (PRESERVED COUNTS)</div>
                    <div class="stat-val" style="color: var(--accent-blue);">{exact_rating:.1f} / 5.0</div>
                    <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Preserved Count Dist.</div>
                </div>
                <div class="stat-box" style="border-color: var(--accent-magenta); grid-column: span 2;">
                    <div class="stat-label" style="color: var(--accent-magenta);">METHOD 2 (OPTIMAL L1 DP CUTOFFS)</div>
                    <div class="stat-val" style="color: var(--accent-magenta);">{optimal_rating:.1f} / 5.0</div>
                    <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Minimum Rating Deviation Cutoffs</div>
                </div>
            </div>

            <div class="gauge-container">
                <div class="gauge-title">GAUSSIAN BELL CURVE POSITION ({percentile:.1f}th Percentile)</div>
                <div class="gauge-bar">
                    <div class="gauge-fill" style="width: {max(2.0, min(100.0, percentile))}%;"></div>
                </div>
                <div class="gauge-markers">
                    <span>-3.0σ (Bottom)</span>
                    <span>0.0σ (Mean 50%)</span>
                    <span>+3.0σ (Top)</span>
                </div>
            </div>

            <div class="action-buttons">
                <a href="/vote?target={title_enc}" class="btn-action btn-vote">🎯 Matchup Vote</a>
                <a href="/stats" class="btn-action btn-back">📊 View Distribution Analytics</a>
                <a href="/delete?title={title_enc}" class="btn-action btn-delete" onclick="return confirm('Are you sure you want to permanently delete {title}?');">🗑️ Delete Movie</a>
            </div>
        </div>
    </div>
</body>
</html>
"""


def generate_add_html():
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{TEXT_CONTENT['add_title']}</title>
    <style>
        {get_color_css()}
        .form-container {{ max-width: 450px; margin: 0 auto; background: var(--bg-card); padding: 30px; border-radius: 12px; border: 1px solid var(--border-color); box-shadow: 0 6px 18px rgba(0,0,0,0.6); }}
        .form-group {{ margin-bottom: 20px; text-align: left; }}
        label {{ display: block; font-weight: bold; margin-bottom: 8px; color: var(--text-secondary); font-size: 14px; }}
        input[type="text"], input[type="number"] {{ width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-input); color: var(--text-primary); font-size: 15px; box-sizing: border-box; }}
        input[type="text"]:focus, input[type="number"]:focus {{ border-color: var(--accent-pink); outline: none; }}
        .rating-box {{ display: flex; align-items: center; gap: 15px; }}
        .rating-val {{ font-size: 22px; font-weight: bold; color: var(--accent-pink); min-width: 50px; text-align: right; }}
        .btn-submit {{ width: 100%; padding: 12px; font-size: 16px; font-weight: bold; background-color: var(--accent-magenta); color: white; border: none; border-radius: 8px; cursor: pointer; margin-top: 10px; transition: background 0.2s; }}
        .btn-submit:hover {{ background-color: var(--accent-pink); color: #000; }}
    </style>
</head>
<body>
    <h1>{TEXT_CONTENT['add_title']}</h1>
    <p class="subtitle">{TEXT_CONTENT['add_subtitle']}</p>
    {generate_header_nav("add")}

    <div class="form-container">
        <form action="/add" method="GET">
            <div class="form-group">
                <label for="title">Movie Title *</label>
                <input type="text" id="title" name="title" placeholder="e.g. Inception" required autofocus>
            </div>

            <div class="form-group">
                <label for="year">Release Year (Optional)</label>
                <input type="number" id="year" name="year" placeholder="e.g. 2010" min="1880" max="2030">
            </div>

            <div class="form-group">
                <label for="rating">Initial Rating (Scale ~1-10) *</label>
                <div class="rating-box">
                    <input type="number" id="rating" name="rating" min="0" max="100" step="0.1" value="7.0" required oninput="document.getElementById('val-disp').innerText = parseFloat(this.value).toFixed(1) + '/10'">
                    <span class="rating-val" id="val-disp">7.0/10</span>
                </div>
            </div>

            <button type="submit" class="btn-submit">{TEXT_CONTENT['add_btn']}</button>
        </form>
    </div>
</body>
</html>
"""


def generate_import_html(message=""):
    status_html = f'<div class="status-msg">{message}</div>' if message else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{TEXT_CONTENT['import_title']}</title>
    <style>
        {get_color_css()}
        .container {{ max-width: 600px; margin: 0 auto; }}
        .card {{ background: var(--bg-card); border: 1px solid var(--border-color); padding: 25px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 6px 18px rgba(0,0,0,0.6); }}
        .card h2 {{ margin-top: 0; font-size: 20px; color: var(--text-primary); text-align: left; }}
        .card p {{ color: var(--text-secondary); font-size: 14px; line-height: 1.5; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: var(--accent-magenta); color: #fff; text-decoration: none; border-radius: 8px; border: none; font-size: 14px; font-weight: bold; cursor: pointer; transition: background 0.2s; }}
        .btn:hover {{ background: var(--accent-pink); color: #000; }}
        .btn-export {{ background: var(--accent-blue); color: #fff; width: 100%; margin-top: 5px; }}
        .btn-export:hover {{ background: var(--accent-pink); color: #000; }}
        select {{ width: 100%; padding: 10px; border-radius: 8px; background: var(--bg-input); color: var(--text-primary); border: 1px solid var(--border-color); font-size: 14px; outline: none; margin-bottom: 15px; }}
        input[type="file"] {{ margin: 15px 0; display: block; color: var(--text-secondary); font-size: 14px; }}
        .status-msg {{ padding: 12px 15px; background: var(--accent-dark-plum); border: 1px solid var(--accent-pink); color: #ffffff; margin-bottom: 25px; border-radius: 8px; text-align: center; font-size: 14px; }}
    </style>
</head>
<body>
    <h1>{TEXT_CONTENT['import_title']}</h1>
    <p class="subtitle">{TEXT_CONTENT['import_subtitle']}</p>
    {generate_header_nav("import")}

    <div class="container">
        {status_html}

        <div class="card">
            <h2>Export Database Ratings</h2>
            <p>Select your preferred rating scale format and download your full movie database as a CSV file.</p>
            <form action="/export" method="GET">
                <label for="scale" style="display: block; font-weight: bold; color: var(--text-secondary); font-size: 14px; margin-bottom: 8px;">Select Scale for Export:</label>
                <select id="scale" name="scale">
                    <option value="elo">Raw Elo Rating Scale (e.g. ~1200 Baseline)</option>
                    <option value="zscore">Standard Normal Z-Score Scale (σ Units)</option>
                    <option value="exact">5-Star Scale (Method 1: Preserved Count Distribution)</option>
                    <option value="optimal">5-Star Scale (Method 2: Optimal L1 DP Cutoffs)</option>
                    <option value="scale10">10-Point Percentile Scale (1.0 to 10.0)</option>
                    <option value="star5">5-Star Percentile Scale (0.5 to 5.0)</option>
                </select>
                <button type="submit" class="btn btn-export">📥 Download Exported CSV</button>
            </form>
        </div>

        <div class="card">
            <h2>Import Ratings</h2>
            <p>Upload a CSV file containing movie titles and ratings to scale and merge into your database.</p>
            <form action="/import" method="post" enctype="multipart/form-data">
                <label for="csv_file" style="font-weight: bold; color: var(--text-secondary); font-size: 14px;">Select CSV File:</label>
                <input type="file" id="csv_file" name="csv_file" accept=".csv" required>
                <button type="submit" class="btn">🚀 Upload & Import</button>
            </form>
        </div>
    </div>
</body>
</html>"""


def generate_stats_html():
    for item in AppState.movie_elo:
        item[1] = AppState.elo.getPlayerRating(item[0])
    AppState.movie_elo.sort(key=lambda x: x[1], reverse=True)

    total_movies = len(AppState.movie_elo)
    if total_movies == 0:
        return "<h1>No movies loaded to display statistics!</h1>"

    elo_vals = [m[1] for m in AppState.movie_elo]
    mean_elo = sum(elo_vals) / total_movies
    variance = sum((e - mean_elo) ** 2 for e in elo_vals) / total_movies
    std_dev = math.sqrt(variance) if variance > 0 else 1.0

    norm_bin_counts = [0] * 10
    bin_movie_samples = [[] for _ in range(10)]

    for rank, item in enumerate(AppState.movie_elo, 1):
        z = (item[1] - mean_elo) / std_dev
        idx, label, low, high = get_normal_bin_info(z)
        norm_bin_counts[idx] += 1
        if len(bin_movie_samples[idx]) < 3:
            bin_movie_samples[idx].append(item[0])

    ratings_map, ratings_list = get_movie_original_ratings()
    _, _, exact_bin_counts, optimal_bin_counts = compute_doc3_methods(AppState.movie_elo, ratings_map, ratings_list)

    theoretical_pcts = [0.0228, 0.0440, 0.0918, 0.1498, 0.1916, 0.1916, 0.1498, 0.0918, 0.0440, 0.0228]
    expected_counts = [p * total_movies for p in theoretical_pcts]

    max_count = max(
        max(norm_bin_counts),
        max(exact_bin_counts),
        max(optimal_bin_counts),
        max(expected_counts),
        1,
    )

    histogram_bars_html = ""
    for i in range(10):
        norm_c = norm_bin_counts[i]
        exact_c = exact_bin_counts[i]
        optimal_c = optimal_bin_counts[i]
        exp_c = expected_counts[i]

        norm_h = int((norm_c / max_count) * 220)
        exact_h = int((exact_c / max_count) * 220)
        optimal_h = int((optimal_c / max_count) * 220)
        ideal_h = int((exp_c / max_count) * 220)

        bin_label = f"Bin {i + 1}"

        histogram_bars_html += f"""
        <div class="bar-column">
            <div class="bar-wrapper">
                <div class="ideal-line" style="bottom: {ideal_h}px;" title="Theoretical Expectation: {exp_c:.1f} movies"></div>
                <a href="/bin?bin={i + 1}&method=norm" class="bar bar-norm" style="height: {max(norm_h, 4)}px;" title="Standard Normal Bin #{i + 1}: {norm_c} movies">
                    <span class="bar-count-norm">{norm_c if norm_c > 0 else ''}</span>
                </a>
                <a href="/bin?bin={i + 1}&method=exact" class="bar bar-exact" style="height: {max(exact_h, 4)}px;" title="Method 1 Bin #{i + 1}: {exact_c} movies">
                    <span class="bar-count-exact">{exact_c if exact_c > 0 else ''}</span>
                </a>
                <a href="/bin?bin={i + 1}&method=optimal" class="bar bar-optimal" style="height: {max(optimal_h, 4)}px;" title="Method 2 Bin #{i + 1}: {optimal_c} movies">
                    <span class="bar-count-optimal">{optimal_c if optimal_c > 0 else ''}</span>
                </a>
            </div>
            <a href="/bin?bin={i + 1}&method=norm" style="text-decoration: none;">
                <div class="bar-label" style="color: var(--accent-pink); cursor: pointer;">{bin_label} ↗</div>
            </a>
            <div class="bar-sublabel">{NORMAL_BIN_BOUNDS[i][2]}</div>
        </div>
        """

    table_rows_html = ""
    for i in range(10):
        norm_c = norm_bin_counts[i]
        exact_c = exact_bin_counts[i]
        optimal_c = optimal_bin_counts[i]
        exp_c = expected_counts[i]

        norm_pct = (norm_c / total_movies) * 100.0
        exact_pct = (exact_c / total_movies) * 100.0
        optimal_pct = (optimal_c / total_movies) * 100.0

        samples_str = ", ".join(bin_movie_samples[i]) if bin_movie_samples[i] else "<em>Empty Bucket</em>"

        table_rows_html += f"""
        <tr>
            <td><a href="/bin?bin={i + 1}&method=norm" style="color: var(--accent-pink); font-weight: bold; text-decoration: none;">Bin {i + 1} ↗</a> ({NORMAL_BIN_BOUNDS[i][2]})</td>
            <td><a href="/bin?bin={i + 1}&method=norm" style="color: var(--accent-pink); font-weight: bold; text-decoration: none;">{norm_c} ({norm_pct:.1f}%)</a></td>
            <td><a href="/bin?bin={i + 1}&method=exact" style="color: var(--accent-blue); font-weight: bold; text-decoration: none;">{exact_c} ({exact_pct:.1f}%)</a></td>
            <td><a href="/bin?bin={i + 1}&method=optimal" style="color: var(--accent-magenta); font-weight: bold; text-decoration: none;">{optimal_c} ({optimal_pct:.1f}%)</a></td>
            <td style="color: var(--text-secondary);">~{exp_c:.1f} ({(exp_c / total_movies) * 100:.1f}%)</td>
            <td class="sample-movies">
                {samples_str}<br>
                <a href="/bin?bin={i + 1}&method=norm" style="color: var(--accent-pink); font-size: 11px; text-decoration: none; font-weight: bold;">View Bin {i + 1} Movies →</a>
            </td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{TEXT_CONTENT['stats_title']}</title>
    <style>
        {get_color_css()}
        .stats-summary {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
        .stat-card {{ background: var(--bg-card); border: 1px solid var(--border-color); padding: 15px 25px; border-radius: 12px; text-align: center; min-width: 140px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }}
        .stat-card .val {{ font-size: 22px; font-weight: bold; color: var(--accent-pink); margin-top: 5px; }}
        .stat-card .label {{ font-size: 12px; color: var(--text-secondary); font-weight: bold; text-transform: uppercase; }}

        .chart-card {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 25px; margin-bottom: 30px; box-shadow: 0 6px 18px rgba(0,0,0,0.6); max-width: 1100px; margin-left: auto; margin-right: auto; }}
        .chart-title {{ font-size: 18px; font-weight: bold; margin-bottom: 5px; text-align: center; color: var(--text-primary); }}
        .chart-desc {{ font-size: 13px; color: var(--text-secondary); text-align: center; margin-bottom: 20px; }}

        .legend {{ display: flex; justify-content: center; gap: 25px; margin-bottom: 25px; font-size: 13px; font-weight: bold; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; color: var(--text-secondary); }}
        .legend-box {{ width: 14px; height: 14px; border-radius: 3px; display: inline-block; }}

        .histogram {{ display: flex; justify-content: space-between; align-items: flex-end; height: 260px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px; gap: 8px; position: relative; }}
        .bar-column {{ flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end; position: relative; }}
        .bar-wrapper {{ width: 100%; height: 220px; position: relative; display: flex; justify-content: center; }}

        .bar {{ display: block; border-radius: 6px 6px 0 0; position: absolute; bottom: 0; transition: height 0.3s ease, filter 0.2s ease, transform 0.1s ease; text-decoration: none; cursor: pointer; }}
        .bar:hover {{ filter: brightness(1.35); z-index: 10 !important; transform: scaleY(1.02); }}
        .bar-norm {{ background: rgba(232, 147, 210, 0.85); border: 1px solid #e893d2; z-index: 3; width: 30%; left: 5%; }}
        .bar-exact {{ background: rgba(58, 126, 204, 0.85); border: 1px solid #3a7ecc; z-index: 2; width: 35%; left: 35%; }}
        .bar-optimal {{ background: rgba(198, 31, 153, 0.85); border: 1px solid #c61f99; z-index: 1; width: 30%; left: 65%; }}

        .bar-count-norm {{ position: absolute; top: -18px; width: 100%; text-align: center; font-size: 10px; font-weight: bold; color: #e893d2; }}
        .bar-count-exact {{ position: absolute; top: -18px; width: 100%; text-align: center; font-size: 10px; font-weight: bold; color: #3a7ecc; }}
        .bar-count-optimal {{ position: absolute; top: -18px; width: 100%; text-align: center; font-size: 10px; font-weight: bold; color: #c61f99; }}

        .ideal-line {{ position: absolute; width: 100%; height: 2px; background: #ede5f6; z-index: 4; border-top: 1px dashed #ede5f6; opacity: 0.8; pointer-events: none; }}

        .bar-label {{ font-size: 11px; font-weight: bold; margin-top: 8px; text-align: center; }}
        .bar-sublabel {{ font-size: 9px; color: var(--text-secondary); text-align: center; margin-top: 2px; }}

        .table-card {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 25px; max-width: 1100px; margin: 0 auto 40px auto; box-shadow: 0 6px 18px rgba(0,0,0,0.6); overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }}
        th, td {{ padding: 12px 10px; border-bottom: 1px solid var(--border-color); }}
        th {{ background: var(--bg-input); color: var(--text-secondary); font-size: 12px; text-transform: uppercase; }}
        tr:hover {{ background: var(--bg-input); }}
        .sample-movies {{ font-size: 12px; color: var(--text-secondary); }}
    </style>
</head>
<body>
    <h1>{TEXT_CONTENT['stats_title']}</h1>
    <p class="subtitle">{TEXT_CONTENT['stats_subtitle']}</p>
    {generate_header_nav("stats")}

    <div class="stats-summary">
        <div class="stat-card">
            <div class="label">Total Movies</div>
            <div class="val">{total_movies}</div>
        </div>
        <div class="stat-card">
            <div class="label">Mean Elo</div>
            <div class="val">{mean_elo:.1f}</div>
        </div>
        <div class="stat-card">
            <div class="label">Std Dev (σ)</div>
            <div class="val">{std_dev:.1f}</div>
        </div>
    </div>

    <div class="chart-card">
        <div class="chart-title">{TEXT_CONTENT['stats_chart_title']}</div>
        <div class="chart-desc">{TEXT_CONTENT['stats_chart_desc']}</div>

        <div class="legend">
            <div class="legend-item"><span class="legend-box" style="background: rgba(232, 147, 210, 0.85); border: 1px solid #e893d2;"></span> Standard Normal Z-Score (σ)</div>
            <div class="legend-item"><span class="legend-box" style="background: rgba(58, 126, 204, 0.85); border: 1px solid #3a7ecc;"></span> Method 1: Preserved Count Dist.</div>
            <div class="legend-item"><span class="legend-box" style="background: rgba(198, 31, 153, 0.85); border: 1px solid #c61f99;"></span> Method 2: Optimal L1 DP Cutoffs</div>
        </div>

        <div class="histogram">
            {histogram_bars_html}
        </div>
    </div>

    <div class="table-card">
        <h2 style="margin-top: 0; margin-bottom: 15px; font-size: 18px; color: var(--text-primary); text-align: left;">Bin Breakdown Table</h2>
        <table>
            <thead>
                <tr>
                    <th>Bin Range</th>
                    <th>Standard Normal</th>
                    <th>Method 1</th>
                    <th>Method 2</th>
                    <th>Expected</th>
                    <th>Sample Movies</th>
                </tr>
            </thead>
            <tbody>
                {table_rows_html}
            </tbody>
        </table>
    </div>
</body>
</html>
"""