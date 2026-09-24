# WSGI para PythonAnywhere. No uses "python app.py" en el Web tab.
import json
import os
import sys
import traceback
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import app as desk


def _qs(environ):
    return urllib.parse.parse_qs(environ.get("QUERY_STRING") or "")


def _json(payload, status="200 OK"):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Cache-Control", "no-store"),
        ("Content-Length", str(len(body))),
    ]
    return status, headers, body


def application(environ, start_response):
    path = environ.get("PATH_INFO") or "/"
    try:
        if path in ("/", "/index.html"):
            html = (desk.HTML
                    .replace("__TODAY__", json.dumps(desk.TODAY_22_09, ensure_ascii=False))
                    .replace("__TODAY_DATE__", desk.now_pe().strftime("%Y-%m-%d")))
            body = html.encode("utf-8")
            start_response("200 OK", [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Cache-Control", "no-store"),
                ("Content-Length", str(len(body))),
            ])
            return [body]
        if path in ("/favicon.svg", "/favicon.ico"):
            body = desk.FAVICON_SVG.encode("utf-8")
            start_response("200 OK", [
                ("Content-Type", "image/svg+xml; charset=utf-8"),
                ("Cache-Control", "public, max-age=86400"),
                ("Content-Length", str(len(body))),
            ])
            return [body]
        qs = _qs(environ)
        if path == "/api/calendar":
            date = (qs.get("date") or ["2026-09-24"])[0]
            status, headers, body = _json(desk.calendar_for_date(date))
        elif path == "/api/calendar-range":
            raw = (qs.get("dates") or [",".join(desk.upcoming_dates(8))])[0]
            dates = [d.strip() for d in raw.split(",") if d.strip()][:8]
            status, headers, body = _json(desk.calendar_range(dates))
        elif path == "/api/women-matches":
            date = (qs.get("date") or ["2026-09-24"])[0]
            status, headers, body = _json(desk.women_matches_for_date(date))
        elif path == "/api/league-table":
            lid = int((qs.get("id") or ["274"])[0] or 274)
            status, headers, body = _json(desk.fotmob_league_table(lid))
        elif path == "/api/prematch":
            home = (qs.get("home") or [""])[0].strip()
            away = (qs.get("away") or [""])[0].strip()
            date = (qs.get("date") or [desk.now_pe().strftime("%Y-%m-%d")])[0]
            status, headers, body = _json(desk.prematch_context(home, away, date))
        elif path == "/api/h2h":
            home = (qs.get("home") or [""])[0].strip()
            away = (qs.get("away") or [""])[0].strip()
            h2h = desk.h2h_summary(home, away)
            h2h["home"] = home
            h2h["away"] = away
            status, headers, body = _json(h2h)
        elif path == "/api/bettor-prematch":
            home = (qs.get("home") or [""])[0].strip()
            away = (qs.get("away") or [""])[0].strip()
            status, headers, body = _json(desk.bettor_prematch(home, away))
        elif path == "/api/team-stats":
            home = (qs.get("home") or [""])[0].strip()
            away = (qs.get("away") or [""])[0].strip()
            limit = min(20, max(5, int((qs.get("limit") or [20])[0])))
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=2) as pool:
                h = pool.submit(desk.summarize_team, home, limit, away).result()
                a = pool.submit(desk.summarize_team, away, limit, home).result()
            h["logo"] = desk.resolve_team_logo(home) or desk.logo_for(home)
            a["logo"] = desk.resolve_team_logo(away) or desk.logo_for(away)
            status, headers, body = _json({"home": h, "away": a, "source": h.get("source")})
        elif path == "/api/team-logo":
            name = (qs.get("name") or [""])[0].strip()
            status, headers, body = _json({"team": name, "logo": desk.resolve_team_logo(name)})
        elif path == "/api/matches":
            status, headers, body = _json(desk.ALL_MATCHES)
        else:
            body = b"Not Found"
            start_response("404 Not Found", [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))])
            return [body]
        start_response(status, headers)
        return [body]
    except Exception as e:
        payload = {"error": str(e), "trace": traceback.format_exc()[-800:]}
        status, headers, body = _json(payload, "500 Internal Server Error")
        start_response(status, headers)
        return [body]
