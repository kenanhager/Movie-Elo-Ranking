import hashlib
import json
import re
from html import escape
from urllib.parse import quote, urlencode, urlsplit

from config import TEXT_CONTENT, get_color_css
from state import AppState


ICON_PATHS = {
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "list": '<path d="M9 5h12M9 12h12M9 19h12M3 5h1.5M3 12h1.5M3 19h1.5"/>',
    "vote": '<path d="m4 7 4-4 4 4M8 3v18m12-4-4 4-4-4m4 4V3"/>',
    "rank": '<path d="M8 5h13M8 12h10M8 19h7M3 5h1.5M3 12h1.5M3 19h1.5"/>',
    "chart": '<path d="M4 3v18h17M8 16v-5m5 5V6m5 10V9"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "data": '<path d="M12 3v12m-4-4 4 4 4-4M5 15v5h14v-5"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    "arrow": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    "left": '<path d="M20 12H4m6-6-6 6 6 6"/>',
    "trash": '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
    "film": '<rect x="3" y="3" width="18" height="18" rx="2.5"/><path d="M7 3v18M17 3v18M3 8h4m-4 8h4M17 8h4m-4 8h4"/>',
    "up": '<path d="m6 15 6-6 6 6"/>',
    "down": '<path d="m6 9 6 6 6-6"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "close": '<path d="m6 6 12 12M6 18 18 6"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3 2.5c-.5.2-.5 1-.5 1.5M12 17h.01"/>',
    "undo": '<path d="M8 4 3 9l5 5M3 9h10a6 6 0 0 1 0 12"/>',
}


APP_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;1,400;1,600&family=JetBrains+Mono:wght@500;600&display=swap');

:root {
    --bg-base: #0b0c0e;
    --bg-elevated: #121418;
    --bg-card: #171a20;
    --bg-card-hover: #1e222a;
    --bg-glass: rgba(18, 20, 24, 0.82);
    --border-subtle: rgba(255, 255, 255, 0.07);
    --border-strong: rgba(255, 255, 255, 0.14);
    --border-accent: rgba(229, 169, 60, 0.45);
    --text-main: #f3f4f6;
    --text-secondary: #9ca3af;
    --text-muted: #646b78;
    --accent: #e5a93c;
    --accent-hover: #f0b952;
    --accent-soft: rgba(229, 169, 60, 0.14);
    --green: #34d399;
    --green-soft: rgba(52, 211, 153, 0.14);
    --blue: #60a5fa;
    --blue-soft: rgba(96, 165, 250, 0.14);
    --danger: #f87171;
    --danger-soft: rgba(248, 113, 113, 0.14);
    --sidebar-w: 260px;
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 22px;
    --shadow-sm: 0 4px 12px rgba(0, 0, 0, 0.25);
    --shadow-md: 0 10px 30px rgba(0, 0, 0, 0.45);
    --shadow-lg: 0 20px 50px rgba(0, 0, 0, 0.65);
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-serif: 'Playfair Display', Georgia, serif;
    --font-mono: 'JetBrains Mono', monospace;
}

*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    background-color: var(--bg-base);
    color: var(--text-main);
    font-family: var(--font-sans);
    font-size: 16px;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
    scroll-behavior: smooth;
}

body {
    min-height: 100vh;
    background:
        radial-gradient(circle at 15% 0%, rgba(229, 169, 60, 0.06), transparent 40%),
        radial-gradient(circle at 85% 10%, rgba(96, 165, 250, 0.04), transparent 40%),
        var(--bg-base);
    display: flex;
    overflow-x: hidden;
}

a {
    color: inherit;
    text-decoration: none;
    transition: color 0.18s ease, background-color 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}

img {
    display: block;
    max-width: 100%;
}

.sr-only, .skip-link {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

.skip-link:focus {
    clip: auto;
    width: auto;
    height: auto;
    margin: 1rem;
    padding: 0.6rem 1rem;
    background: var(--accent);
    color: #000;
    font-weight: 600;
    border-radius: var(--radius-sm);
    z-index: 9999;
}

.icon {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
}

/* SIDEBAR NAVIGATION (COLLAPSIBLE ON DESKTOP & MOBILE) */
.sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: var(--sidebar-w);
    background: var(--bg-elevated);
    border-right: 1px solid var(--border-subtle);
    padding: 1.5rem 1rem;
    display: flex;
    flex-direction: column;
    z-index: 100;
    overflow-y: auto;
    transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
}

.sidebar::before {
    content: "CINE·ELO";
    display: block;
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.9rem;
    letter-spacing: 0.18em;
    color: var(--accent);
    padding: 0.35rem 2.75rem 1.4rem 0.75rem;
    border-bottom: 1px solid var(--border-subtle);
    margin-bottom: 1.25rem;
}

.icon-button.nav-close {
    position: absolute;
    top: 1.25rem;
    right: 1rem;
}

/* When sidebar is open on desktop, hide the redundant hamburger button in topbar */
body:not(.sidebar-collapsed) .icon-button.menu-toggle {
    display: none;
}

/* When sidebar is collapsed on desktop, slide it off-screen and expand main content */
body.sidebar-collapsed .sidebar {
    transform: translateX(-100%);
}

body.sidebar-collapsed .app-content {
    margin-left: 0;
}

.nav-group {
    margin-bottom: 1.5rem;
}

.nav-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 0 0.75rem;
    margin-bottom: 0.45rem;
}

.nav-link {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.62rem 0.75rem;
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    font-size: 0.92rem;
    font-weight: 500;
    position: relative;
    margin-bottom: 2px;
}

.nav-link:hover {
    color: var(--text-main);
    background: rgba(255, 255, 255, 0.04);
}

.nav-link.active {
    color: var(--accent);
    background: var(--accent-soft);
    font-weight: 600;
}

.nav-dot {
    margin-left: auto;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent);
}

/* MAIN LAYOUT & TOPBAR */
.app-content {
    flex: 1;
    margin-left: var(--sidebar-w);
    min-width: 0;
    display: flex;
    flex-direction: column;
    transition: margin-left 0.28s cubic-bezier(0.16, 1, 0.3, 1);
}

.topbar {
    position: sticky;
    top: 0;
    z-index: 80;
    height: 68px;
    background: var(--bg-glass);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border-subtle);
    padding: 0 2.25rem;
    display: flex;
    align-items: center;
    gap: 1.25rem;
}

.breadcrumb {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.88rem;
    color: var(--text-secondary);
    white-space: nowrap;
}

.breadcrumb a:hover {
    color: var(--text-main);
}

.breadcrumb span:last-child {
    color: var(--text-main);
    font-weight: 600;
}

.search-form {
    margin-left: auto;
    position: relative;
    width: 100%;
    max-width: 340px;
    display: flex;
    align-items: center;
}

.search-btn {
    position: absolute;
    left: 0.75rem;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    display: flex;
    align-items: center;
}

.search-input {
    width: 100%;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border-subtle);
    border-radius: 999px;
    padding: 0.5rem 1rem 0.5rem 2.4rem;
    color: var(--text-main);
    font-family: var(--font-sans);
    font-size: 0.88rem;
    transition: all 0.2s ease;
}

.search-input::placeholder {
    color: var(--text-muted);
}

.search-input:focus {
    outline: none;
    background: rgba(255, 255, 255, 0.07);
    border-color: var(--border-accent);
    box-shadow: 0 0 0 3px rgba(229, 169, 60, 0.12);
}

.topbar-add {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.5rem 0.95rem;
    border-radius: 999px;
    background: var(--accent-soft);
    border: 1px solid var(--border-accent);
    color: var(--accent);
    font-size: 0.85rem;
    font-weight: 600;
    white-space: nowrap;
}

.topbar-add:hover {
    background: var(--accent);
    color: #0b0c0e;
}

main {
    width: 100%;
    max-width: 1360px;
    margin: 0 auto;
    padding: 2.25rem 2.25rem 4rem;
}

/* HERO SECTION */
.page-hero {
    margin-bottom: 2.25rem;
    padding-bottom: 1.75rem;
    border-bottom: 1px solid var(--border-subtle);
}

.hero-copy h1 {
    font-family: var(--font-serif);
    font-size: clamp(2rem, 3.5vw, 2.85rem);
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -0.02em;
    color: var(--text-main);
}

.hero-copy h1 em {
    font-style: italic;
    font-weight: 400;
    color: var(--accent);
}

.hero-copy .subtitle {
    margin-top: 0.65rem;
    font-size: 1.02rem;
    color: var(--text-secondary);
    max-width: 68ch;
}

.hero-actions {
    margin-top: 1.35rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
}

/* BUTTONS & CONTROLS */
.button, button.button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.65rem 1.2rem;
    border-radius: var(--radius-sm);
    font-family: var(--font-sans);
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.18s ease;
    text-decoration: none;
    line-height: 1.2;
}

.button.primary {
    background: var(--accent);
    color: #0b0c0e;
    box-shadow: 0 2px 10px rgba(229, 169, 60, 0.25);
}

.button.primary:hover:not(:disabled) {
    background: var(--accent-hover);
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(229, 169, 60, 0.35);
}

.button.secondary {
    background: var(--bg-card);
    color: var(--text-main);
    border-color: var(--border-strong);
}

.button.secondary:hover:not(:disabled) {
    background: var(--bg-card-hover);
    border-color: rgba(255, 255, 255, 0.25);
}

.button.danger {
    background: var(--danger-soft);
    color: var(--danger);
    border-color: rgba(248, 113, 113, 0.3);
}

.button.danger:hover:not(:disabled) {
    background: var(--danger);
    color: #0b0c0e;
}

.button.full-width {
    width: 100%;
}

.button.disabled, .button:disabled {
    opacity: 0.45;
    cursor: not-allowed;
    pointer-events: none;
}

.icon-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: var(--radius-sm);
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
}

.icon-button:hover, .icon-button[aria-pressed="true"] {
    color: var(--accent);
    border-color: var(--border-accent);
    background: var(--accent-soft);
}

/* COLLECTION OVERVIEW STATS */
.collection-summary, .stats-summary {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.15rem;
    margin-bottom: 2.25rem;
}

.collection-stat, .stat-card {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.01) 100%), var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 1.25rem 1.4rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: var(--shadow-sm);
}

.metric-label, .stat-card .label {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
    margin-bottom: 0.5rem;
}

.metric-value, .stat-card .val {
    font-family: var(--font-mono);
    font-size: 1.75rem;
    font-weight: 600;
    color: var(--text-main);
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
}

.metric-value small {
    font-size: 0.85rem;
    color: var(--text-muted);
    font-weight: 500;
}

.top-film-value {
    font-family: var(--font-serif);
    font-size: 1.35rem;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--accent);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.top-film-value:hover {
    color: var(--accent-hover);
}

/* TOOLBAR */
.section-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 1.35rem;
}

.section-title {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.section-title h2 {
    font-size: 1.25rem;
    font-weight: 600;
}

.count-pill {
    font-family: var(--font-mono);
    font-size: 0.78rem;
    padding: 0.2rem 0.65rem;
    border-radius: 999px;
    background: var(--accent-soft);
    color: var(--accent);
    border: 1px solid var(--border-accent);
}

.toolbar-controls {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.sort-label {
    font-size: 0.85rem;
    color: var(--text-secondary);
}

.view-toggle {
    display: inline-flex;
    gap: 0.35rem;
    background: var(--bg-elevated);
    padding: 0.25rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-subtle);
}

/* MOVIE POSTER GRID & LIST VIEW */
.movie-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(185px, 1fr));
    gap: 1.35rem;
}

.movie-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
    box-shadow: var(--shadow-sm);
}

.movie-card:hover {
    transform: translateY(-4px);
    border-color: var(--border-strong);
    box-shadow: var(--shadow-md);
}

.poster-link {
    position: relative;
    aspect-ratio: 2 / 3;
    background: #0d0f12;
    overflow: hidden;
    display: block;
}

.poster-link img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.35s ease;
}

.movie-card:hover .poster-link img {
    transform: scale(1.04);
}

.rank-badge {
    position: absolute;
    top: 0.65rem;
    left: 0.65rem;
    z-index: 2;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    font-weight: 700;
    padding: 0.22rem 0.55rem;
    border-radius: 6px;
    background: rgba(11, 12, 14, 0.85);
    backdrop-filter: blur(8px);
    color: var(--accent);
    border: 1px solid var(--border-accent);
}

.poster-hint {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(11, 12, 14, 0.92) 0%, rgba(11, 12, 14, 0.2) 60%, transparent 100%);
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding: 1rem;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-main);
    gap: 0.35rem;
    opacity: 0;
    transition: opacity 0.22s ease;
}

.movie-card:hover .poster-hint {
    opacity: 1;
}

.movie-card-info {
    padding: 0.9rem;
    display: flex;
    flex-direction: column;
    flex: 1;
    gap: 0.35rem;
}

.movie-meta {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: var(--text-muted);
    font-family: var(--font-mono);
}

.movie-card-title {
    font-weight: 600;
    font-size: 0.96rem;
    line-height: 1.3;
    color: var(--text-main);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin-bottom: 0.35rem;
}

.movie-card-title:hover {
    color: var(--accent);
}

.movie-card-bottom {
    margin-top: auto;
    padding-top: 0.6rem;
    border-top: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.4rem;
}

.movie-rating {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--accent);
}

.card-actions {
    display: flex;
    gap: 0.25rem;
}

.card-action {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    background: rgba(255, 255, 255, 0.03);
}

.card-action .icon {
    width: 15px;
    height: 15px;
}

.card-action:hover {
    color: var(--text-main);
    background: rgba(255, 255, 255, 0.1);
}

.card-action.danger:hover {
    color: var(--danger);
    background: var(--danger-soft);
}

/* LIST VIEW MODE */
.movie-grid.list-view {
    grid-template-columns: 1fr;
    gap: 0.6rem;
}

.movie-grid.list-view .movie-card {
    flex-direction: row;
    align-items: center;
    padding: 0.55rem 1rem;
    transform: none;
}

.movie-grid.list-view .poster-link {
    width: 48px;
    height: 72px;
    aspect-ratio: 2 / 3;
    border-radius: 6px;
    flex-shrink: 0;
}

.movie-grid.list-view .poster-hint {
    display: none;
}

.movie-grid.list-view .rank-badge {
    position: static;
    margin-right: 0.75rem;
}

.movie-grid.list-view .movie-card-info {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    padding: 0 0 0 1rem;
    gap: 1rem;
}

.movie-grid.list-view .movie-card-title {
    margin-bottom: 0;
    -webkit-line-clamp: 1;
    font-size: 1rem;
}

.movie-grid.list-view .movie-card-bottom {
    margin-top: 0;
    padding-top: 0;
    border-top: none;
    gap: 1.25rem;
}

/* PAGINATION */
.pagination {
    margin-top: 2.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
}

.page-info {
    font-size: 0.88rem;
    color: var(--text-secondary);
    font-family: var(--font-mono);
}

/* HEAD-TO-HEAD VOTE PAGE */
.spotlight-banner {
    background: var(--accent-soft);
    border: 1px solid var(--border-accent);
    border-radius: var(--radius-md);
    padding: 0.85rem 1.25rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    color: var(--accent);
}

.exit-spotlight {
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.3rem 0.7rem;
    border-radius: 6px;
    background: rgba(0, 0, 0, 0.25);
}

.matchup-container {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 2rem;
    max-width: 960px;
    margin: 0 auto 2rem;
}

.vote-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 1.35rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    position: relative;
    box-shadow: var(--shadow-md);
    transition: transform 0.22s ease, border-color 0.22s ease;
}

.vote-card:hover {
    transform: translateY(-4px);
    border-color: var(--border-accent);
}

.target-tag {
    position: absolute;
    top: 1.9rem;
    left: 1.9rem;
    z-index: 3;
    background: var(--accent);
    color: #000;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    letter-spacing: 0.08em;
}

.vote-card img {
    width: 100%;
    max-width: 280px;
    aspect-ratio: 2 / 3;
    object-fit: cover;
    border-radius: var(--radius-md);
    margin-bottom: 1.15rem;
    box-shadow: var(--shadow-sm);
}

.vote-title {
    font-family: var(--font-serif);
    font-size: 1.4rem;
    font-weight: 700;
    margin-bottom: 0.35rem;
}

.vote-meta {
    display: flex;
    gap: 0.85rem;
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 1.25rem;
}

.vote-card form {
    width: 100%;
}

.vs {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: var(--bg-elevated);
    border: 1px solid var(--border-strong);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-serif);
    font-style: italic;
    font-size: 1.15rem;
    color: var(--accent);
    box-shadow: var(--shadow-sm);
}

.controls {
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: 0.85rem;
}

/* RANK 10 CLUSTER PAGE */
.rank-container {
    max-width: 780px;
    margin: 0 auto;
}

.rank-intro {
    display: flex;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
    margin-bottom: 0.85rem;
    padding: 0 0.25rem;
}

.rank-list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    margin-bottom: 1.75rem;
}

.rank-item {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 0.65rem 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    cursor: grab;
    transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.rank-item:hover {
    border-color: var(--border-strong);
    background: var(--bg-card-hover);
}

.rank-item.dragging {
    opacity: 0.55;
    border-color: var(--accent);
    transform: scale(0.99);
}

.rank-num {
    font-family: var(--font-mono);
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--accent);
    width: 2rem;
    text-align: center;
}

.rank-item img {
    width: 44px;
    height: 66px;
    object-fit: cover;
    border-radius: 6px;
    flex-shrink: 0;
}

.item-info {
    flex: 1;
    min-width: 0;
}

.item-title {
    font-weight: 600;
    font-size: 1rem;
    color: var(--text-main);
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.item-year {
    font-size: 0.82rem;
    font-weight: 400;
    color: var(--text-muted);
    font-family: var(--font-mono);
}

.item-elo {
    font-family: var(--font-mono);
    font-size: 0.82rem;
    color: var(--text-secondary);
    margin-top: 0.15rem;
}

.btn-group {
    display: flex;
    gap: 0.35rem;
}

.btn-move {
    width: 34px;
    height: 34px;
    border-radius: 8px;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    color: var(--text-secondary);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.btn-move:hover {
    color: var(--accent);
    border-color: var(--border-accent);
    background: var(--accent-soft);
}

.submit-container {
    display: flex;
    gap: 0.85rem;
    justify-content: flex-end;
}

/* MOVIE DETAIL PROFILE */
.gallery-back {
    margin-bottom: 1.5rem;
}

.detail-card {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 2.5rem;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    padding: 2rem;
    box-shadow: var(--shadow-md);
}

.detail-poster > img {
    width: 100%;
    aspect-ratio: 2 / 3;
    object-fit: cover;
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    margin-bottom: 1rem;
}

.poster-editor {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
}

.poster-editor summary {
    padding: 0.75rem 1rem;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
    list-style: none;
    color: var(--text-secondary);
}

.poster-editor summary::-webkit-details-marker {
    display: none;
}

.poster-editor summary:hover {
    color: var(--text-main);
}

.poster-editor-body {
    padding: 1rem;
    border-top: 1px solid var(--border-subtle);
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.poster-help {
    font-size: 0.78rem;
    color: var(--text-muted);
}

.poster-divider {
    text-align: center;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin: 0.5rem 0;
}

.poster-preview {
    margin: 0.5rem 0;
    text-align: center;
}

.poster-preview img {
    max-height: 180px;
    margin: 0 auto 0.35rem;
    border-radius: var(--radius-sm);
}

.detail-content .movie-title {
    font-family: var(--font-serif);
    font-size: 2.25rem;
    line-height: 1.15;
    margin-bottom: 0.35rem;
}

.detail-content .movie-year {
    font-family: var(--font-mono);
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-bottom: 1rem;
}

.placement-label {
    display: inline-block;
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    background: var(--accent-soft);
    border: 1px solid var(--border-accent);
    color: var(--accent);
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 1.5rem;
}

.profile-insights {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.75rem;
}

.profile-insight {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 1rem 1.15rem;
    display: flex;
    flex-direction: column;
}

.profile-insight span {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-secondary);
}

.profile-insight strong {
    font-family: var(--font-mono);
    font-size: 1.5rem;
    color: var(--text-main);
    margin: 0.25rem 0;
}

.profile-insight small {
    font-size: 0.78rem;
    color: var(--text-muted);
}

.nearby-section {
    margin-bottom: 1.75rem;
}

.nearby-section h2 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 0.75rem;
}

.neighbor-list {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 0.85rem;
}

.neighbor-film {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 0.65rem 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.85rem;
}

.neighbor-film:hover {
    border-color: var(--border-accent);
    background: var(--bg-card-hover);
}

.neighbor-film img {
    width: 42px;
    height: 63px;
    object-fit: cover;
    border-radius: 6px;
    flex-shrink: 0;
}

.neighbor-film > span {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
}

.neighbor-film small {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--accent);
}

.neighbor-film strong {
    font-size: 0.92rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.neighbor-film > span > span {
    font-size: 0.78rem;
    color: var(--text-muted);
}

.action-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 0.85rem;
}

/* ANALYTICS, HISTOGRAM & BINS */
.panel {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 1.75rem;
    margin-bottom: 1.75rem;
    box-shadow: var(--shadow-sm);
}

.chart-title, .panel h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.4rem;
}

.chart-desc {
    color: var(--text-secondary);
    font-size: 0.92rem;
    margin-bottom: 1.25rem;
}

.legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1.25rem;
    margin-bottom: 1.5rem;
    font-size: 0.85rem;
    color: var(--text-secondary);
}

.legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
}

.legend-box {
    width: 12px;
    height: 12px;
    border-radius: 3px;
    background: var(--accent);
    display: inline-block;
}

.legend-box.exact {
    background: var(--green);
}

.legend-box.optimal {
    background: var(--blue);
}

.chart-scroll {
    overflow-x: auto;
    padding-bottom: 0.5rem;
}

.histogram {
    display: grid;
    grid-template-columns: repeat(10, minmax(72px, 1fr));
    gap: 0.75rem;
    padding-top: 1.5rem;
    min-width: 720px;
}

.bar-column {
    display: flex;
    flex-direction: column;
    align-items: center;
}

.bar-wrapper {
    height: 230px;
    width: 100%;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    gap: 4px;
    position: relative;
    border-bottom: 1px solid var(--border-strong);
    padding: 0 4px;
}

.ideal-line {
    position: absolute;
    left: 0;
    right: 0;
    border-top: 2px dashed rgba(255, 255, 255, 0.28);
    pointer-events: none;
    z-index: 2;
}

.bar {
    flex: 1;
    max-width: 20px;
    border-radius: 4px 4px 0 0;
    position: relative;
    display: flex;
    justify-content: center;
    transition: opacity 0.15s ease, transform 0.15s ease;
}

.bar:hover {
    opacity: 0.9;
    transform: scaleY(1.02);
}

.bar-norm { background: var(--accent); }
.bar-exact { background: var(--green); }
.bar-optimal { background: var(--blue); }

.bar-count {
    position: absolute;
    top: -1.35rem;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    color: var(--text-secondary);
}

.bar-label {
    margin-top: 0.6rem;
    font-family: var(--font-mono);
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-main);
}

.bar-label:hover {
    color: var(--accent);
}

.bar-sublabel {
    font-size: 0.72rem;
    color: var(--text-muted);
    text-align: center;
}

.table-card {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
    font-size: 0.9rem;
}

th, td {
    padding: 0.85rem 1rem;
    text-align: left;
    border-bottom: 1px solid var(--border-subtle);
    vertical-align: top;
}

th {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    font-weight: 600;
}

td a.norm { color: var(--accent); font-family: var(--font-mono); }
td a.exact { color: var(--green); font-family: var(--font-mono); }
td a.optimal { color: var(--blue); font-family: var(--font-mono); }

.stat-caption {
    font-size: 0.78rem;
    color: var(--text-muted);
}

.sample-movies {
    color: var(--text-secondary);
    font-size: 0.85rem;
    max-width: 280px;
}

.sample-movies a {
    color: var(--accent);
    font-size: 0.8rem;
    font-weight: 500;
}

/* BIN CONTROLS */
.bin-controls {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 2rem;
}

.dist-toggle, .bin-selector {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.dist-btn, .bin-btn {
    padding: 0.5rem 0.95rem;
    border-radius: var(--radius-sm);
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-secondary);
}

.dist-btn:hover, .bin-btn:hover {
    color: var(--text-main);
    border-color: var(--border-strong);
}

.dist-btn.active-norm, .bin-btn.active {
    background: var(--accent-soft);
    border-color: var(--border-accent);
    color: var(--accent);
    font-weight: 600;
}

.dist-btn.active-exact {
    background: var(--green-soft);
    border-color: var(--green);
    color: var(--green);
    font-weight: 600;
}

.dist-btn.active-optimal {
    background: var(--blue-soft);
    border-color: var(--blue);
    color: var(--blue);
    font-weight: 600;
}

/* FORMS, ADD & IMPORT/EXPORT */
.form-container {
    max-width: 560px;
    margin: 0 auto;
}

.data-layout {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
    gap: 1.75rem;
}

.panel-heading {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin-bottom: 1.25rem;
    color: var(--accent);
}

.panel-heading h2 {
    color: var(--text-main);
    margin-bottom: 0;
}

.form-group {
    margin-bottom: 1.25rem;
}

label {
    display: block;
    font-size: 0.88rem;
    font-weight: 600;
    margin-bottom: 0.45rem;
    color: var(--text-main);
}

label span {
    font-weight: 400;
    color: var(--text-muted);
}

input[type="text"], input[type="number"], input[type="url"], select, input[type="file"] {
    width: 100%;
    padding: 0.68rem 0.9rem;
    border-radius: var(--radius-sm);
    background: var(--bg-elevated);
    border: 1px solid var(--border-strong);
    color: var(--text-main);
    font-family: var(--font-sans);
    font-size: 0.92rem;
    margin-bottom: 0.5rem;
}

input:focus, select:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(229, 169, 60, 0.14);
}

.rating-box {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.rating-val {
    font-family: var(--font-mono);
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--accent);
    white-space: nowrap;
}

.upload-area {
    border: 2px dashed var(--border-strong);
    border-radius: var(--radius-md);
    padding: 1.5rem;
    text-align: center;
    margin: 1rem 0 1.25rem;
    background: rgba(255, 255, 255, 0.015);
}

.upload-area .icon {
    width: 28px;
    height: 28px;
    color: var(--accent);
    margin: 0 auto 0.5rem;
}

.export-box {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 1.25rem;
    margin-top: 1rem;
}

.export-box h3 {
    font-size: 1rem;
    margin-bottom: 0.35rem;
}

.export-box p {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 1rem;
}

.form-note {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-top: 0.85rem;
    text-align: center;
}

/* GUIDE / HELP PAGE */
.guide-steps {
    list-style: none;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 1.25rem;
    margin-bottom: 2rem;
}

.guide-step {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    display: flex;
    gap: 1.15rem;
}

.guide-number {
    font-family: var(--font-mono);
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--accent);
}

.guide-step h2 {
    font-size: 1.1rem;
    margin-bottom: 0.45rem;
}

.guide-step p {
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin-bottom: 1rem;
}

.guide-link {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--accent);
}

.guide-notes p {
    color: var(--text-secondary);
    margin-top: 0.65rem;
    font-size: 0.92rem;
}

/* STATUS & EMPTY STATES */
.status-msg {
    background: var(--green-soft);
    border: 1px solid var(--green);
    color: var(--green);
    padding: 0.85rem 1.15rem;
    border-radius: var(--radius-md);
    margin-bottom: 1.5rem;
    font-size: 0.92rem;
    font-weight: 500;
}

.status-msg.error {
    background: var(--danger-soft);
    border-color: var(--danger);
    color: var(--danger);
}

.empty-state {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 3.5rem 2rem;
    text-align: center;
    max-width: 540px;
    margin: 2rem auto;
}

.empty-symbol {
    width: 54px;
    height: 54px;
    border-radius: 50%;
    background: var(--accent-soft);
    color: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 1rem;
}

.empty-symbol .icon {
    width: 26px;
    height: 26px;
}

.empty-state h2 {
    font-family: var(--font-serif);
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
}

.empty-state p {
    color: var(--text-secondary);
    margin-bottom: 1.5rem;
}

.empty-actions {
    display: flex;
    justify-content: center;
    gap: 0.75rem;
    flex-wrap: wrap;
}

/* RESPONSIVE BREAKPOINTS */
@media (max-width: 960px) {
    .sidebar {
        transform: translateX(-100%);
        box-shadow: var(--shadow-lg);
    }
    .sidebar.open {
        transform: translateX(0);
    }
    body:not(.sidebar-collapsed) .icon-button.menu-toggle {
        display: inline-flex;
    }
    .app-content {
        margin-left: 0;
    }
    .topbar {
        padding: 0 1.25rem;
    }
    main {
        padding: 1.5rem 1.25rem 3rem;
    }
    .collection-summary, .stats-summary, .profile-insights {
        grid-template-columns: 1fr;
    }
    .matchup-container {
        grid-template-columns: 1fr;
        gap: 1.25rem;
    }
    .vs {
        margin: 0 auto;
    }
    .detail-card {
        grid-template-columns: 1fr;
    }
    .detail-poster {
        max-width: 260px;
        margin: 0 auto;
    }
}
"""


APP_JS = """
document.addEventListener('DOMContentLoaded', () => {
    // 1. Sidebar collapse & expand (works on both desktop and mobile)
    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.querySelector('.menu-toggle');
    const navClose = document.querySelector('.nav-close');
    const isMobile = () => window.matchMedia('(max-width: 960px)').matches;

    if (!isMobile() && localStorage.getItem('cine_elo_sidebar') === 'collapsed') {
        document.body.classList.add('sidebar-collapsed');
    }

    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => {
            if (isMobile()) {
                const isOpen = sidebar.classList.toggle('open');
                menuToggle.setAttribute('aria-expanded', String(isOpen));
            } else {
                document.body.classList.remove('sidebar-collapsed');
                localStorage.setItem('cine_elo_sidebar', 'open');
                menuToggle.setAttribute('aria-expanded', 'true');
            }
        });
    }

    if (navClose && sidebar) {
        navClose.addEventListener('click', () => {
            if (isMobile()) {
                sidebar.classList.remove('open');
            } else {
                document.body.classList.add('sidebar-collapsed');
                localStorage.setItem('cine_elo_sidebar', 'collapsed');
            }
            if (menuToggle) menuToggle.setAttribute('aria-expanded', 'false');
        });
    }

    // 2. Grid / List view toggle with localStorage persistence
    const movieGrid = document.querySelector('.movie-grid');
    const viewButtons = document.querySelectorAll('.view-toggle [data-view]');
    const savedView = localStorage.getItem('cine_elo_view') || 'grid';

    function applyView(mode) {
        if (!movieGrid) return;
        movieGrid.classList.toggle('list-view', mode === 'list');
        viewButtons.forEach(btn => {
            btn.setAttribute('aria-pressed', String(btn.dataset.view === mode));
        });
        localStorage.setItem('cine_elo_view', mode);
    }

    if (viewButtons.length && movieGrid) {
        applyView(savedView);
        viewButtons.forEach(btn => {
            btn.addEventListener('click', () => applyView(btn.dataset.view));
        });
    }

    // 3. Delete confirmation prompts
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', (e) => {
            let msg = 'Are you sure?';
            try { msg = JSON.parse(el.getAttribute('data-confirm')); } catch (_) { msg = el.getAttribute('data-confirm'); }
            if (!window.confirm(msg)) {
                e.preventDefault();
            }
        });
    });

    // 4. Rank 10 cluster ordering (Up/Down buttons, Drag & Drop, and Form serialization)
    const rankList = document.getElementById('rank-list');
    const rankForm = document.getElementById('ranking-form');

    function renumberRankList() {
        if (!rankList) return;
        rankList.querySelectorAll('.rank-item').forEach((item, idx) => {
            const num = item.querySelector('.rank-num');
            if (num) num.textContent = String(idx + 1).padStart(2, '0');
        });
    }

    if (rankList) {
        rankList.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-move');
            if (!btn) return;
            const item = btn.closest('.rank-item');
            if (!item) return;
            if (btn.dataset.move === 'up' && item.previousElementSibling) {
                rankList.insertBefore(item, item.previousElementSibling);
                renumberRankList();
            } else if (btn.dataset.move === 'down' && item.nextElementSibling) {
                rankList.insertBefore(item.nextElementSibling, item);
                renumberRankList();
            }
        });

        let draggedItem = null;
        rankList.addEventListener('dragstart', (e) => {
            draggedItem = e.target.closest('.rank-item');
            if (draggedItem) draggedItem.classList.add('dragging');
        });
        rankList.addEventListener('dragend', () => {
            if (draggedItem) draggedItem.classList.remove('dragging');
            draggedItem = null;
            renumberRankList();
        });
        rankList.addEventListener('dragover', (e) => {
            e.preventDefault();
            if (!draggedItem) return;
            const afterElement = [...rankList.querySelectorAll('.rank-item:not(.dragging)')].reduce((closest, child) => {
                const box = child.getBoundingClientRect();
                const offset = e.clientY - box.top - box.height / 2;
                return (offset < 0 && offset > closest.offset) ? { offset, element: child } : closest;
            }, { offset: Number.NEGATIVE_INFINITY }).element;
            if (!afterElement) {
                rankList.appendChild(draggedItem);
            } else {
                rankList.insertBefore(draggedItem, afterElement);
            }
        });
    }

    if (rankForm && rankList) {
        rankForm.addEventListener('submit', () => {
            rankForm.querySelectorAll('input[type="hidden"]').forEach(i => i.remove());
            const items = [...rankList.querySelectorAll('.rank-item')];
            items.forEach((item, index) => {
                const title = item.getAttribute('data-title');
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'm' + index;
                input.value = title;
                rankForm.appendChild(input);
            });
            const orderInput = document.createElement('input');
            orderInput.type = 'hidden';
            orderInput.name = 'order';
            orderInput.value = items.map(i => i.getAttribute('data-title')).join('|||');
            rankForm.appendChild(orderInput);
        });
    }

    // 5. Add Film live rating display
    const ratingInput = document.getElementById('rating');
    const ratingDisp = document.getElementById('val-disp');
    if (ratingInput && ratingDisp) {
        ratingInput.addEventListener('input', () => {
            ratingDisp.textContent = `${ratingInput.value}/10`;
        });
    }

    // 6. Custom Poster live preview
    const posterFile = document.getElementById('poster-file');
    const posterUrl = document.getElementById('poster-url');
    const previewWrap = document.querySelector('.poster-preview');
    const previewImg = document.getElementById('poster-preview');

    if (posterFile && previewWrap && previewImg) {
        posterFile.addEventListener('change', () => {
            const file = posterFile.files && posterFile.files[0];
            if (file) {
                previewImg.src = URL.createObjectURL(file);
                previewWrap.hidden = false;
            }
        });
    }
    if (posterUrl && previewWrap && previewImg) {
        posterUrl.addEventListener('input', () => {
            const val = posterUrl.value.trim();
            if (val.startsWith('http://') || val.startsWith('https://')) {
                previewImg.src = val;
                previewWrap.hidden = false;
            } else {
                previewWrap.hidden = true;
            }
        });
    }
});
"""


def icon(name):
    return f'<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICON_PATHS[name]}</svg>'


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
        <button class="icon-button nav-close" aria-label="Collapse sidebar" title="Collapse sidebar">{icon('close')}</button>
        <nav>{links}</nav>
    </aside>"""


def page(title, subtitle, active, content, query="", eyebrow="", hero_extra="", hero_class=""):
    labels = {"rankings": "Rankings", "stats": "Analytics", "vote": "Match voting", "rank10": "Rank a cluster", "add": "Add a film", "import": "Import & export", "search": "Search", "detail": "Film profile", "help": "How to use"}
    eyebrow_html = f'<p class="nav-label" style="padding:0;margin-bottom:0.4rem;color:var(--accent)">{escape(eyebrow)}</p>' if eyebrow else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#0b0c0e">
    <title>{escape(re.sub('<[^>]+>', ' ', title)).strip()} · CineElo</title>
    <style>{get_color_css()}{APP_CSS}</style>
</head>
<body data-page="{active}">
    <a class="skip-link" href="#main">Skip to content</a>
    {header_nav(active)}
    <div class="app-content">
        <header class="topbar">
            <button class="icon-button menu-toggle" aria-label="Open navigation" title="Expand sidebar" aria-controls="sidebar" aria-expanded="true">{icon('menu')}</button>
            <div class="breadcrumb"><a href="/">Collection</a><span>/</span><span>{labels.get(active, 'Collection')}</span></div>
            <form action="/search" method="GET" class="search-form" role="search">
                <button type="submit" class="search-btn" aria-label="Search films">{icon('search')}</button>
                <input type="search" name="q" aria-label="Search your collection" placeholder="{TEXT_CONTENT['search_placeholder']}" value="{escape(query, quote=True)}" required class="search-input">
            </form>
            <a class="topbar-add" href="/add">{icon('plus')}<span>Add a film</span></a>
        </header>
        <main id="main">
            <section class="page-hero {hero_class}">
                <div class="hero-copy">{eyebrow_html}<h1>{title}</h1>{('<p class="subtitle">' + escape(subtitle) + '</p>') if subtitle else ''}{hero_extra}</div>
            </section>
            {content}
        </main>
    </div>
    <script>{APP_JS}</script>
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
        <a class="poster-link" href="{detail_url}" data-movie-link><span class="rank-badge">#{rank:02d}</span>{poster(poster_url, title)}<span class="poster-hint">View film {icon('arrow')}</span></a>
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
