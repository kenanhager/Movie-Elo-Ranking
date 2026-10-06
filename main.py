import http.server
from http.server import ThreadingHTTPServer
import math
from urllib.parse import parse_qs, urlparse
import webbrowser

from config import DEFAULT_ELO_MEAN, DEFAULT_ELO_STD, PORT
from data_manager import (
    append_to_ratings_csv,
    generate_export_csv,
    get_movie_original_ratings,
    load_initial_data,
    load_poster_cache,
    process_ratings_csv_data,
    remove_movie_from_db,
    save_to_csv,
)
from state import AppState
from templates import (
    generate_add_html,
    generate_bin_view_html,
    generate_gallery_html,
    generate_import_html,
    generate_movie_detail_html,
    generate_rank10_html,
    generate_search_html,
    generate_stats_html,
    generate_vote_html,
)


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/":
            page = int(params.get("page", [1])[0])
            html = generate_gallery_html(page=page)
            self._send_html(html)

        elif path == "/bin":
            bin_idx = int(params.get("bin", [1])[0]) - 1
            method = params.get("method", ["norm"])[0]
            html = generate_bin_view_html(bin_idx=bin_idx, method=method)
            self._send_html(html)

        elif path == "/stats":
            html = generate_stats_html()
            self._send_html(html)

        elif path == "/search":
            q = params.get("q", [""])[0]
            html = generate_search_html(query=q)
            self._send_html(html)

        elif path == "/movie":
            t = params.get("title", [""])[0]
            html = generate_movie_detail_html(title_query=t)
            self._send_html(html)

        elif path == "/vote":
            winner = params.get("winner", [None])[0]
            m1_name = params.get("m1", [None])[0]
            m2_name = params.get("m2", [None])[0]
            target_name = params.get("target", [None])[0]

            if winner and m1_name and m2_name:
                if winner == "1":
                    AppState.elo.recordMatch(m1_name, m2_name, winner=m1_name)
                elif winner == "2":
                    AppState.elo.recordMatch(m1_name, m2_name, winner=m2_name)
                elif winner == "3":
                    AppState.elo.recordMatch(m1_name, m2_name, draw=True)
                save_to_csv()

            html = generate_vote_html(target_title=target_name)
            self._send_html(html)

        elif path == "/rank10":
            ranked_titles = params.get("ranked", [])
            if len(ranked_titles) >= 2:
                n = len(ranked_titles)
                for i in range(n):
                    for j in range(i + 1, n):
                        AppState.elo.recordMatch(ranked_titles[i], ranked_titles[j], winner=ranked_titles[i])
                save_to_csv()

            html = generate_rank10_html()
            self._send_html(html)

        elif path == "/add":
            title = params.get("title", [None])[0]
            rating_val = params.get("rating", [None])[0]
            year_val = params.get("year", [""])[0]

            if title and rating_val:
                append_to_ratings_csv([(title, rating_val, year_val)])
                try:
                    r_float = float(rating_val)
                    _, ratings_list = get_movie_original_ratings()
                    if ratings_list:
                        r_mean = sum(ratings_list) / len(ratings_list)
                        r_var = sum((r - r_mean) ** 2 for r in ratings_list) / len(ratings_list)
                        r_std = math.sqrt(r_var) if r_var > 0 else 1.0
                    else:
                        r_mean, r_std = 7.0, 1.5

                    z = (r_float - r_mean) / r_std if r_std else 0.0
                    scaled_elo = DEFAULT_ELO_MEAN + (z * DEFAULT_ELO_STD)

                    AppState.movie_elo.append([title, scaled_elo, year_val])
                    AppState.elo.addPlayer(title, rating=scaled_elo)
                    save_to_csv()
                except Exception as e:
                    print(f"Error adding movie: {e}")

            html = generate_add_html()
            self._send_html(html)

        elif path == "/import":
            html = generate_import_html()
            self._send_html(html)

        elif path == "/export":
            scale = params.get("scale", ["elo"])[0]
            csv_data = generate_export_csv(scale=scale)
            self.send_response(200)
            self.send_header("Content-type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="movie_ratings_export_{scale}.csv"')
            self.end_headers()
            self.wfile.write(csv_data.encode("utf-8"))

        elif path == "/delete":
            t = params.get("title", [None])[0]
            if t:
                remove_movie_from_db(t)
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()

        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/import":
            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))

            body = self.rfile.read(content_length)

            try:
                boundary = content_type.split("boundary=")[1].encode()
                parts = body.split(b"--" + boundary)
                csv_text = ""

                for part in parts:
                    if b'filename="' in part:
                        headers, content = part.split(b"\r\n\r\n", 1)
                        content = content.rsplit(b"\r\n", 1)[0]
                        csv_text = content.decode("utf-8", errors="ignore")
                        break

                if csv_text:
                    added, skipped = process_ratings_csv_data(csv_text)
                    msg = f"Successfully imported {added} new movie(s) into database! ({skipped} existing titles retained)"
                else:
                    msg = "Error: Could not read uploaded CSV file data."
            except Exception as e:
                msg = f"Error processing CSV import: {e}"

            html = generate_import_html(message=msg)
            self._send_html(html)

    def _send_html(self, html):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


def main():
    load_poster_cache()
    load_initial_data()

    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, RequestHandler)
    print(f"Server started at http://localhost:{PORT}")
    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except Exception:
        pass
    httpd.serve_forever()


if __name__ == "__main__":
    main()