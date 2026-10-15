import http.server
from http.server import ThreadingHTTPServer
import math
import os
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse
import webbrowser
from elopy import Implementation

from config import DEFAULT_ELO_MEAN, DEFAULT_ELO_STD, MAX_IMPORT_BYTES, MAX_POSTER_BYTES, PORT, POSTER_UPLOAD_DIR, TMDB_API_KEY
from posters import UPLOAD_NAME, get_poster_url, reset_custom_poster, save_custom_poster, save_poster_cache
from data_manager import (
    append_to_ratings_csv,
    disambiguate_titles,
    generate_export_csv,
    get_existing_movie_identities,
    get_movie_original_ratings,
    is_duplicate_movie,
    load_initial_data,
    load_poster_cache,
    process_ratings_csv_data,
    remove_movie_from_db,
    save_to_csv,
)
from state import AppState
from ui import safe_return_path
from voting import clear_vote_history, load_vote_history, record_vote, undo_vote
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
    generate_help_html,
)



class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/posters/'):
            self._serve_uploaded_poster(parsed.path, head_only=True)
        elif parsed.path == '/poster':
            self._resolve_poster(parse_qs(parsed.query).get('title', [''])[0])
        else:
            super().do_HEAD()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/poster':
            self._resolve_poster(parse_qs(parsed.query).get('title', [''])[0])
            return
        if parsed.path.startswith('/posters/'):
            self._serve_uploaded_poster(parsed.path)
            return
        if parsed.path.startswith('/static/'):
            super().do_GET()
            return
        with AppState.lock:
            self._do_app_GET()

    def _do_app_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/":
            page = self._integer(params.get("page", [1])[0], 1)
            html = generate_gallery_html(page=page)
            self._send_html(html)

        elif path == "/bin":
            bin_idx = self._integer(params.get("bin", [1])[0], 1) - 1
            method = params.get("method", ["norm"])[0]
            html = generate_bin_view_html(bin_idx=bin_idx, method=method)
            self._send_html(html)

        elif path == "/stats":
            html = generate_stats_html()
            self._send_html(html)

        elif path == '/help':
            self._send_html(generate_help_html())

        elif path == "/search":
            q = params.get("q", [""])[0]
            html = generate_search_html(query=q)
            self._send_html(html)

        elif path == "/movie":
            t = params.get("title", [""])[0]
            statuses = {'saved': 'Custom poster saved. It now appears throughout your collection.', 'reset': 'Automatic poster restored.'}
            html = generate_movie_detail_html(title_query=t, message=statuses.get(params.get('poster_status', [''])[0], ''), return_to=safe_return_path(params.get('return_to', ['/'])[0]))
            self._send_html(html)

        elif path == "/vote":
            winner = params.get("winner", [None])[0]
            m1_name = params.get("m1", [None])[0]
            m2_name = params.get("m2", [None])[0]
            target_name = params.get("target", [None])[0]

            if winner in ('1', '2', '3') and m1_name != m2_name and m1_name in AppState.elo.players and m2_name in AppState.elo.players:
                self._record_vote_response({key: values[0] for key, values in params.items()})
                return

            statuses = {'saved': 'Vote saved.', 'undone': 'Vote undone. Both previous scores have been restored.', 'duplicate': 'This vote was already saved.'}
            html = generate_vote_html(target_title=target_name, pair_titles=params.get('pair', []), message=statuses.get(params.get('status', [''])[0], ''))
            self._send_html(html)

        elif path == "/rank10":
            ranked_titles = params.get("ranked", [])
            if len(ranked_titles) > 10 or len(set(ranked_titles)) != len(ranked_titles) or any(title not in AppState.elo.players for title in ranked_titles):
                self.send_error(400, 'Choose up to ten distinct films from your collection.')
                return
            if len(ranked_titles) >= 2:
                n = len(ranked_titles)
                for i in range(n):
                    for j in range(i + 1, n):
                        AppState.elo.recordMatch(ranked_titles[i], ranked_titles[j], winner=ranked_titles[i])
                save_to_csv()
                clear_vote_history()

            html = generate_rank10_html()
            self._send_html(html)

        elif path == "/add":
            title = params.get("title", [None])[0]
            rating_val = params.get("rating", [None])[0]
            year_val = params.get("year", [""])[0]

            if title and rating_val:
                existing_identities = get_existing_movie_identities(AppState.movie_elo)
                if not is_duplicate_movie(title, year_val, existing_identities):
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
                        AppState.movie_elo = disambiguate_titles(AppState.movie_elo)

                        AppState.elo = Implementation()
                        for item in AppState.movie_elo:
                            AppState.elo.addPlayer(item[0], rating=item[1])
                        save_to_csv()
                        clear_vote_history()
                    except Exception as e:
                        print(f"Error adding movie: {e}")

            html = generate_add_html()
            self._send_html(html)

        elif path == "/import":
            html = generate_import_html()
            self._send_html(html)

        elif path == "/export":
            export_type = params.get("type", ["elo_data"])[0]
            method = params.get("method", ["norm"])[0]
            csv_data = generate_export_csv(export_type=export_type, method=method)

            if export_type == "letterboxd":
                filename = "letterboxd_data.csv"
            else:
                filename = "elo_data.csv"

            self.send_response(200)
            self.send_header("Content-type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(csv_data.encode("utf-8"))

        elif path == "/delete":
            t = params.get("title", [None])[0]
            if t:
                remove_movie_from_db(t)
                clear_vote_history()
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()

        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in ('/import', '/poster', '/vote', '/vote/undo'):
            self.send_error(404)
            return
        limit = MAX_IMPORT_BYTES if parsed.path == '/import' else MAX_POSTER_BYTES + 65536 if parsed.path == '/poster' else 65536
        try:
            fields, files = self._read_form(limit)
        except ValueError as error:
            self.send_error(400, str(error))
            return
        with AppState.lock:
            if parsed.path == '/vote':
                self._record_vote_response(fields)
                return
            if parsed.path == '/vote/undo':
                try:
                    previous = undo_vote(fields.get('vote_id', ''))
                except (ValueError, OSError) as error:
                    self._send_html(generate_vote_html(message=str(error), error=True))
                    return
                query = [('status', 'undone'), ('pair', previous['m1']), ('pair', previous['m2'])]
                if previous.get('target'):
                    query.append(('target', previous['target']))
                self._redirect('/vote?' + urlencode(query))
                return
            if parsed.path == '/poster':
                self._update_poster(fields, files)
                return
            try:
                content = files.get('csv_file', b'')
                csv_text = content.decode('utf-8-sig', errors='replace')
                if csv_text:
                    added, skipped = process_ratings_csv_data(csv_text)
                    clear_vote_history()
                    msg = f"Successfully imported {added} new movie(s) into database! ({skipped} existing titles retained)"
                else:
                    msg = "Error: Could not read uploaded CSV file data."
            except Exception as e:
                msg = f"Error processing CSV import: {e}"

            html = generate_import_html(message=msg)
            self._send_html(html)

    def _redirect(self, location):
        self.send_response(303)
        self.send_header('Location', location)
        self.end_headers()

    def _record_vote_response(self, fields):
        target = fields.get('target') or None
        try:
            saved = record_vote(fields.get('m1'), fields.get('m2'), fields.get('winner'), target, fields.get('vote_id'))
        except (ValueError, OSError) as error:
            self._send_html(generate_vote_html(target_title=target, message=str(error), error=True))
            return
        query = {'status': 'saved' if saved else 'duplicate'}
        if target:
            query['target'] = target
        self._redirect('/vote?' + urlencode(query))

    @staticmethod
    def _integer(value, fallback):
        try:
            return int(value)
        except (ValueError, TypeError):
            return fallback

    def _read_form(self, limit):
        try:
            size = int(self.headers.get('Content-Length', 0))
        except ValueError:
            raise ValueError('Invalid request size.')
        if size < 0 or size > limit:
            raise ValueError('The upload is too large. Choose a smaller file.')
        body = self.rfile.read(size)
        content_type = self.headers.get('Content-Type', '')
        if content_type.startswith('application/x-www-form-urlencoded'):
            return {key: values[0] for key, values in parse_qs(body.decode('utf-8'), keep_blank_values=True).items()}, {}
        if not content_type.startswith('multipart/form-data'):
            raise ValueError('Use an image upload or a form submission.')
        message = BytesParser(policy=default).parsebytes(('Content-Type: ' + content_type + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + body)
        if not message.is_multipart():
            raise ValueError('The upload could not be read. Choose the file again.')
        fields, files = {}, {}
        for part in message.iter_parts():
            name = part.get_param('name', header='content-disposition')
            if not name:
                continue
            payload = part.get_payload(decode=True) or b''
            if part.get_filename() is not None:
                files[name] = payload
            else:
                fields[name] = payload.decode('utf-8', errors='replace')
        return fields, files

    def _update_poster(self, fields, files):
        title = fields.get('title', '')
        return_to = safe_return_path(fields.get('return_to', '/'))
        movie = next((movie for movie in AppState.movie_elo if movie[0].casefold() == title.casefold()), None)
        if movie is None:
            self.send_error(404, 'Film not found in your collection.')
            return
        try:
            if fields.get('action') == 'reset':
                reset_custom_poster(movie[0], movie[2])
                status = 'reset'
            else:
                save_custom_poster(movie[0], movie[2], content=files.get('poster_file'), url=fields.get('poster_url', ''))
                status = 'saved'
        except (ValueError, OSError) as error:
            self._send_html(generate_movie_detail_html(title_query=movie[0], message=str(error), poster_error=True, return_to=return_to))
            return
        self._redirect('/movie?' + urlencode({'title': movie[0], 'poster_status': status, 'return_to': return_to}))

    def _resolve_poster(self, title):
        with AppState.lock:
            movie = next((tuple(movie) for movie in AppState.movie_elo if movie[0].casefold() == title.casefold()), None)
        if movie is None:
            self.send_error(404, 'Film not found in your collection.')
            return
        url = get_poster_url(movie[0], TMDB_API_KEY, movie[2])
        self.send_response(302)
        self.send_header('Location', url)
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()

    def _serve_uploaded_poster(self, path, head_only=False):
        filename = path.removeprefix('/posters/')
        if not UPLOAD_NAME.fullmatch(filename):
            self.send_error(404)
            return
        try:
            source = (Path(POSTER_UPLOAD_DIR) / filename).open('rb')
        except OSError:
            self.send_error(404)
            return
        with source:
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(filename))
            self.send_header('Content-Length', str(os.fstat(source.fileno()).st_size))
            self.send_header('Cache-Control', 'public, max-age=31536000, immutable')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            if not head_only:
                self.copyfile(source, self.wfile)

    def _send_html(self, html):
        content = html.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(content)


def main():
    load_poster_cache()
    load_initial_data()
    load_vote_history()

    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, RequestHandler)
    print(f"Server started at http://localhost:{PORT}")
    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except Exception:
        pass
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
        save_poster_cache()


if __name__ == "__main__":
    main()
