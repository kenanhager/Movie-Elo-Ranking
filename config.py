PORT = 8000
TMDB_API_KEY = "e2c94c95bdc86a424519046697bb28f0"
CACHE_FILE = "poster_cache.json"
CUSTOM_POSTER_FILE = "custom_posters.json"
POSTER_UPLOAD_DIR = "posters"
MAX_POSTER_BYTES = 8 * 1024 * 1024
MAX_IMPORT_BYTES = 32 * 1024 * 1024
VOTE_HISTORY_FILE = "vote_history.json"


DEFAULT_ELO_MEAN = 1200.0
DEFAULT_ELO_STD = 200.0


THEME_COLORS = {
    "bg_main": "#141514",
    "bg_card": "#1d1e1b",
    "bg_input": "#242520",
    "border_color": "#34352e",
    "border_highlight": "#d5ab66",
    "text_primary": "#f2eee5",
    "text_secondary": "#aaa99e",
    "accent_magenta": "#d5ab66",
    "accent_pink": "#e3c28c",
    "accent_plum": "#899c83",
    "accent_blue": "#93afbf",
    "accent_dark_plum": "#30291f",
    "btn_hover": "#e3c28c",
    "btn_danger": "#e19687",
    "btn_danger_bg": "#332420",
}


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
    "font_family": "'Avenir Next', Avenir, 'Segoe UI', sans-serif",
}


TEXT_CONTENT = {

    "gallery_title": "Movie rankings",
    "gallery_subtitle": "Browse your collection, compare films, and adjust their order.",


    "rank10_title": "Rank a cluster",
    "rank10_subtitle": "{count} films with similar Elo ratings. Drag to reorder, or use the arrows, from best to worst.",
    "rank10_submit_btn": "Save ranking & update Elo",
    "rank10_skip_btn": "Try another cluster",


    "vote_title": "Choose the better film",
    "vote_spotlight_label": "Focused matchup",


    "stats_title": "Collection analytics",
    "stats_subtitle": "Explore your ratings through three distribution methods. Select a bar to see the films behind it.",
    "stats_chart_title": "Rating distribution",
    "stats_chart_desc": "Ten bins, three perspectives. Dashed markers show the expected normal distribution.",


    "add_title": "Add a film",
    "add_subtitle": "Enter a title, release year, and starting rating.",
    "add_btn": "Add to collection",


    "search_title": "Search Results",
    "search_placeholder": "Find a film…",
    "search_btn": "Search",


    "import_title": "Import & export",
    "import_subtitle": "Import your Letterboxd ratings, or take your current rankings with you.",


    "detail_title": "Film profile",
    "detail_subtitle": "",
}


NORMAL_BIN_BOUNDS = [
    (-float("inf"), -2.0, "\n< -2.0σ"),
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
    :root {{ --font-sans: {s['font_family']}; }}
    """
