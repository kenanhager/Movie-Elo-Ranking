import csv
import http.server
import math
import os
import socketserver
from urllib.parse import parse_qs, urlparse
import requests

TMDB_API_KEY = "e2c94c95bdc86a424519046697bb28f0"  # Replace with your TMDB API Key
PORT = 8000
POSTER_CACHE = {}
movie_elo = []

# Load movies from CSV
with open("save.csv", "r", newline="", encoding="utf-8") as file:
  read = csv.reader(file)
  for row in read:
    if len(row) >= 2:
      title = row[0]
      rating = float(row[1])
      movie_elo.append([title, rating])


def get_poster_url(movie_item, api_key):
  """Searches TMDB for a movie poster with in-memory caching."""
  title = str(movie_item[0]).strip()

  if title in POSTER_CACHE:
    return POSTER_CACHE[title]

  url = "https://api.themoviedb.org/3/search/movie"
  params = {"api_key": api_key, "query": title}

  if (
      len(movie_item) > 2
      and str(movie_item[2]).isdigit()
      and len(str(movie_item[2])) == 4
  ):
    params["year"] = str(movie_item[2])

  try:
    res = requests.get(url, params=params, timeout=5).json()
    results = res.get("results", [])
    if results and results[0].get("poster_path"):
      poster_url = (
          f"https://image.tmdb.org/t/p/w185{results[0]['poster_path']}"
      )
      POSTER_CACHE[title] = poster_url
      return poster_url
  except Exception as e:
    print(f"Error fetching {title}: {e}")

  fallback_url = "https://via.placeholder.com/185x278?text=No+Poster"
  POSTER_CACHE[title] = fallback_url
  return fallback_url


def generate_gallery(movies_data, api_key, page=1, per_page=100):
  """Generates HTML gallery string for a specific page."""
  total_movies = len(movies_data)
  total_pages = max(1, math.ceil(total_movies / per_page))
  page = max(1, min(page, total_pages))

  start_idx = (page - 1) * per_page
  end_idx = min(start_idx + per_page, total_movies)
  page_movies = movies_data[start_idx:end_idx]

  print(
      f"Loading page {page}/{total_pages} (Movies {start_idx + 1} to"
      f" {end_idx})..."
  )

  cards_html = ""
  for i, item in enumerate(page_movies):
    rank = start_idx + i + 1
    title = item[0]
    rating = item[1] if len(item) > 1 else None
    poster_url = get_poster_url(item, api_key)

    rating_html = (
        f'<div class="rating">Rating: {rating:.1f}</div>'
        if rating is not None
        else ""
    )

    cards_html += f"""
        <div class="card">
            <div class="badge">#{rank}</div>
            <img src="{poster_url}" alt="{title}">
            <div class="title">{title}</div>
            {rating_html}
        </div>
        """

  # Navigation Buttons
  prev_btn = (
      f'<a href="/?page={page - 1}" class="btn">← Previous</a>'
      if page > 1
      else '<span class="btn disabled">← Previous</span>'
  )
  next_btn = (
      f'<a href="/?page={page + 1}" class="btn">Next →</a>'
      if page < total_pages
      else '<span class="btn disabled">Next →</span>'
  )

  pagination_html = f"""
    <div class="pagination">
        {prev_btn}
        <span class="page-info">Page {page} of {total_pages} ({total_movies} Total Movies)</span>
        {next_btn}
    </div>
    """

  return f"""<!DOCTYPE html>
<html>
<head>
    <title>Movie Poster Gallery</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #121212; color: white; padding: 20px; margin: 0; }}
        h1 {{ text-align: center; margin-bottom: 10px; }}
        .grid {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; margin-top: 20px; }}
        .card {{ 
            position: relative; 
            background: #1e1e1e; 
            padding: 10px; 
            border-radius: 8px; 
            width: 185px; 
            text-align: center; 
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            transition: transform 0.2s ease;
        }}
        .card:hover {{ transform: translateY(-5px); }}
        .badge {{ 
            position: absolute; 
            top: 15px; 
            left: 15px; 
            background: rgba(0, 0, 0, 0.85); 
            color: #ffcc00; 
            font-weight: bold; 
            font-size: 13px; 
            padding: 4px 8px; 
            border-radius: 4px; 
            border: 1px solid #ffcc00; 
            z-index: 2;
        }}
        .card img {{ width: 100%; height: 278px; object-fit: cover; border-radius: 4px; }}
        .title {{ font-size: 14px; font-weight: bold; margin-top: 8px; word-wrap: break-word; }}
        .rating {{ font-size: 12px; color: #aaaaaa; margin-top: 4px; }}
        .pagination {{ display: flex; justify-content: center; align-items: center; gap: 15px; margin: 25px 0; }}
        .btn {{ 
            padding: 8px 16px; 
            border-radius: 5px; 
            text-decoration: none; 
            font-weight: bold; 
            background-color: #007bff; 
            color: white; 
            transition: background 0.2s;
        }}
        .btn:hover:not(.disabled) {{ background-color: #0056b3; }}
        .btn.disabled {{ background-color: #333333; color: #777777; cursor: not-allowed; }}
        .page-info {{ font-size: 15px; color: #cccccc; }}
    </style>
</head>
<body>
    <h1>Movie Poster Gallery</h1>
    {pagination_html}
    <div class="grid">
        {cards_html}
    </div>
    {pagination_html}
</body>
</html>
"""


class GalleryRequestHandler(http.server.SimpleHTTPRequestHandler):

  movies_data = []
  api_key = ""

  def do_GET(self):
    parsed = urlparse(self.path)
    if parsed.path in ["/", "/index.html"]:
      query_params = parse_qs(parsed.query)
      try:
        page = int(query_params.get("page", [1])[0])
      except (ValueError, TypeError):
        page = 1

      html_content = generate_gallery(
          self.movies_data, self.api_key, page=page, per_page=100
      )

      self.send_response(200)
      self.send_header("Content-Type", "text/html; charset=utf-8")
      self.end_headers()
      self.wfile.write(html_content.encode("utf-8"))
    else:
      super().do_GET()


if __name__ == "__main__":
  # Sort descending by ELO rating so #1 is the top rank
  movie_elo.sort(key=lambda x: x[1], reverse=True)

  api_key = (
      input("Enter TMDB API Key (or press Enter to use default): ").strip()
      or TMDB_API_KEY
  )

  # Write initial page 1 index.html
  initial_html = generate_gallery(movie_elo, api_key, page=1, per_page=100)
  with open("index.html", "w", encoding="utf-8") as f:
    f.write(initial_html)

  # Configure custom HTTP request handler
  GalleryRequestHandler.movies_data = movie_elo
  GalleryRequestHandler.api_key = api_key

  print(f"\nServer running at http://localhost:{PORT}")
  print("Click 'Open in Browser' in the Codespaces prompt below.")

  os.chdir(os.path.dirname(os.path.abspath(__file__)))
  with socketserver.TCPServer(("", PORT), GalleryRequestHandler) as httpd:
    httpd.serve_forever()