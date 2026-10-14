import hashlib
import json
import re
from html import escape
from urllib.parse import quote, urlencode, urlsplit

from config import TEXT_CONTENT, get_color_css
from state import AppState


ICON_PATHS = {
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    "list": '<path d="M9 5h12M9 12h12M9 19h12M3 5h1M3 12h1M3 19h1"/>',
    "vote": '<path d="m4 7 4-4 4 4M8 3v18m12-4-4 4-4-4m4 4V3"/>',
    "rank": '<path d="M8 5h13M8 12h10M8 19h7M3 5h1M3 12h1M3 19h1"/>',
    "chart": '<path d="M4 3v18h17M8 16v-5m5 5V6m5 10V9"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "data": '<path d="M12 3v12m-4-4 4 4 4-4M5 15v5h14v-5"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    "arrow": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    "left": '<path d="M20 12H4m6-6-6 6 6 6"/>',
    "trash": '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
    "film": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 8h4m-4 8h4M17 8h4m-4 8h4"/>',
    "up": '<path d="m6 15 6-6 6 6"/>',
    "down": '<path d="m6 9 6 6 6-6"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "close": '<path d="m6 6 12 12M6 18 18 6"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3 2.5c-.5.2-.5 1-.5 1.5M12 17h.01"/>',
    "undo": '<path d="M8 4 3 9l5 5M3 9h10a6 6 0 0 1 0 12"/>',
}


def icon(name):
    return f'<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICON_PATHS[name]}</svg>'


def header_nav(active="rankings", query_val=""):
    groups = [
        ("YOUR COLLECTION", [("rankings", "/", "grid", "Rankings"), ("stats", "/stats", "chart", "Analytics")]),
        ("RANKING TOOLS", [("vote", "/vote", "vote", "Match voting"), ("rank10", "/rank10", "rank", "Rank a cluster")]),
        ("DATA", [("add", "/add", "plus", "Add a film"), ("import", "/import", "data", "Import & export")]),
        ("HELP", [("help", "/help", "help", "How to use")]),
    ]
    links = ""
    for label, items in groups:
        links += f'<div class="nav-group"><p class="nav-label">{label}</p>'
        for key, url, symbol, text in items:
            current = ' aria-current="page"' if active == key else ""
            links += f'<a href="{url}" class="nav-link {"active" if active == key else ""}"{current}>{icon(symbol)}<span>{text}</span>{"<span class=nav-dot></span>" if active == key else ""}</a>'
        links += "</div>"
    return f"""
    <aside class="sidebar" id="sidebar" aria-label="Main navigation">
        <button class="icon-button nav-close" aria-label="Close navigation">{icon('close')}</button>
        <nav>{links}</nav>
    </aside>"""


def page(title, subtitle, active, content, query="", eyebrow="", hero_extra="", hero_class=""):
    labels = {"rankings": "Rankings", "stats": "Analytics", "vote": "Match voting", "rank10": "Rank a cluster", "add": "Add a film", "import": "Import & export", "search": "Search", "detail": "Film profile", "help": "How to use"}
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#141514">
    <link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
    <title>{escape(re.sub('<[^>]+>', ' ', title)).strip()}</title>
    <style>{get_color_css()}</style>
    <link rel="stylesheet" href="/static/app.css">
    <script src="/static/app.js" defer></script>
</head>
<body data-page="{active}">
    <a class="skip-link" href="#main">Skip to content</a>
    {header_nav(active)}
    <div class="app-content">
        <header class="topbar">
            <button class="icon-button menu-toggle" aria-label="Open navigation" aria-controls="sidebar" aria-expanded="false">{icon('menu')}</button>
            <div class="breadcrumb"><a href="/">Collection</a><span>/</span><span>{labels.get(active, 'Collection')}</span></div>
            <form action="/search" method="GET" class="search-form" role="search">
                <button type="submit" class="search-btn" aria-label="Search films">{icon('search')}</button>
                <input type="search" name="q" aria-label="Search your collection" placeholder="{TEXT_CONTENT['search_placeholder']}" value="{escape(query, quote=True)}" required class="search-input">
            </form>
            <a class="topbar-add" href="/add">{icon('plus')}<span>Add a film</span></a>
        </header>
        <main id="main">
            <section class="page-hero {hero_class}">
                <div class="hero-copy"><h1>{title}</h1>{('<p class="subtitle">' + escape(subtitle) + '</p>') if subtitle else ''}{hero_extra}</div>
            </section>
            {content}
        </main>
    </div>
</body>
</html>"""


def poster(url, title, css_class="", lazy=True):
    return f'<img src="{escape(url, quote=True)}" alt="{escape(str(title), quote=True)}" class="{css_class}" {"loading=lazy" if lazy else ""} decoding="async">'


def safe_return_path(value):
    try:
        parts = urlsplit(value)
    except ValueError:
        return '/'
    if parts.scheme or parts.netloc or parts.path not in ('/', '/search', '/bin') or '\\' in value or any(ord(character) < 32 for character in value):
        return '/'
    return value


def movie_anchor(title, year):
    return 'movie-' + hashlib.sha256(f'{title}|||{year}'.encode()).hexdigest()[:12]


def movie_link(title, return_to='/'):
    return '/movie?' + urlencode({'title': title, 'return_to': safe_return_path(return_to)})


def movie_card(rank, title, year, rating, poster_url, rating_text=None, return_to='/'):
    url_title = quote(str(title), safe="")
    safe_title = escape(str(title))
    confirmation = escape(json.dumps(f'Remove “{title}” from your collection?'), quote=True)
    anchor = movie_anchor(title, year)
    detail_url = escape(movie_link(title, return_to + '#' + anchor), quote=True)
    return f"""<article class="movie-card" id="{anchor}">
        <a class="poster-link" href="{detail_url}" data-movie-link><span class="rank-badge">{rank:02d}</span>{poster(poster_url, title)}<span class="poster-hint">View film {icon('arrow')}</span></a>
        <div class="movie-card-info"><div class="movie-meta"><span>{escape(str(year)) if year else 'Year unlisted'}</span><span class="elo-label">ELO</span></div>
        <a class="movie-card-title" href="{detail_url}" data-movie-link>{safe_title}</a>
        <div class="movie-card-bottom"><span class="movie-rating">{escape(rating_text) if rating_text else f'{rating:,.1f}'}</span><div class="card-actions">
            <a href="/vote?target={url_title}" class="card-action" aria-label="Vote on {escape(str(title), quote=True)}" title="Focused matchup">{icon('vote')}</a>
            <a href="{detail_url}" class="card-action" data-movie-link aria-label="Profile for {escape(str(title), quote=True)}" title="Film profile">{icon('chart')}</a>
            <a href="/delete?title={url_title}" class="card-action danger" data-confirm="{confirmation}" aria-label="Delete {escape(str(title), quote=True)}" title="Remove film">{icon('trash')}</a>
        </div></div></div>
    </article>"""


def empty_state(title, description, actions=True):
    return f"""<div class="empty-state"><div class="empty-symbol">{icon('film')}</div><h2>{escape(title)}</h2><p>{escape(description)}</p>
    {('<div class="empty-actions"><a class="button primary" href="/import">' + icon('data') + 'Import your ratings</a><a class="button secondary" href="/add">' + icon('plus') + 'Add a film</a></div>') if actions else ''}</div>"""


def empty_page(active, title, description):
    return page(title, description, active, empty_state("Add films to get started", "Add films individually or import a ratings CSV."))
