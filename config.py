# ==============================================================================
# CONFIGURATION & VISUAL THEMING
# ==============================================================================

# --- Server & API Settings ---
PORT = 8000
TMDB_API_KEY = "e2c94c95bdc86a424519046697bb28f0"
CACHE_FILE = "poster_cache.json"

# --- Elo Defaults ---
DEFAULT_ELO_MEAN = 1200.0
DEFAULT_ELO_STD = 200.0

# --- Visual Theme Colors (Hex Codes) ---
THEME_COLORS = {
    "bg_main": "#0f0617",
    "bg_card": "#1b0e2a",
    "bg_input": "#27143c",
    "border_color": "#3e1b5b",
    "border_highlight": "#c61f99",
    "text_primary": "#ede5f6",
    "text_secondary": "#cda4de",
    "accent_magenta": "#c61f99",
    "accent_pink": "#e893d2",
    "accent_plum": "#872655",
    "accent_blue": "#3a7ecc",
    "accent_dark_plum": "#4f0a2b",
    "btn_hover": "#e893d2",
    "btn_danger": "#ff4757",
    "btn_danger_bg": "#3a111a",
}

# --- Visual Element Sizes & Layout ---
UI_SIZES = {
    "card_width": "185px",
    "card_padding": "10px",
    "card_border_radius": "12px",
    "poster_height": "278px",
    "poster_detail_width": "220px",
    "poster_detail_height": "330px",
    "detail_card_max_width": "820px",
    "rank_container_max_width": "650px",
    "form_container_max_width": "450px",
    "stats_card_max_width": "1100px",
    "font_family": "'Segoe UI', Arial, sans-serif",
}

# --- Page Titles, Subtitles, and UI Text ---
TEXT_CONTENT = {
    # Gallery View
    "gallery_title": "Movie Poster Rankings",
    "gallery_subtitle": "Click any movie or view stats to see standard distribution bin placement!",

    # Rank 10 Cluster View
    "rank10_title": "Rank {count} Movies (Similar Elo Cluster)",
    "rank10_subtitle": "Drag & drop or use arrows to fine-tune order from #1 (Best) to #{count} (Worst)",
    "rank10_submit_btn": "Submit Ranking & Update Elo",
    "rank10_skip_btn": "➡ Get New Cluster",

    # Voting View
    "vote_title": "Which Movie is Better?",
    "vote_spotlight_label": "Focused Subcategory Mode:",

    # Stats Analytics View
    "stats_title": "Distribution Analytics",
    "stats_subtitle": "Click any bar on the graph to filter movies in that specific distribution's bin!",
    "stats_chart_title": "10-Bin Bell Curve Comparison Histogram",
    "stats_chart_desc": "Comparing Standard Normal Z-Score (σ), Method 1: Preserved Count Dist., and Method 2: Optimal L1 DP Cutoffs",

    # Add Movie View
    "add_title": "Add New Movie",
    "add_subtitle": "Enter a title and rating. Elo scales directly with standard normal z-scores!",
    "add_btn": "Add Movie & Start Matchups",

    # Search View
    "search_title": "Search Results",
    "search_placeholder": "Search movie...",
    "search_btn": "Search",

    # CSV Management View
    "import_title": "CSV Management",
    "import_subtitle": "Import external Letterboxd/ratings CSV files or export current database ratings",

    # Movie Analytics Profile
    "detail_title": "Movie Analytics Profile",
    "detail_subtitle": "Complete standard deviation and distribution profile",
}

# Standard Normal Distribution Bin Definitions (z-score units)
NORMAL_BIN_BOUNDS = [
    (-float("inf"), -2.0, "\nBin 1: < -2.0σ"),
    (-2.0, -1.5, "\n-2.0σ - -1.5σ"),
    (-1.5, -1.0, "\n-1.5σ - -1.0σ"),
    (-1.0, -0.5, "\n-1.0σ - -0.5σ"),
    (-0.5, 0.0, "\n-0.5σ - 0.0σ"),
    (0.0, 0.5, "\n0.0σ - +0.5σ"),
    (0.5, 1.0, "\n+0.5σ - +1.0σ"),
    (1.0, 1.5, "\n+1.0σ - +1.5σ"),
    (1.5, 2.0, "\n+1.5σ - +2.0σ"),
    (2.0, float("inf"), "\n>= +2.0σ"),
]


def get_color_css():
    """Generates CSS root variables based on configuration settings."""
    c = THEME_COLORS
    s = UI_SIZES
    return f"""
    :root {{
        --bg-main: {c['bg_main']};
        --bg-card: {c['bg_card']};
        --bg-input: {c['bg_input']};
        --border-color: {c['border_color']};
        --border-highlight: {c['border_highlight']};
        --text-primary: {c['text_primary']};
        --text-secondary: {c['text_secondary']};
        --accent-magenta: {c['accent_magenta']};
        --accent-pink: {c['accent_pink']};
        --accent-plum: {c['accent_plum']};
        --accent-blue: {c['accent_blue']};
        --accent-dark-plum: {c['accent_dark_plum']};
        --btn-hover: {c['btn_hover']};
        --btn-danger: {c['btn_danger']};
        --btn-danger-bg: {c['btn_danger_bg']};
    }}
    body {{ font-family: {s['font_family']}; background: var(--bg-main); color: var(--text-primary); padding: 20px; margin: 0; }}
    h1, h2, h3 {{ text-align: center; color: var(--text-primary); margin-bottom: 8px; }}
    .subtitle {{ text-align: center; color: var(--text-secondary); margin-bottom: 25px; font-size: 14px; }}
    .nav-bar {{ display: flex; justify-content: center; align-items: center; gap: 12px; margin-bottom: 25px; flex-wrap: wrap; }}
    .nav-link {{ text-decoration: none; color: var(--text-secondary); font-weight: 600; font-size: 14px; padding: 8px 16px; border-radius: 8px; background: var(--bg-card); border: 1px solid var(--border-color); transition: all 0.2s ease; }}
    .nav-link.active, .nav-link:hover {{ color: #ffffff; background: var(--accent-plum); border-color: var(--accent-pink); }}
    .search-form {{ display: flex; gap: 6px; margin-left: 10px; }}
    .search-input {{ padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-input); color: var(--text-primary); font-size: 14px; outline: none; }}
    .search-input:focus {{ border-color: var(--accent-pink); }}
    .search-btn {{ padding: 8px 14px; border-radius: 8px; border: none; background: var(--accent-magenta); color: white; font-weight: bold; cursor: pointer; transition: background 0.2s; }}
    .search-btn:hover {{ background: var(--btn-hover); color: #000; }}
    """