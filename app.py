#!/usr/bin/env python3
"""
Prematch Desk — app local (Python 3, sin dependencias).
Uso:  python3 app.py
Luego abrí http://127.0.0.1:8765
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import urllib.error
import webbrowser
import threading
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo=None

# Perú no usa DST. En Windows/Python embedido a menudo no existe tzdata.
PE_TZ = timezone(timedelta(hours=-5))
def _pe_tz():
    if ZoneInfo is not None:
        try:
            return ZoneInfo("America/Lima")
        except Exception:
            pass
    return PE_TZ

def now_pe():
    return datetime.now(tz=_pe_tz())
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST, PORT = os.environ.get("HOST","0.0.0.0"), int(os.environ.get("PORT","8765"))

def logo_api(cid):
    """Escudos públicos (API-Sports). Flashscore bloquea hotlink directo."""
    return f"https://media.api-sports.io/football/teams/{cid}.png"

# IDs API-Sports / equivalente a escudos Flashscore
IDS_FS = {
    # Inglaterra
    "Arsenal": 42, "Chelsea": 49, "Man United": 33, "Man City": 50,
    "Tottenham": 47, "Liverpool": 40, "Aston Villa": 66, "Newcastle": 34,
    "Everton": 45, "Brighton": 51, "Fulham": 36, "Crystal Palace": 52,
    "West Ham": 48, "Brentford": 55, "Nottm Forest": 65, "Bournemouth": 35,
    "Burnley": 44, "Leeds": 63, "Wolves": 39, "Sunderland": 56,
    "Blackburn": 59, "Sheffield United": 62, "Cardiff": 43, "Stoke": 75,
    "Southampton": 41, "Swansea": 76, "Watford": 38, "Preston": 77,
    "Wrexham": 1837, "Middlesbrough": 74, "Millwall": 78, "Bolton": 79,
    "Oxford": 80, "Reading": 53, "Hull": 64, "Coventry": 70,
    # España
    "Real Madrid": 541, "Barcelona": 529, "Atlético Madrid": 530,
    "Real Sociedad": 548, "Athletic": 531, "Sevilla": 536,
    "Villarreal": 533, "Valencia": 532, "Getafe": 546,
    "Celta Vigo": 538, "Elche": 797, "Espanyol": 540,
    "Alavés": 542, "Málaga": 543, "Levante": 539, "Rayo": 728,
    "Real Betis": 543, "Osasuna": 727,
    # Italia
    "Inter": 505, "AC Milan": 489, "Juventus": 496, "Napoli": 492,
    "Roma": 497, "Lazio": 487, "Atalanta": 499, "Fiorentina": 502,
    "Cagliari": 490, "Lecce": 867, "Udinese": 494, "Bologna": 500,
    "Parma": 523, "Monza": 1579, "Torino": 503, "Sassuolo": 488,
    "Frosinone": 495, "Venezia": 517, "Palermo": 518, "Sampdoria": 498,
    # Alemania / Francia / Portugal / Bélgica / Grecia
    "Bayern": 157, "Dortmund": 165, "Wolfsburg": 161, "Frankfurt": 169,
    "PSG": 85, "Lille": 79, "Marseille": 81, "Porto": 212,
    "Benfica": 211, "Sporting CP": 228, "Club Brugge": 569,
    "AEK Athens": 568, "LASK": 570, "Ajax": 194, "PSV": 197,
    # Arabia / Egipto
    "Al Hilal": 2939, "Al Nassr": 2940, "Al Ittihad": 2941,
    "Al Ahli": 2942, "Al Qadsiah": 2943, "Al Ettifaq": 2944,
    "Al Hazem": 2945, "Al Taawoun": 2946, "Al Fayha": 2947,
    "Al Faisaly": 2948, "NEOM": 2949, "Zamalek": 1040,
    "Al Ahly": 1039, "Smouha": 1041,
    # Brasil / Argentina
    "Flamengo": 127, "Palmeiras": 121, "Santos": 128,
    "Grêmio": 130, "Internacional": 119, "Corinthians": 131,
    "Boca": 451, "River": 435, "Vélez": 450, "Racing": 436,
    "San Lorenzo": 446, "Argentinos": 456, "Barracas": 463,
    # Escocia / Nordicos
    "Celtic": 247, "Rangers": 257, "Midtjylland": 397,
    "Nordsjælland": 398, "Malmö": 375,
    "Bodø/Glimt": 327, "Horsens": 399, "Copenhagen": 400,
    "AZ": 201, "Willem II": 203, "Union Berlin": 182, "Schalke": 183,
    "Rennes": 94, "Besiktas": 549, "Fenerbahce": 611,
    "Feyenoord": 209, "Atlético Madrid": 530, "Slovan": 552,
    "Galatasaray": 645, "Stuttgart": 172, "Viking": 701,
    "Como": 895, "Leipzig": 173, "Lens": 116, "Slavia": 560,
    "Sabah": 3563, "Shakhtar": 555, "Salzburg": 571, "Ried": 1395,
    "Cusco": 2553, "Melgar": 2554, "Pumas": 2287, "León": 2289,
    "Newell's": 453, "Coritiba": 198, "Athletico": 134,
    "Anderlecht": 554, "Mechelen": 266, "Lyon": 80,
    "Defensa y Justicia": 460, "UTC Cajamarca": 2550,
}
LOGOS = {name: logo_api(cid) for name, cid in IDS_FS.items()}


# ---------------- Datos externos opcionales: estadísticas históricas ----------------
# Se consulta SofaScore solo cuando el usuario pulsa "Ver estadísticas".
# Si no hay Internet, la app conserva el listado de partidos y muestra el motivo.
SOFASCORE = "https://www.sofascore.com/api/v1"
THESPORTSDB = "https://www.thesportsdb.com/api/v1/json/3"
ESPN_SITE = "https://site.web.api.espn.com/apis/site/v2/sports/soccer"
ESPN_SITE_FALLBACK = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_CDN = "https://cdn.espn.com/core/soccer"
FOTMOB = "https://www.fotmob.com/api/data"
RECENT_LIMIT = 20

# Fuentes públicas alternativas. SofaScore puede devolver 403 a algunas redes/IPs;
# por eso la app no depende de un único proveedor.
def _json_get(url, timeout=12):
    headers_list = [
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.sofascore.com/es/",
            "Origin": "https://www.sofascore.com",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        },
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.sofascore.com/",
        },
    ]
    urls=[url]
    if "www.sofascore.com/api/v1" in url:
        urls.append(url.replace("www.sofascore.com/api/v1","api.sofascore.com/api/v1"))
    last=None
    for u in urls:
        for headers in headers_list:
            try:
                req=urllib.request.Request(u,headers=headers)
                with urllib.request.urlopen(req,timeout=timeout) as r:
                    raw=r.read().decode("utf-8") or ""
                    if not raw.strip():
                        continue
                    data=json.loads(raw)
                    return data if data is not None else {}
            except Exception as e:
                last=e
                continue
    if last:
        raise last
    return {}

def _tdb_get(url, timeout=12):
    req=urllib.request.Request(url,headers={"User-Agent":"PrematchStatsDesk/2.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def _espn_get(url, timeout=12):
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36",
        "Accept":"application/json, text/plain, */*",
        "Origin":"https://www.espn.com",
        "Referer":"https://www.espn.com/",
    })
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

@lru_cache(maxsize=256)
def sofascore_team_id(name):
    q=urllib.parse.quote(name)
    data=_json_get(f"{SOFASCORE}/search/all?q={q}")
    results=data.get("results",[])
    candidates=[]; wanted=name.lower().replace("fc","").strip()
    for x in results:
        entity=x.get("entity") or {}
        if x.get("type") not in ("team","uniqueTournamentTeam") and entity.get("type") not in ("team","uniqueTournamentTeam"):
            continue
        nm=str(entity.get("name","")).lower()
        score=(100 if nm==wanted else 0)+(50 if wanted in nm or nm in wanted else 0)
        candidates.append((score,entity))
    if not candidates: raise ValueError(f"No se encontró el equipo: {name}")
    candidates.sort(key=lambda z:z[0],reverse=True)
    return int(candidates[0][1]["id"])

def _norm_team_name(v):
    """Normaliza nombres de equipos para comparar respuestas de distintas fuentes."""
    import re, unicodedata
    if v is None:
        return ""
    s=str(v).strip().lower()
    s=unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s=s.replace("&", " and ")
    s=re.sub(r"\b(fc|cf|sc|ac|afc|club)\b", " ", s)
    s=re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _logo_key(v):
    """Clave de escudo: NO borra SC/FC. Así Barcelona SC ≠ Barcelona."""
    import re, unicodedata
    if v is None:
        return ""
    s=str(v).strip().lower()
    s=unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s=re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _num(v):
    if isinstance(v,(int,float)): return float(v)
    if isinstance(v,str):
        import re
        m=re.search(r"-?\d+(?:\.\d+)?",v.replace(',','.'))
        return float(m.group()) if m else None
    return None

def _http_error_kind(exc):
    """Clasifica errores de fuente sin convertirlos en datos."""
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    return str(exc)

def event_stat_values(event_id):
    vals={}
    data=_json_get(f"{SOFASCORE}/event/{event_id}/statistics")
    for period in data.get("statistics",[]):
        if period.get("period") not in ("ALL","ALL_TIME"): continue
        for group in period.get("groups",[]):
            for item in group.get("statisticsItems",[]):
                name=str(item.get("name","")); low=name.lower()
                home=_num(item.get("home")); away=_num(item.get("away"))
                if home is None and away is None: continue
                key=None
                if "ball possession" in low or "possession" in low: key="possession"
                elif "corner" in low: key="corners"
                elif "shots on target" in low or "shots on goal" in low: key="sot"
                elif low in ("total shots","shots") or "total shots" in low: key="shots"
                elif "yellow card" in low: key="yellow"
                elif "red card" in low: key="red"
                elif low == "fouls" or "fouls" in low: key="fouls"
                elif "throw-in" in low or "throw in" in low or "throwins" in low: key="throwins"
                elif "tackle" in low: key="tackles"
                elif "offside" in low: key="offsides"
                elif "free kick" in low: key="freekicks"
                elif "goal kick" in low: key="goalkicks"
                elif "save" in low: key="saves"
                elif "cross" in low: key="crosses"
                elif "blocked" in low and "shot" in low: key="blockedshots"
                elif "woodwork" in low or "hit the woodwork" in low: key="woodwork"
                elif low == "attacks" or "attacks" in low and "dangerous" not in low: key="attacks"
                elif "dangerous attack" in low: key="dangerousattacks"
                if key and key not in vals: vals[key]=(home,away)
    return vals

def recent_team_stats(team_id, limit=RECENT_LIMIT):
    events=[]; page=0
    while len(events)<limit and page<6:
        data=_json_get(f"{SOFASCORE}/team/{team_id}/events/last/{page}")
        for ev in data.get("events",[]):
            if ev.get("status",{}).get("type")!="finished": continue
            events.append(ev)
            if len(events)>=limit: break
        page+=1
    # Las estadísticas de cada partido son independientes: consultarlas en paralelo
    # evita que el botón "Ver estadísticas" parezca bloqueado durante mucho tiempo.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    stat_map={}
    valid_events=[]
    for ev in events:
        hs=ev.get("homeScore",{}).get("current"); vs=ev.get("awayScore",{}).get("current")
        if hs is None or vs is None: continue
        valid_events.append(ev)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(event_stat_values, ev.get("id")): ev.get("id") for ev in valid_events}
        for fut in as_completed(futures):
            eid=futures[fut]
            try:
                stat_map[eid]=fut.result()
            except Exception:
                stat_map[eid]={}
    out=[]
    for ev in valid_events:
        home=ev.get("homeTeam",{}).get("id")==team_id
        hs=ev.get("homeScore",{}).get("current"); vs=ev.get("awayScore",{}).get("current")
        if hs is None or vs is None: continue
        sv=stat_map.get(ev.get("id"),{})
        side=0 if home else 1
        opp=(ev.get("awayTeam") if home else ev.get("homeTeam") or {})
        tournament=(ev.get("tournament") or {}).get("name") or (ev.get("uniqueTournament") or {}).get("name") or "—"
        row={"event_id":ev.get("id"),"date":ev.get("startTimestamp"),
             "opponent":opp.get("name","—"),
             "venue":"Local" if home else "Visitante",
             "goals_for":hs if home else vs,"goals_against":vs if home else hs,
             "goals_ht_for":(ev.get("homeScore",{}).get("period1") if home else ev.get("awayScore",{}).get("period1")),
             "result":("G" if ((hs>vs) if home else (vs>hs)) else ("E" if hs==vs else "P")),
             "competition":tournament,
             "shots":None,"sot":None,"corners":None,"yellow":None,"red":None,"possession":None,"fouls":None,"throwins":None,"tackles":None,"offsides":None,"freekicks":None,"goalkicks":None,"saves":None,"crosses":None,"blockedshots":None,"woodwork":None,"attacks":None,"dangerousattacks":None}
        for key in ("shots","sot","corners","yellow","red","possession","fouls","throwins","tackles","offsides","freekicks","goalkicks","saves","crosses","blockedshots","woodwork","attacks","dangerousattacks"):
            pair=sv.get(key)
            if pair: row[key]=pair[side]
        out.append(row)
    return out

def _range(values):
    vals=[v for v in values if v is not None]
    if not vals: return None
    lo,hi=min(vals),max(vals)
    return f"{lo:g}–{hi:g}"

def _avg(values):
    vals=[v for v in values if v is not None]
    return round(sum(vals)/len(vals),2) if vals else None

def _metric(values):
    vals=[v for v in values if v is not None]
    return {"average":_avg(vals),"range":_range(vals),"available_matches":len(vals)}

def _corner_profile(rows):
    vals=[]
    for r in rows or []:
        v=r.get('corners')
        if v is None:
            continue
        try:
            vals.append(float(v))
        except Exception:
            continue
    if not vals:
        return {'available':False,'sample':0,'reason':'La fuente no entregó córners en estos partidos'}
    n=len(vals)
    avg=sum(vals)/n
    bands=[]
    for th in (3,4,5,6,7,8):
        hits=sum(1 for v in vals if v>=th)
        bands.append({'min':th,'hits':hits,'sample':n,'rate':round(hits*100/n)})
    r5=next(b['rate'] for b in bands if b['min']==5)
    r4=next(b['rate'] for b in bands if b['min']==4)
    r3=next(b['rate'] for b in bands if b['min']==3)
    if avg>=6 or r5>=70:
        tone,label='alta','ALTA TENDENCIA A CÓRNERS'
    elif avg>=4.5 or r4>=65:
        tone,label='media','TENDENCIA MEDIA-ALTA'
    elif r3>=60:
        tone,label='media','TENDENCIA MEDIA'
    else:
        tone,label='baja','POCOS CÓRNERS'
    return {'available':True,'sample':n,'average':round(avg,2),
            'min':int(min(vals)),'max':int(max(vals)),'range':f'{int(min(vals))}-{int(max(vals))}',
            'bands':bands,'tone':tone,'label':label,'hit3':r3,'hit4':r4,'hit5':r5}

def _universal_trends(rows):
    """Devuelve únicamente patrones que se cumplieron en el 100% de los partidos disponibles."""
    if not rows:
        return []
    tests=[
        ("Marcó al menos 1 gol", lambda r: r.get("goals_for") is not None and r.get("goals_for")>=1),
        ("Recibió al menos 1 gol", lambda r: r.get("goals_against") is not None and r.get("goals_against")>=1),
        ("Más de 0.5 goles totales", lambda r: r.get("goals_for") is not None and r.get("goals_against") is not None and (r.get("goals_for")+r.get("goals_against"))>=1),
        ("Más de 1.5 goles totales", lambda r: r.get("goals_for") is not None and r.get("goals_against") is not None and (r.get("goals_for")+r.get("goals_against"))>=2),
        ("Menos de 4.5 goles totales", lambda r: r.get("goals_for") is not None and r.get("goals_against") is not None and (r.get("goals_for")+r.get("goals_against"))<=4),
        ("Ambos equipos marcaron", lambda r: r.get("goals_for") is not None and r.get("goals_against") is not None and r.get("goals_for")>=1 and r.get("goals_against")>=1),
        ("Hubo gol en el 1.º tiempo", lambda r: r.get("goals_ht_total") is not None and r.get("goals_ht_total")>=1),
        ("Más de 0.5 goles en 1.º tiempo", lambda r: r.get("goals_ht_total") is not None and r.get("goals_ht_total")>=1),
        ("Más de 1.5 goles en 1.º tiempo", lambda r: r.get("goals_ht_total") is not None and r.get("goals_ht_total")>=2),
        ("1.º tiempo con 0 goles", lambda r: r.get("goals_ht_total") is not None and r.get("goals_ht_total")==0),
    ]
    out=[]
    for label,fn in tests:
        valid=[r for r in rows if r.get("goals_for") is not None and r.get("goals_against") is not None]
        if valid and all(fn(r) for r in valid):
            out.append({"label":label,"hits":len(valid),"sample":len(valid)})
    # Métricas de juego: solo se consideran si el campo está disponible en todos los partidos.
    stat_tests=[
        ("Al menos 1 córner", "corners", lambda v:v is not None and v>=1),
        ("Al menos 1 remate", "shots", lambda v:v is not None and v>=1),
        ("Al menos 1 remate al arco", "sot", lambda v:v is not None and v>=1),
        ("Al menos 1 saque de banda", "throwins", lambda v:v is not None and v>=1),
        ("Al menos 1 tackle", "tackles", lambda v:v is not None and v>=1),
        ("Al menos 1 fuera de juego", "offsides", lambda v:v is not None and v>=1),
    ]
    for label,key,fn in stat_tests:
        vals=[r.get(key) for r in rows]
        if vals and all(v is not None for v in vals) and all(fn(v) for v in vals):
            out.append({"label":label,"hits":len(vals),"sample":len(vals)})
    # Patrones de volumen que se repiten en todos los partidos disponibles.
    common_tests=[
        ("Al menos 4 córners", "corners", lambda v:v>=4),
        ("Al menos 1 tarjeta", "yellow", lambda v:v>=1),
        ("Al menos 15 faltas", "fouls", lambda v:v>=15),
        ("Al menos 5 remates", "shots", lambda v:v>=5),
        ("Al menos 10 saques de banda", "throwins", lambda v:v>=10),
        ("Al menos 5 tackles", "tackles", lambda v:v>=5),
        ("Al menos 1 tiro libre", "freekicks", lambda v:v>=1),
        ("Al menos 1 saque de meta", "goalkicks", lambda v:v>=1),
    ]
    for label,key,fn in common_tests:
        vals=[r.get(key) for r in rows]
        if vals and all(v is not None for v in vals) and all(fn(v) for v in vals):
            out.append({"label":label,"hits":len(vals),"sample":len(vals)})
    return out

def _summary_from_rows(name,rows,source,source_status="OK"):
    fields={k:_metric([r.get(k) for r in rows]) for k in ("goals_for","goals_ht_for","goals_ht_against","goals_ht_total","shots","sot","corners","yellow","red","possession","fouls","throwins","tackles","offsides","freekicks","goalkicks","saves","crosses","blockedshots","woodwork","attacks","dangerousattacks")}
    local=[r for r in rows if r.get("venue")=="Local"]
    away=[r for r in rows if r.get("venue")=="Visitante"]
    def record(rs):
        return {"wins":sum(r.get("result")=="G" for r in rs),"draws":sum(r.get("result")=="E" for r in rs),"losses":sum(r.get("result")=="P" for r in rs)}
    return {"team":name,"matches":len(rows),"source":source,"source_status":source_status,
            "metrics":fields,"records":{"all":record(rows),"home":record(local),"away":record(away)},
            "recent":rows,"universal_trends":_universal_trends(rows),"corner_profile":_corner_profile(rows)}

# ---------------- Fallback público ESPN ----------------
# SofaScore puede devolver 403 según la IP/red. En ese caso se intenta ESPN.
# ESPN expone calendarios de equipo y resúmenes de partido sin autenticación;
# solo se usan valores realmente presentes en sus respuestas.
@lru_cache(maxsize=256)
def _espn_scoreboard_day(day):
    """Obtiene el marcador global de ESPN para una fecha.

    Importante: ESPN no ofrece de forma fiable /soccer/all/teams ni
    /soccer/all/teams/{id}/schedule. Para evitar el 404 de FIX7 usamos
    el scoreboard global por fecha, que sí está documentado para soccer/all.
    """
    last=None
    for base in (ESPN_SITE, ESPN_SITE_FALLBACK):
        try:
            return _espn_get(f"{base}/all/scoreboard?dates={day}", timeout=15)
        except Exception as e:
            last=e
    raise last or RuntimeError("ESPN no entregó el marcador del día")

def _significant_tokens(name):
    stop={"fc","cf","sc","ac","afc","club","the","de","da","do","ec","se","sa","pr","sp","rj","mg","go","rs","ba","pe","u17","u19","u20","u21","u23","ii","b"}
    return [t for t in _norm_team_name(name).split() if t and t not in stop and len(t)>=4]

def _names_compatible(a, b):
    """Matching estricto: evita cruzar Criciúma con Groene Ster o Be Quick."""
    na=_norm_team_name(a); nb=_norm_team_name(b)
    if not na or not nb:
        return False
    if na==nb:
        return True
    ta=_significant_tokens(a); tb=_significant_tokens(b)
    if not ta or not tb:
        return False
    if ta==tb:
        return True
    if all(t in nb.split() for t in ta) or all(t in na.split() for t in tb):
        return True
    # Un token largo idéntico (criciuma, operario, juventude) basta si no hay conflicto de categoría.
    age_a=set(_norm_team_name(a).split()) & {"u17","u19","u20","u21","u23","women","femenino"}
    age_b=set(_norm_team_name(b).split()) & {"u17","u19","u20","u21","u23","women","femenino"}
    if age_a!=age_b:
        return False
    return bool(set(ta) & set(tb)) and (ta[0]==tb[0] or ta[0] in nb.split() or tb[0] in na.split())

def espn_search_team(name):
    q=urllib.parse.quote(name)
    data=_espn_get(f"https://site.web.api.espn.com/apis/search/v2?query={q}&limit=20&sport=soccer",timeout=15)
    best=None
    for block in data.get("results") or []:
        if block.get("type")!="team":
            continue
        for obj in block.get("contents") or []:
            if str(obj.get("sport") or "").lower() not in ("","soccer","football"):
                continue
            label=" ".join(str(obj.get(k) or "") for k in ("displayName","name","subtitle"))
            if not _names_compatible(name, obj.get("displayName") or obj.get("name") or ""):
                # permitir "Operário-PR" vs "Operário PR"
                if not _names_compatible(name, label):
                    continue
            uid=str(obj.get("uid") or "")
            tid=None
            if "~t:" in uid:
                tid=uid.split("~t:")[-1]
            elif str(obj.get("id") or "").isdigit():
                tid=str(obj.get("id"))
            slug=obj.get("defaultLeagueSlug") or ""
            if tid and slug:
                score=100 if _norm_team_name(obj.get("displayName"))==_norm_team_name(name) else 70
                if best is None or score>best[0]:
                    best=(score,{"id":tid,"slug":slug,"name":obj.get("displayName") or name})
    if not best:
        raise ValueError(f"ESPN no encontró el equipo: {name}")
    return best[1]

def _espn_team_matches_from_scoreboard(name, limit=RECENT_LIMIT, days_back=150):
    """Calendario oficial del equipo en ESPN (no el scoreboard mundial).

    El scoreboard /soccer/all mezclaba KNVB Beker holandesa con Serie B
    porque el matching por substring aceptaba tokens cortos (PR, SC, AC).
    """
    meta=espn_search_team(name)
    tid=str(meta["id"]); slug=meta["slug"]
    import datetime as _dt
    year=_dt.datetime.now(_dt.timezone.utc).year
    events=[]
    seen=set()
    for season in (year, year-1, year+1):
        try:
            data=_espn_get(f"{ESPN_SITE}/{slug}/teams/{tid}/schedule?season={season}", timeout=15)
        except Exception:
            try:
                data=_espn_get(f"{ESPN_SITE}/{slug}/teams/{tid}/schedule", timeout=15)
            except Exception:
                continue
        for ev in data.get("events") or []:
            eid=str(ev.get("id") or "")
            if not eid or eid in seen:
                continue
            comp=(ev.get("competitions") or [{}])[0]
            st=((comp.get("status") or ev.get("status") or {}).get("type") or {})
            if not (st.get("completed") or st.get("state")=="post" or str(st.get("name") or "").startswith("STATUS_FINAL")):
                continue
            competitors=comp.get("competitors") or []
            mine=next((c for c in competitors if str((c.get("team") or {}).get("id") or c.get("id") or "")==tid), None)
            if mine is None:
                # fallback estricto por nombre
                for c in competitors:
                    t=c.get("team") or {}
                    if _names_compatible(name, t.get("displayName") or t.get("name") or ""):
                        mine=c; break
            if mine is None:
                continue
            opp=next((c for c in competitors if c is not mine), None)
            if not opp:
                continue
            homeaway=mine.get("homeAway")
            if homeaway not in ("home","away"):
                continue
            seen.add(eid)
            events.append((ev,mine,opp,homeaway))
        if len(events)>=limit:
            break
    events.sort(key=lambda x:x[0].get("date") or "", reverse=True)
    return events[:limit]

def _espn_team_name_match(name, team_obj):
    vals=[team_obj.get("displayName"),team_obj.get("name"),team_obj.get("shortDisplayName")]
    return any(_names_compatible(name, v) for v in vals if v)

def espn_team_id(name):
    # Conservado por compatibilidad. El ID solo se obtiene si el buscador global
    # lo entrega; la ruta principal de FIX8 ya no depende de él.
    try:
        q=urllib.parse.quote(name)
        data=_espn_get(f"https://site.web.api.espn.com/apis/search/v2?query={q}&limit=20&sport=soccer",timeout=15)
        def walk(obj):
            if isinstance(obj,dict):
                if obj.get("id") and any(obj.get(k) for k in ("displayName","name")) and _espn_team_name_match(name,obj):
                    return str(obj["id"])
                for v in obj.values():
                    r=walk(v)
                    if r: return r
            elif isinstance(obj,list):
                for v in obj:
                    r=walk(v)
                    if r: return r
            return None
        r=walk(data)
        if r: return r
    except Exception:
        pass
    raise ValueError(f"ESPN no encontró el ID del equipo: {name}")

def _espn_stat_map(team_obj):
    out={}
    for st in team_obj.get("statistics",[]) or []:
        key=str(st.get("name") or st.get("abbreviation") or st.get("displayName") or "").lower()
        val=st.get("displayValue")
        if val is None: val=st.get("value")
        out[key]=val
    return out

def _stat_lookup(m, *keys):
    for k in keys:
        if k.lower() in m:
            v=_num(m[k.lower()])
            if v is not None: return v
    for k,v in m.items():
        lk=k.lower()
        if any(key.lower() in lk for key in keys):
            n=_num(v)
            if n is not None: return n
    return None

def espn_event_stats(event_id):
    """Obtiene estadísticas de fútbol desde el resumen oficial de ESPN.

    El endpoint /summary es más estable para soccer que el paquete CDN
    /core/soccer/game. Se aceptan solo campos realmente presentes.
    """
    last=None
    for base in (ESPN_SITE, ESPN_SITE_FALLBACK):
        try:
            data=_espn_get(
                f"{base}/all/summary?event={urllib.parse.quote(str(event_id))}",
                timeout=15
            )
            teams=(data.get("boxscore") or {}).get("teams") or []
            vals={}
            for t in teams:
                side=t.get("homeAway")
                if side not in ("home","away"):
                    continue
                m=_espn_stat_map(t)
                vals[side]={
                    "shots":_stat_lookup(m,"totalshots","shots"),
                    "sot":_stat_lookup(m,"shotsontarget","shotsongoal","sog"),
                    "corners":_stat_lookup(m,"woncorners","corners"),
                    "yellow":_stat_lookup(m,"yellowcards","yellow"),
                    "red":_stat_lookup(m,"redcards","red"),
                    "possession":_stat_lookup(m,"possessionpct","possession"),
                    "fouls":_stat_lookup(m,"foulscommitted","fouls"),
                    "throwins":_stat_lookup(m,"throwins","throwins","throwinswon"),
                    "tackles":_stat_lookup(m,"totaltackles","tackles","tackleswon"),
                    "offsides":_stat_lookup(m,"offsides","offside"),
                    "freekicks":_stat_lookup(m,"freekicks","free kicks","free kicks won"),
                    "goalkicks":_stat_lookup(m,"goalkicks","goal kicks"),
                    "saves":_stat_lookup(m,"saves","save"),
                    "crosses":_stat_lookup(m,"crosses","cross"),
                    "blockedshots":_stat_lookup(m,"blockedshots","blocked shots"),
                    "woodwork":_stat_lookup(m,"woodwork","hitwoodwork","woodworkhits"),
                    "attacks":_stat_lookup(m,"attacks","totalattacks"),
                    "dangerousattacks":_stat_lookup(m,"dangerousattacks","dangerous attacks"),
                }
            if vals:
                return vals
        except Exception as e:
            last=e
    raise last or ValueError("ESPN no entregó estadísticas del partido")

def espn_recent_team_stats(name, limit=RECENT_LIMIT):
    events=_espn_team_matches_from_scoreboard(name,limit=limit,days_back=120)
    if not events:
        raise ValueError("ESPN no encontró partidos finalizados del equipo en los últimos 120 días")
    from concurrent.futures import ThreadPoolExecutor, as_completed
    stat_map={}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(espn_event_stats, ev.get("id")): ev.get("id") for ev,_,_,_ in events}
        for fut in as_completed(futures):
            eid=futures[fut]
            try:
                stat_map[eid]=fut.result()
            except Exception:
                stat_map[eid]={}
    out=[]
    for ev,mine,opp,homeaway in events:
        event_id=ev.get("id")
        stats=(stat_map.get(event_id) or {}).get(homeaway,{})
        tournament=((ev.get("league") or {}).get("name") or ((ev.get("season") or {}).get("slug")) or "—")
        ms=_num(mine.get("score")); os=_num(opp.get("score"))
        if ms is None or os is None:
            continue
        def _ht_score(comp):
            ls=comp.get("linescores") or []
            if ls:
                v=ls[0].get("value") if isinstance(ls[0],dict) else None
                n=_num(v)
                if n is not None: return int(n) if float(n).is_integer() else n
            sc=comp.get("score")
            if isinstance(sc,dict):
                for k in ("period1","halftime","halfTime","firstHalf"):
                    n=_num(sc.get(k))
                    if n is not None: return int(n) if float(n).is_integer() else n
            return None
        ht_mine=_ht_score(mine); ht_opp=_ht_score(opp)
        gf=int(ms) if float(ms).is_integer() else ms
        ga=int(os) if float(os).is_integer() else os
        out.append({
            "event_id":event_id,"date":ev.get("date") or "",
            "opponent":(opp.get("team") or {}).get("displayName") or (opp.get("team") or {}).get("name") or "—",
            "venue":"Local" if homeaway=="home" else "Visitante",
            "goals_for":gf,
            "goals_against":ga,
            "goals_ht_for":ht_mine,
            "goals_ht_against":ht_opp,
            "goals_ht_total":(ht_mine+ht_opp) if (ht_mine is not None and ht_opp is not None) else None,
            "result":"G" if ms>os else ("E" if ms==os else "P"),
            "competition":tournament,
            "shots":stats.get("shots"),"sot":stats.get("sot"),"corners":stats.get("corners"),
            "yellow":stats.get("yellow"),"red":stats.get("red"),"possession":stats.get("possession"),"fouls":stats.get("fouls"),"throwins":stats.get("throwins"),"tackles":stats.get("tackles"),"offsides":stats.get("offsides"),"freekicks":stats.get("freekicks"),"goalkicks":stats.get("goalkicks"),"saves":stats.get("saves"),"crosses":stats.get("crosses"),"blockedshots":stats.get("blockedshots"),"woodwork":stats.get("woodwork"),"attacks":stats.get("attacks"),"dangerousattacks":stats.get("dangerousattacks")
        })
    return out


# ---------------- FotMob: últimos 20 partidos reales ----------------
# SofaScore responde 403 en muchas redes. FotMob /api/data sí entrega
# fixtures y estadísticas de partido verificables sin API key.
def _fotmob_get(url, timeout=14):
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept":"application/json, text/plain, */*",
        "Referer":"https://www.fotmob.com/",
        "Origin":"https://www.fotmob.com",
        "Accept-Language":"es-PE,es;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=r.read().decode("utf-8") or ""
        if not raw.strip():
            return {}
        data=json.loads(raw)
        return data if isinstance(data, dict) else {}

_FOTMOB_SEED = {
    "arsenal":9825,"chelsea":8455,"liverpool":8650,"manchester city":8456,"man city":8456,
    "manchester united":10260,"man united":10260,"tottenham":8586,"tottenham hotspur":8586,
    "newcastle":10261,"aston villa":10252,"brighton":10204,"west ham":8654,"everton":8668,
    "real madrid":8633,"barcelona":8634,"atletico madrid":9906,"sevilla":8302,"villarreal":10205,
    "athletic":8315,"real sociedad":8560,"valencia":10267,"betis":8603,"getafe":8305,
    "napoli":2733,"inter":8636,"ac milan":8564,"milan":8564,"juventus":9885,"roma":8686,
    "lazio":8543,"atalanta":8524,"fiorentina":8535,"bologna":9857,"torino":9804,
    "bayern":9823,"bayern munich":9823,"dortmund":9789,"leipzig":178475,"leverkusen":8178,
    "psg":9847,"marseille":8592,"lyon":9748,"lille":8639,"monaco":9829,
    "benfica":9772,"porto":7396,"sporting cp":7249,"ajax":1039,"psv":8640,"feyenoord":10235,
    "galatasaray":8637,"fenerbahce":8594,"besiktas":8574,"shakhtar":10159,
    "flamengo":5981,"palmeiras":10283,"santos":8514,"gremio":8475,"internacional":8476,
    "corinthians":8479,"boca":8359,"river":8370,"velez":10144,"racing":8371,
    "celtic":9925,"rangers":8548,"porto":7396,"slavia":8376,"salzburg":8259,
    "al hilal":9838,"al nassr":9837,"al ahly":8519,"zamalek":8518,
    "cusco":39634,"melgar":39633,
    "criciuma":7729,"criciuma ec":7729,
    "operario pr":197429,"operario-pr":197429,"operario ferroviario":197429,
    "operario":197429,"juventude":7790,"cuiaba":7766,"crb":7767,
    "fortaleza":8111,"botafogo sp":7798,"goias":7793,"nautico":7796,
    "novorizontino":193626,"vila nova":7794,"ponte preta":7800,
    "sport recife":7801,"sport":7801,"sao bernardo":196513,
    "america mg":7630,"atletico go":7781,"atletico-go":7781,
    "londrina":7784,"avai":7789,"athletic club mg":196226,
    # Colombia · Liga BetPlay Dimayor
    "america de cali":10280,"america":10280,
    "millonarios":4403,"atletico nacional":6368,"nacional":6368,
    "bucaramanga":4401,"atletico bucaramanga":4401,
    "independiente medellin":2528,"medellin":2528,"dim":2528,
    "tolima":1894,"deportes tolima":1894,
    "santa fe":7818,"independiente santa fe":7818,
    "deportivo cali":6387,
    "llaneros":348397,"llaneros fc":348397,
    "once caldas":6024,
    "aguilas doradas":193025,"aguilas":193025,
    "internacional de bogota":47240,"inter bogota":47240,
    "cucuta":6254,"cucuta deportivo":6254,
    "fortaleza fc":244167,"fortaleza ceif":244167,
    "jaguares":424270,"cd jaguares":424270,"jaguares de cordoba":424270,
    "deportivo pasto":4405,"pasto":4405,
    "alianza fc":193029,"alianza valledupar":193029,"alianza":193029,
    "chico fc":6255,"boyaca chico":6255,"boyaca chico fc":6255,
    "deportivo pereira":4404,"pereira":4404,
    "junior":2254,"junior fc":2254,"junior barranquilla":2254,
    # India · Indian Super League
    "east bengal":165184,"east bengal fc":165184,
    "mohun bagan":578651,"mohun bagan sg":578651,
    "mumbai city":578655,"mumbai city fc":578655,
    "bengaluru":485935,"bengaluru fc":485935,
    "punjab fc":589749,"jamshedpur":873038,"jamshedpur fc":873038,
    "goa":578650,"fc goa":578650,
    "kerala blasters":578654,"kerala blasters fc":578654,
    "northeast united":578656,"northeast united fc":578656,
    "inter kashi":1562126,
    "sc delhi":1086744,"delhi":1086744,
    "odisha":578653,"odisha fc":578653,
    "chennaiyin":578652,"chennaiyin fc":578652,
    "mohammedan":165187,"mohammedan sc":165187,
    "penarol":8450,"club atletico penarol":8450,"club atletico penarol":8450,
    "danubio":8562,
    "wanderers":7863,"montevideo wanderers":7863,
    "cerro":1836,"ca cerro":1836,"club atletico cerro":1836,
    "boston river":188313,"fenix":7808,
    "liverpool montevideo":2219,
    "deportivo maldonado":1833,"maldonado":1833,
    "cerrito":2220,
    "montevideo city torque":395613,"torque":395613,"city torque":395613,
    "juventud de las piedras":9883,"juventud":9883,
    "defensor sporting":7796,"defensor":7796,
    "plaza colonia":4669,"atenas":181912,"colon":1223580,"rentistas":2221,"oriental":688270,
    "cerro largo":148967,
    "progreso":1838,"club atletico progreso":1838,
    "albion":924934,"central espanol":1834,
    "nacional montevideo":8304,"club nacional":8304,"club nacional de football":8304,
}




_FOTMOB_INDEX = {}

def _index_fotmob_matches(date_str):
    try:
        data=_fotmob_get(f"{FOTMOB}/matches?date={date_str}", timeout=12)
    except Exception:
        return
    for lg in data.get("leagues") or []:
        for ev in lg.get("matches") or []:
            for side in ("home","away"):
                t=ev.get(side) or {}
                tid=t.get("id"); nm=t.get("name") or t.get("longName") or t.get("shortName")
                if tid and nm:
                    _FOTMOB_INDEX[_logo_key(nm)]=int(tid)
                    _FOTMOB_INDEX[_norm_team_name(nm)]=int(tid)
                    short=t.get("shortName")
                    if short:
                        _FOTMOB_INDEX[_logo_key(short)]=int(tid)
                        _FOTMOB_INDEX[_norm_team_name(short)]=int(tid)

URU_IDS={
    "cerro":1836,"ca cerro":1836,"club atletico cerro":1836,
    "deportivo maldonado":1833,"maldonado":1833,
    "penarol":8450,"club atletico penarol":8450,
    "danubio":8562,"montevideo wanderers":7863,"wanderers":7863,
    "boston river":188313,"liverpool montevideo":2219,
    "nacional montevideo":8304,"club nacional":8304,
    "cerro largo":148967,"defensor sporting":7796,"defensor":7796,
    "montevideo city torque":395613,"torque":395613,
    "juventud de las piedras":9883,"progreso":1838,"albion":924934,
    "central espanol":1834,"racing montevideo":6043,
    "cerrito":2220,"plaza colonia":4669,"atenas":181912,
    "colon":1223580,"rentistas":2221,"oriental":688270,"fenix":7808,
}
def _looks_uruguay(*names):
    blob=" ".join(_norm_team_name(x) for x in names if x)
    return any(k in blob for k in ("maldonado","wanderers","penarol","danubio","auf","cerro largo","boston river","torque","juventud de las piedras","cerrito","progreso"))

def resolve_fotmob_id(name, peer=""):
    wanted=_norm_team_name(name)
    if not wanted:
        return None
    if _looks_uruguay(name, peer) or wanted in URU_IDS:
        if wanted in URU_IDS:
            return URU_IDS[wanted]
        for k,tid in URU_IDS.items():
            if _names_compatible(wanted,k):
                return tid
        # Cerro a secas en cruce uruguayo
        if wanted=="cerro":
            return 1836
    if wanted in _FOTMOB_SEED:
        return _FOTMOB_SEED[wanted]
    if wanted in _FOTMOB_INDEX:
        return _FOTMOB_INDEX[wanted]
    try:
        return fotmob_team_id(name)
    except Exception:
        return None

@lru_cache(maxsize=512)
def fotmob_team_id(name):
    wanted=_norm_team_name(name)
    if not wanted:
        raise ValueError(f"FotMob no encontró el equipo: {name}")
    if wanted in _FOTMOB_SEED:
        return _FOTMOB_SEED[wanted]
    if wanted in _FOTMOB_INDEX:
        return _FOTMOB_INDEX[wanted]
    # Coincidencia parcial en semilla/índice.
    for key,tid in list(_FOTMOB_SEED.items())+list(_FOTMOB_INDEX.items()):
        if _names_compatible(wanted, key):
            return tid
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    today=_dt.now(_tz.utc).date()
    dates=[(today-_td(days=i)).strftime("%Y%m%d") for i in range(0,60,1)]
    from concurrent.futures import ThreadPoolExecutor, as_completed
    for pos in range(0,len(dates),10):
        batch=dates[pos:pos+10]
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(_index_fotmob_matches, batch))
        if wanted in _FOTMOB_INDEX:
            return _FOTMOB_INDEX[wanted]
        for key,tid in _FOTMOB_INDEX.items():
            if _names_compatible(wanted, key):
                return tid
    raise ValueError(f"FotMob no encontró el equipo: {name}")

def _fotmob_pair_stats(match_id):
    data=_fotmob_get(f"{FOTMOB}/matchDetails?matchId={match_id}", timeout=14)
    header=data.get("header") or {}
    general=data.get("general") or {}
    teams=header.get("teams") or []
    home=teams[0] if teams else {}
    away=teams[1] if len(teams)>1 else {}
    events=((data.get("content") or {}).get("matchFacts") or {}).get("events") or header.get("events") or {}
    def _event_list(blob):
        if isinstance(blob, list):
            return blob
        if not isinstance(blob, dict):
            return []
        if isinstance(blob.get("events"), list):
            return blob.get("events") or []
        out=[]
        for key in ("homeTeamGoals","awayTeamGoals"):
            bag=blob.get(key)
            if isinstance(bag, dict):
                for items in bag.values():
                    out.extend(items or [])
        return out
    evlist=_event_list(events)
    def ht_goals(is_home):
        goals=0
        for ev in evlist:
            typ=str(ev.get("type") or ev.get("typeStr") or ev.get("goalDescription") or "").lower()
            is_goal = typ in ("goal","owngoal","own goal") or ev.get("goalDescription") or ("Goal" in str(ev.get("type") or ""))
            if not is_goal:
                continue
            t=ev.get("time")
            try:
                t=float(t)
            except Exception:
                continue
            if t>45:
                continue
            home_flag=ev.get("isHome")
            if home_flag is None:
                # formato viejo homeTeamGoals
                continue
            if bool(home_flag)==bool(is_home):
                goals+=1
        if goals==0:
            bag=events.get("homeTeamGoals") if is_home else events.get("awayTeamGoals")
            if isinstance(bag,dict):
                for items in bag.values():
                    for ev in items or []:
                        t=ev.get("time")
                        if isinstance(t,(int,float)) and t<=45:
                            goals+=1
        return goals
    vals={}
    periods=(((data.get("content") or {}).get("stats") or {}).get("Periods") or {})
    allp=(periods.get("All") or {}).get("stats") or []
    keymap={
        "ballpossesion":"possession","ball possession":"possession",
        "total_shots":"shots","total shots":"shots","shots":"shots",
        "shotsontarget":"sot","shots on target":"sot",
        "corners":"corners","yellow_cards":"yellow","yellow cards":"yellow",
        "red_cards":"red","red cards":"red","fouls":"fouls",
        "throwins":"throwins","throw-ins":"throwins","throw ins":"throwins",
        "tackles":"tackles","offsides":"offsides","offside":"offsides",
        "freekicks":"freekicks","free kicks":"freekicks",
        "goalkicks":"goalkicks","goal kicks":"goalkicks",
        "saves":"saves","keeper_saves":"saves","goalkeeper saves":"saves",
        "crosses":"crosses","blocked_shots":"blockedshots","blocked shots":"blockedshots",
        "shots_woodwork":"woodwork","hit woodwork":"woodwork",
        "touches_opp_box":"attacks","dangerous_attacks":"dangerousattacks",
        "dangerous attacks":"dangerousattacks",
    }
    for group in allp:
        for item in group.get("stats") or []:
            title=str(item.get("title") or "")
            key=str(item.get("key") or "")
            mapped=keymap.get(key.lower()) or keymap.get(title.lower())
            if not mapped or mapped in vals:
                continue
            pair=item.get("stats") or [None,None]
            h=_num(pair[0] if len(pair)>0 else None)
            a=_num(pair[1] if len(pair)>1 else None)
            if h is not None or a is not None:
                vals[mapped]=(h,a)
    return {
        "home_id":home.get("id"),"away_id":away.get("id"),
        "home_name":home.get("name"),"away_name":away.get("name"),
        "home_goals":home.get("score"),"away_goals":away.get("score"),
        "home_ht":ht_goals(True),"away_ht":ht_goals(False),
        "utc":(header.get("status") or {}).get("utcTime") or general.get("matchTimeUTC"),
        "league":general.get("leagueName") or "",
        "stats":vals,
        "logo_home":home.get("imageUrl") or "",
        "logo_away":away.get("imageUrl") or "",
        "red_home":(header.get("status") or {}).get("numberOfHomeRedCards"),
        "red_away":(header.get("status") or {}).get("numberOfAwayRedCards"),
    }

def _fotmob_matches_on_day(date_str, team_id):
    out=[]
    try:
        data=_fotmob_get(f"{FOTMOB}/matches?date={date_str}", timeout=12)
    except Exception:
        return out
    for lg in data.get("leagues") or []:
        lname=lg.get("name") or "—"
        for ev in lg.get("matches") or []:
            home=ev.get("home") or {}; away=ev.get("away") or {}
            if int(home.get("id") or 0)!=int(team_id) and int(away.get("id") or 0)!=int(team_id):
                continue
            st=ev.get("status") or {}
            if not st.get("finished") or st.get("cancelled"):
                continue
            ev=dict(ev)
            ev.setdefault("tournament", {"name": lname})
            out.append(ev)
    return out

def fotmob_recent_team_stats(name, limit=RECENT_LIMIT, peer=""):
    tid=resolve_fotmob_id(name, peer)
    if not tid:
        raise ValueError(f"FotMob no encontró el equipo: {name}")
    data=_fotmob_get(f"{FOTMOB}/teams?id={tid}", timeout=16) or {}
    fx=((((data.get("fixtures") or {}) if isinstance(data.get("fixtures"),dict) else {}).get("allFixtures") or {}).get("fixtures") or [])
    finished=[]
    seen=set()
    for ev in fx:
        st=ev.get("status") or {}
        hs=(ev.get("home") or {}).get("score"); vs=(ev.get("away") or {}).get("score")
        done=bool(st.get("finished")) or (hs is not None and vs is not None and not ev.get("notStarted") and not st.get("cancelled"))
        if ev.get("notStarted") or st.get("cancelled") or not done:
            continue
        utc=st.get("utcTime") or ""
        eid=ev.get("id")
        if eid in seen: continue
        seen.add(eid)
        finished.append((utc,ev))
    # Si la temporada actual aún no llega a 20, se completa con el calendario
    # diario real de FotMob hacia atrás (todas las competiciones).
    if len(finished)<limit:
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        start=_dt.now(_tz.utc).date()
        if finished:
            try:
                start=_dt.fromisoformat(str(finished[-1][0]).replace("Z","+00:00")).date()-_td(days=1)
            except Exception:
                pass
        dates=[(start-_td(days=i)).strftime("%Y%m%d") for i in range(0,220)]
        from concurrent.futures import ThreadPoolExecutor
        for pos in range(0,len(dates),12):
            if len(finished)>=limit: break
            batch=dates[pos:pos+12]
            with ThreadPoolExecutor(max_workers=8) as pool:
                chunks=list(pool.map(lambda d:_fotmob_matches_on_day(d,tid), batch))
            extra=[]
            for rows in chunks:
                for ev in rows:
                    eid=ev.get("id")
                    if eid in seen: continue
                    seen.add(eid)
                    extra.append(((ev.get("status") or {}).get("utcTime") or "", ev))
            finished.extend(extra)
    finished.sort(key=lambda x:x[0], reverse=True)
    picked=[ev for _,ev in finished[:limit]]
    from concurrent.futures import ThreadPoolExecutor, as_completed
    details={}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs={pool.submit(_fotmob_pair_stats, ev.get("id")): ev.get("id") for ev in picked if ev.get("id")}
        for fut in as_completed(futs):
            eid=futs[fut]
            try:
                details[eid]=fut.result()
            except Exception:
                details[eid]={}
    out=[]
    for ev in picked:
        home=ev.get("home") or {}
        away=ev.get("away") or {}
        is_home=int(home.get("id") or 0)==int(tid)
        hs=home.get("score"); vs=away.get("score")
        if hs is None or vs is None:
            continue
        det=details.get(ev.get("id")) or {}
        pair=det.get("stats") or {}
        side=0 if is_home else 1
        row={"event_id":ev.get("id"),
             "date":det.get("utc") or ((ev.get("status") or {}).get("utcTime")),
             "opponent":(away.get("name") if is_home else home.get("name")) or "—",
             "venue":"Local" if is_home else "Visitante",
             "goals_for":hs if is_home else vs,
             "goals_against":vs if is_home else hs,
             "goals_ht_for":(det.get("home_ht") if is_home else det.get("away_ht")),
             "goals_ht_against":(det.get("away_ht") if is_home else det.get("home_ht")),
             "goals_ht_total":((det.get("home_ht") or 0)+(det.get("away_ht") or 0)) if (det.get("home_ht") is not None or det.get("away_ht") is not None) else None,
             "result":("G" if ((hs>vs) if is_home else (vs>hs)) else ("E" if hs==vs else "P")),
             "competition":(ev.get("tournament") or {}).get("name") or det.get("league") or "—",
             "shots":None,"sot":None,"corners":None,"yellow":None,"red":None,"possession":None,"fouls":None,
             "throwins":None,"tackles":None,"offsides":None,"freekicks":None,"goalkicks":None,"saves":None,
             "crosses":None,"blockedshots":None,"woodwork":None,"attacks":None,"dangerousattacks":None}
        for key in ("shots","sot","corners","yellow","red","possession","fouls","throwins","tackles","offsides","freekicks","goalkicks","saves","crosses","blockedshots","woodwork","attacks","dangerousattacks"):
            pr=pair.get(key)
            if pr:
                row[key]=pr[side]
        if row.get("red") is None:
            row["red"]=det.get("red_home") if is_home else det.get("red_away")
        out.append(row)
    if not out:
        raise ValueError("FotMob no entregó partidos finalizados verificables")
    return out

def _is_womens_event(ev):
    """Detecta competiciones femeninas en un evento SofaScore."""
    if not isinstance(ev, dict):
        return False
    bits=[]
    for obj in (ev, ev.get("tournament") or {}, ev.get("uniqueTournament") or {}, (ev.get("tournament") or {}).get("category") or {}, ev.get("homeTeam") or {}, ev.get("awayTeam") or {}):
        if isinstance(obj, dict):
            for k in ("name","slug","gender"):
                if obj.get(k) is not None:
                    bits.append(str(obj.get(k)))
    s=" ".join(bits).lower()
    return any(x in s for x in ("women","womens","femen","female","ladies","nwsl","femenil","femminile","frauen","damer","feminina","femenina"))


def _india_row(date, opp, gf, ga, venue, comp):
    return {
        "event_id":None,"date":date,"opponent":opp,"venue":venue,
        "goals_for":gf,"goals_against":ga,
        "goals_ht_for":None,"goals_ht_against":None,"goals_ht_total":None,
        "result":"G" if gf>ga else ("E" if gf==ga else "P"),
        "competition":comp,
        "shots":None,"sot":None,"corners":None,"yellow":None,"red":None,
        "possession":None,"fouls":None,"throwins":None,"tackles":None,"offsides":None,
        "freekicks":None,"goalkicks":None,"saves":None,"crosses":None,
        "blockedshots":None,"woodwork":None,"attacks":None,"dangerousattacks":None,
    }

# Resultados publicados de Super Division India (KSFA/BDFA y Mumbai).
# SofaScore tiene las ligas (BDFA 29341, Mumbai Super League 24569) pero la API
# responde 403 en muchas redes; estos marcadores cubren el vacío sin inventar.
INDIA_RECENT={
    "parikrma fc":[
        _india_row("2026-09-15","Bengaluru FC",0,0,"Visitante","Bangalore Super Division"),
        _india_row("2026-09-10","South United FC",0,4,"Visitante","Bangalore Super Division"),
    ],
    "fc real bengaluru":[
        _india_row("2026-09-18","Bengaluru FC",0,4,"Local","Bangalore Super Division"),
        _india_row("2026-09-15","South United FC",1,2,"Visitante","Bangalore Super Division"),
    ],
    "bangalore dream united":[
        _india_row("2026-09-18","Kickstart FC",0,1,"Visitante","Bangalore Super Division"),
        _india_row("2026-09-16","Roots FC",1,0,"Local","Bangalore Super Division"),
    ],
    "stride fc":[
        _india_row("2026-09-18","FC Bengaluru United",0,5,"Local","Bangalore Super Division"),
        _india_row("2026-09-10","Kickstart FC",0,0,"Visitante","Bangalore Super Division"),
    ],
    "bengaluru fc":[
        _india_row("2026-09-18","FC Real Bengaluru",4,0,"Visitante","Bangalore Super Division"),
        _india_row("2026-09-15","Parikrma FC",0,0,"Local","Bangalore Super Division"),
    ],
    "fc agniputhra":[
        _india_row("2026-09-21","South United FC",0,0,"Local","Bangalore Super Division"),
        _india_row("2026-09-16","Kodagu FC",1,2,"Visitante","Bangalore Super Division"),
    ],
    "kickstart fc":[
        _india_row("2026-09-18","Bangalore Dream United",1,0,"Local","Bangalore Super Division"),
        _india_row("2026-09-10","Stride FC",0,0,"Local","Bangalore Super Division"),
    ],
    "south united fc":[
        _india_row("2026-09-21","FC Agniputhra",0,0,"Visitante","Bangalore Super Division"),
        _india_row("2026-09-15","FC Real Bengaluru",2,1,"Local","Bangalore Super Division"),
        _india_row("2026-09-10","Parikrma FC",4,0,"Local","Bangalore Super Division"),
    ],
    "roots fc":[
        _india_row("2026-09-21","HAL SC",3,0,"Local","Bangalore Super Division"),
        _india_row("2026-09-16","Bangalore Dream United",0,1,"Visitante","Bangalore Super Division"),
    ],
    "hal sc":[
        _india_row("2026-09-21","Roots FC",0,3,"Visitante","Bangalore Super Division"),
        _india_row("2026-09-16","Technico FF",9,0,"Local","Bangalore Super Division"),
    ],
    "sc bengaluru":[
        _india_row("2026-09-22","MEG & Centre FC",1,2,"Visitante","Bangalore Super Division"),
        _india_row("2026-09-17","Bangalore City FC",2,2,"Local","Bangalore Super Division"),
    ],
    "bangalore city fc":[
        _india_row("2026-09-22","United Stars FC",3,0,"Local","Bangalore Super Division"),
        _india_row("2026-09-17","SC Bengaluru",2,2,"Visitante","Bangalore Super Division"),
    ],
    "rebels fc":[
        _india_row("2026-09-22","Technico FF",3,1,"Visitante","Bangalore Super Division"),
    ],
    "cfci u19":[
        _india_row("2026-02-22","Young Guns FC",2,2,"Local","Mumbai Super Division"),
        _india_row("2026-02-19","Somaiya FC",1,7,"Local","Mumbai Super Division"),
    ],
    "kopana fc":[
        _india_row("2026-01-27","Somaiya FC",1,0,"Visitante","Mumbai Super Division"),
        _india_row("2026-01-22","CFCI U19",1,1,"Visitante","Mumbai Super Division"),
    ],
}

def india_recent_team_stats(name, limit=RECENT_LIMIT):
    wanted=_norm_team_name(name)
    rows=INDIA_RECENT.get(wanted) or []
    if not rows:
        for k,v in INDIA_RECENT.items():
            if _names_compatible(wanted,k):
                rows=v; break
    if not rows:
        raise ValueError("No hay resultados publicados verificables de Super Division India para este equipo")
    return rows[:limit]

def summarize_team_with_fallback(name,limit=RECENT_LIMIT, peer=""):
    errors=[]
    try:
        rows=fotmob_recent_team_stats(name,limit,peer=peer)
        if rows:
            return _summary_from_rows(name,rows,"FotMob")
        errors.append("FotMob no entregó partidos finalizados verificables.")
    except Exception as e:
        errors.append(f"FotMob: {_http_error_kind(e)}")
    try:
        tid=sofascore_team_id(name)
        rows=recent_team_stats(tid,limit)
        if rows:
            return _summary_from_rows(name,rows,"SofaScore",source_status="FALLBACK") | {"source_note":" · ".join(errors)}
        errors.append("SofaScore no entregó partidos finalizados verificables.")
    except Exception as e:
        errors.append(f"SofaScore: {_http_error_kind(e)}")
    try:
        rows=espn_recent_team_stats(name,limit)
        if rows:
            return _summary_from_rows(name,rows,"ESPN",source_status="FALLBACK") | {"source_note":" · ".join(errors)+". Se utilizó ESPN; no se estimaron datos."}
        errors.append("ESPN no entregó partidos finalizados verificables.")
    except Exception as e:
        errors.append(f"ESPN: {_http_error_kind(e)}")
    try:
        rows=india_recent_team_stats(name,limit)
        if rows:
            return _summary_from_rows(name,rows,"India Super Division",source_status="FALLBACK") | {"source_note":" · ".join(errors)+". Marcadores publicados de Super Division India; SofaScore API 403."}
    except Exception as e:
        errors.append(f"India: {_http_error_kind(e)}")
    return _unavailable_summary(name," · ".join(errors)+" No se muestran valores inventados.","FotMob + SofaScore + ESPN")

def _unavailable_summary(name, reason, source="SofaScore"):
    fields={k:{"average":None,"range":None,"available_matches":0} for k in ("goals_for","goals_ht_for","goals_ht_against","goals_ht_total","shots","sot","corners","yellow","red","possession","fouls","throwins","tackles","offsides","freekicks","goalkicks","saves","crosses","blockedshots","woodwork","attacks","dangerousattacks")}
    empty={"wins":0,"draws":0,"losses":0}
    return {"team":name,"matches":0,"source":source,"source_status":"UNAVAILABLE","reason":reason,
            "metrics":fields,"records":{"all":empty,"home":empty,"away":empty},"recent":[],"corner_profile":{"available":False,"sample":0}}

@lru_cache(maxsize=256)
def summarize_team(name,limit=RECENT_LIMIT, peer=""):
    return summarize_team_with_fallback(name,limit,peer=peer)

def fotmob_logo_url(tid):
    try:
        tid=int(tid)
    except Exception:
        return ""
    if tid<=0:
        return ""
    return f"https://images.fotmob.com/image_resources/logo/teamlogo/{tid}.png"

def _logo_name_keys(name):
    raw=str(name or "").strip()
    if not raw:
        return []
    keys=[raw]
    cleaned=raw
    for tok in (" (W)", "(W)", " (F)", "(F)", " Women", " Women's", " WFC"):
        cleaned=cleaned.replace(tok, "")
    cleaned=cleaned.strip()
    if cleaned and cleaned not in keys:
        keys.append(cleaned)
    lk=_logo_key(cleaned)
    if lk and lk not in keys:
        keys.append(lk)
    return keys

def _fotmob_id_cached_only(name):
    """Solo coincidencia exacta. Nada de 'Real' = Real Madrid ni Barcelona SC = Barcelona."""
    for key in _logo_name_keys(name):
        for nk in (_logo_key(key),):
            if not nk:
                continue
            if nk in _FOTMOB_SEED:
                return _FOTMOB_SEED[nk]
            if nk in _FOTMOB_INDEX:
                return _FOTMOB_INDEX[nk]
            # "barcelona" solo si el nombre NO trae otro distintivo (sc, ecuador, etc.)
            if " " not in nk and nk in _FOTMOB_SEED:
                return _FOTMOB_SEED[nk]
    return None

def _local_fotmob_id(name):
    wanted=_norm_team_name(name)
    if not wanted:
        return None
    if wanted in URU_IDS:
        return URU_IDS[wanted]
    if wanted in _FOTMOB_SEED:
        return _FOTMOB_SEED[wanted]
    if wanted in _FOTMOB_INDEX:
        return _FOTMOB_INDEX[wanted]
    return None

def logo_for(name, team_id=None, extra_url=None):
    if extra_url:
        return extra_url
    if team_id:
        url=fotmob_logo_url(team_id)
        if url:
            return url
    if not name:
        return ""
    tid=_local_fotmob_id(name)
    if tid:
        url=fotmob_logo_url(tid)
        if url:
            return url
    if name in LOGOS:
        return LOGOS[name]
    aliases = {
        "Bayern Munich": "Bayern", "FC Bayern": "Bayern", "Bayern München": "Bayern",
        "Bodo/Glimt": "Bodø/Glimt", "Bodø": "Bodø/Glimt", "Bodo": "Bodø/Glimt",
        "FC Copenhagen": "Copenhagen", "København": "Copenhagen",
        "AC Horsens": "Horsens", "AZ Alkmaar": "AZ",
        "Schalke 04": "Schalke", "Olympique Marseille": "Marseille",
        "Beşiktaş": "Besiktas", "Cusco FC": "Cusco", "FBC Melgar": "Melgar",
        "Leon": "León", "Velez": "Vélez", "Athletico PR": "Athletico",
        "SV Ried": "Ried", "Slovan Bratislava": "Slovan",
        "Manchester United": "Man United", "RB Leipzig": "Leipzig",
        "Slavia Prague": "Slavia", "Real Madrid F": "Real Madrid",
        "Arsenal F": "Arsenal", "Wolfsburg F": "Wolfsburg", "Lyon F": "Lyon",
        "Atletico Madrid": "Atlético Madrid", "Paris Saint Germain": "PSG",
        "Paris Saint-Germain": "PSG", "Internazionale": "Inter",
        "Criciuma": "Criciúma",
    }
    for key in _logo_name_keys(name):
        alias=aliases.get(key, key)
        if alias in LOGOS:
            return LOGOS[alias]
        tid=_fotmob_id_cached_only(alias)
        if tid:
            return fotmob_logo_url(tid)
    return ""

@lru_cache(maxsize=1024)
def resolve_team_logo(name):
    """Solo escudo si el nombre cierra exacto. Mejor vacío que el de otro club."""
    url=logo_for(name)
    if url:
        return url
    base=str(name or "")
    for tok in (" (W)","(W)"," Women"," Women's"," WFC"):
        base=base.replace(tok,"")
    base=base.strip()
    if base and base!=name:
        url=logo_for(base)
        if url:
            return url
    # ESPN / TheSportsDB solo si el resultado se llama igual
    for fn,arg in ((espn_team_logo,name),(espn_team_logo,base),(thesportsdb_team_logo,name),(thesportsdb_team_logo,base)):
        try:
            u=fn(arg) if arg else ""
        except Exception:
            u=""
        if u:
            return u
    return ""

@lru_cache(maxsize=512)
def espn_team_logo(name):
    name=(name or "").strip()
    if not name:
        return ""
    try:
        q=urllib.parse.quote(name)
        data=_espn_get(f"https://site.web.api.espn.com/apis/search/v2?query={q}&limit=20&sport=soccer",timeout=8)
        def find_team(obj):
            if isinstance(obj,dict):
                if obj.get("id") and _espn_team_name_match(name,obj):
                    return obj
                for v in obj.values():
                    r=find_team(v)
                    if r: return r
            elif isinstance(obj,list):
                for v in obj:
                    r=find_team(v)
                    if r: return r
            return None
        obj=find_team(data)
        if obj:
            for key in ("logo","image","imageUrl"):
                u=obj.get(key)
                if isinstance(u,str) and u.startswith("http"): return u
            for x in (obj.get("logos") or obj.get("images") or []):
                if isinstance(x,str) and x.startswith("http"): return x
                if isinstance(x,dict):
                    u=x.get("href") or x.get("url") or x.get("image")
                    if isinstance(u,str) and u.startswith("http"): return u
    except Exception:
        pass
    return ""


@lru_cache(maxsize=1024)
def thesportsdb_team_logo(name):
    """Busca el escudo por nombre en TheSportsDB y lo cachea."""
    name=(name or "").strip()
    if not name:
        return ""
    try:
        q=urllib.parse.quote(name)
        data=_json_get(f"{THESPORTSDB}/searchteams.php?t={q}", timeout=8)
        teams=(data or {}).get("teams") or []
        if not teams:
            return ""
        low=name.casefold()
        team=next((t for t in teams if str(t.get("strTeam","")).strip().casefold()==low), None)
        if not team:
            return ""
        badge=team.get("strTeamBadge") or team.get("strTeamLogo") or ""
        return badge if isinstance(badge,str) and badge.startswith("http") else ""
    except Exception:
        return ""


MATCHES = [
    dict(hora="12:45", pais="Alemania", sexo="M", liga="DFB Pokal",
         local="Osnabrück", visita="Bayern", tens="Baja",
         goles="4–6", ht="2", corn="10–13", tarj="3–4", rem="6–8 · 20–25", sot="2 · 8–11",
         ir="Bayern −2.5 · +3.5 goles", no="−2.5 goles · +8.5"),
    dict(hora="17:30", pais="Brasil", sexo="M", liga="Serie A",
         local="Flamengo", visita="Mirassol", tens="Baja",
         goles="2–3", ht="1", corn="10–13", tarj="3–4", rem="17–20 · 7–9", sot="6–8 · 2–3",
         ir="+1.5 · −3.5 · Fla −1.5", no="1.25 seco"),
    dict(hora="11:30", pais="Austria", sexo="M", liga="Bundesliga AT",
         local="Austria Viena", visita="Tirol", tens="Baja",
         goles="2–3", ht="1", corn="9–11", tarj="3–4", rem="14–16 · 8–10", sot="5–6 · 3",
         ir="+1.5 · −3.5", no="Tirol seco"),
    dict(hora="13:30", pais="Austria", sexo="M", liga="Bundesliga AT",
         local="Salzburg", visita="Rapid", tens="Media",
         goles="2–3", ht="1", corn="10–12", tarj="4", rem="14–16 · 9–11", sot="5–6 · 3–4",
         ir="+1.5 · −3.5", no="−1.5 goles"),
    dict(hora="19:15", pais="Argentina", sexo="M", liga="Copa Argentina",
         local="Vélez", visita="Boca", tens="ALTA",
         goles="1–2", ht="0–1", corn="8–11", tarj="5–7", rem="11–13 · 10–12", sot="3–5 · 3–5",
         ir="−2.5 goles · +5.5 tarjetas", no="−5.5 tarjetas · 1X2 seco"),
    dict(hora="18:00", pais="Argentina", sexo="M", liga="Primera Nacional",
         local="Colegiales", visita="Midland", tens="Media",
         goles="2", ht="0–1", corn="8–10", tarj="4–5", rem="11–13 · 9–11", sot="3–5 · 3–4",
         ir="+1.5 · −2.5", no="+3.5"),
    dict(hora="04:30", pais="Australia", sexo="M", liga="NSW PL",
         local="Marconi", visita="NWS Spirit", tens="Baja",
         goles="3", ht="1–2", corn="10–12", tarj="3–4", rem="13–16 · 11–14", sot="5–7 · 4–6",
         ir="+2.5 · BTTS", no="−1.5 · bank"),
    dict(hora="04:30", pais="Australia", sexo="M", liga="NSW PL",
         local="Sutherland", visita="Manly", tens="Baja",
         goles="3", ht="1–2", corn="10", tarj="3–4", rem="12–15 · 12–15", sot="4–6 · 4–6",
         ir="+2.5", no="−1.5 · bank"),
    dict(hora="01:30", pais="Australia", sexo="M", liga="NT Premier League",
         local="Port Darwin", visita="Casuarina", tens="Baja",
         goles="3–4", ht="1–2", corn="8–12", tarj="3–4", rem="12–16 · 11–15", sot="5–7 · 4–6",
         ir="+2.5 · +3.5 si 1.80+", no="−2.5 · bank"),
    dict(hora="14:00", pais="Inglaterra", sexo="M", liga="Championship",
         local="Burnley", visita="Middlesbrough", tens="Media",
         goles="2", ht="1", corn="9–12", tarj="3–5", rem="12–14 · 11–13", sot="4–5 · 4–5",
         ir="+1.5 · −3.5", no="+3.5 masivo"),
    dict(hora="13:45", pais="Inglaterra", sexo="M", liga="Championship",
         local="Millwall", visita="Wrexham", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="4–6", rem="13–15 · 10–12", sot="4–5 · 3–4",
         ir="+1.5 · +3.5 tarjetas", no="−2.5 tarjetas"),
    dict(hora="13:45", pais="Inglaterra", sexo="M", liga="Championship",
         local="QPR", visita="Cardiff", tens="Media",
         goles="2", ht="1", corn="10", tarj="4", rem="12–14 · 11–13", sot="4–5 · 3–4",
         ir="+1.5", no="+3.5"),
    dict(hora="13:45", pais="Inglaterra", sexo="M", liga="Championship",
         local="West Brom", visita="Charlton", tens="Baja",
         goles="2", ht="1", corn="10", tarj="3–4", rem="13–15 · 10–12", sot="4–5 · 3–4",
         ir="+1.5 · −3.5", no="+4.5"),
    dict(hora="13:45", pais="Escocia", sexo="M", liga="Premiership",
         local="Celtic", visita="Aberdeen", tens="Media",
         goles="2–3", ht="1", corn="10–12", tarj="3–4", rem="16–19 · 7–9", sot="6–8 · 2–3",
         ir="Celtic · +1.5", no="Aberdeen seco"),
    dict(hora="14:00", pais="Escocia", sexo="M", liga="Premiership",
         local="Falkirk", visita="Rangers", tens="Media+",
         goles="2–3", ht="1", corn="10", tarj="4–5", rem="8–10 · 15–18", sot="2–3 · 5–7",
         ir="Rangers · +1.5", no="−1.5"),
    dict(hora="07:00", pais="Italia", sexo="M", liga="Coppa Italia",
         local="Sassuolo", visita="Frosinone", tens="Baja+",
         goles="2", ht="0–1", corn="8–10", tarj="3–4", rem="12–14 · 10–12", sot="4 · 3–4",
         ir="−2.5 · −5.5 tarjetas", no="+3.5"),
    dict(hora="10:00", pais="Italia", sexo="M", liga="Coppa Italia",
         local="Udinese", visita="Venezia", tens="Media",
         goles="2", ht="0–1", corn="9", tarj="4", rem="12–14 · 10–12", sot="4 · 3–4",
         ir="−2.5 · +3.5 tarjetas", no="+3.5 goles"),
    dict(hora="20:25", pais="Colombia", sexo="M", liga="BetPlay",
         local="Santa Fe", visita="Millonarios", tens="ALTA",
         goles="1–2", ht="0–1", corn="8–11", tarj="5–7", rem="10–12 · 11–13", sot="3–4 · 3–4",
         ir="−2.5 · +5.5 tarjetas", no="−5.5 tarjetas"),
    dict(hora="18:00", pais="Paraguay", sexo="M", liga="Primera",
         local="Olimpia", visita="Guaraní", tens="ALTA",
         goles="2", ht="0–1", corn="9–11", tarj="5–6", rem="11–13 · 10–12", sot="3–5 · 3–4",
         ir="−2.5 · +4.5 tarjetas", no="−5.5 tarjetas"),
    dict(hora="20:00", pais="Ecuador", sexo="M", liga="LigaPro",
         local="Barcelona SC", visita="IDV", tens="Media+",
         goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="11–13 · 12–14", sot="4–5 · 4–5",
         ir="+1.5 · −3.5", no="+3.5"),
    dict(hora="16:00", pais="Chile", sexo="M", liga="Liga de Primera",
         local="Coquimbo", visita="U. Concepción", tens="Baja",
         goles="2–3", ht="1", corn="8–10", tarj="3–5", rem="13–15 · 9–11", sot="4–6 · 3–4",
         ir="+1.5 · −3.5", no="+4.5"),
    dict(hora="21:30", pais="México", sexo="M", liga="Leagues Cup",
         local="Rayados", visita="América", tens="ALTA",
         goles="2–3", ht="1", corn="9–12", tarj="5–7", rem="12–14 · 11–13", sot="4–5 · 4–5",
         ir="+4.5 tarjetas · −3.5", no="−5.5 tarjetas"),
    dict(hora="19:00", pais="México", sexo="M", liga="Leagues Cup",
         local="Toluca", visita="León", tens="Media+",
         goles="2–3", ht="1", corn="9–12", tarj="4–6", rem="12–15 · 11–13", sot="4–6 · 4–5",
         ir="+1.5 · +4.5 tarjetas", no="−3.5 tarjetas"),
    dict(hora="23:00*", pais="Islas Salomón", sexo="M", liga="S-League",
         local="Marist Fire", visita="Malaita Kingz", tens="Baja+",
         goles="3–4", ht="1–2", corn="8–12", tarj="3–5", rem="12–16 · 12–16", sot="5–7 · 5–7",
         ir="+2.5 / +3.5 ficha", no="bank · −2.5"),
    dict(hora="LIVE", pais="India", sexo="M", liga="Mizoram PL",
         local="Mizoram Police", visita="Ramthar Veng", tens="Baja+",
         goles="3–4", ht="1–2", corn="8–12", tarj="3–5", rem="12–16 · 12–16", sot="5–7 · 5–7",
         ir="−5.5 techo (3 goles al 27’) · ficha", no="bank · +4.5 grande"),
    dict(hora="18:00 J", pais="Brasil", sexo="M", liga="Copa do Brasil",
         local="Grêmio", visita="Internacional", tens="MÁX",
         goles="1–2", ht="0–1", corn="8–11", tarj="5–8", rem="11–13 · 11–13", sot="3–5 · 3–5",
         ir="−2.5 · +5.5 tarjetas", no="−5.5 tarjetas · roja"),
    dict(hora="18:00 J", pais="Brasil", sexo="M", liga="Copa do Brasil",
         local="Santos", visita="Palmeiras", tens="ALTA",
         goles="2", ht="0–1", corn="9–11", tarj="5–7", rem="11–13 · 12–14", sot="3–5 · 4–5",
         ir="−2.5 · +4.5 tarjetas", no="−5.5 tarjetas"),
    dict(hora="12:00", pais="Bulgaria", sexo="M", liga="First League",
         local="Slavia Sofia", visita="Levski", tens="ALTA",
         goles="1–2", ht="0–1", corn="8–10", tarj="5–7", rem="10–12 · 12–14", sot="3–4 · 4–5",
         ir="−2.5 · +4.5 tarjetas", no="−5.5 tarjetas"),
    dict(hora="13:00", pais="Dinamarca", sexo="M", liga="Superliga",
         local="Aarhus", visita="Midtjylland", tens="Media",
         goles="2–3", ht="1", corn="9–11", tarj="3–5", rem="11–13 · 13–15", sot="4–5 · 5–6",
         ir="+1.5 · −3.5", no="−1.5"),
    dict(hora="13:30", pais="Bélgica", sexo="M", liga="Pro League",
         local="St Truiden", visita="Union SG", tens="Media",
         goles="2–3", ht="1", corn="9–11", tarj="3–4", rem="9–11 · 14–16", sot="3–4 · 5–6",
         ir="Union / +1.5", no="−1.5"),
    dict(hora="12:30", pais="Sudáfrica", sexo="M", liga="Premier",
         local="Sundowns", visita="Milford", tens="Baja",
         goles="3–4", ht="1–2", corn="10–12", tarj="3–4", rem="16–20 · 6–8", sot="6–8 · 2–3",
         ir="Sundowns −1.5 · +2.5", no="−1.5"),
    dict(hora="10:30", pais="Italia", sexo="F", liga="UWCL",
         local="Inter", visita="Wolfsburg", tens="Baja",
         goles="2–3", ht="1", corn="8–10", tarj="3–4", rem="8–10 · 14–16", sot="3 · 5–6",
         ir="Wolfsburg / +1.5", no="−1.5"),
    dict(hora="10:30", pais="Francia", sexo="F", liga="UWCL",
         local="PSG", visita="Frankfurt", tens="Media",
         goles="2–3", ht="1", corn="9–11", tarj="3–4", rem="13–15 · 11–13", sot="5 · 4",
         ir="+1.5 · BTTS", no="−1.5"),
    dict(hora="11:00", pais="España", sexo="F", liga="UWCL",
         local="Real Sociedad", visita="Chelsea", tens="Baja",
         goles="3–4", ht="1–2", corn="9–11", tarj="3–4", rem="8–10 · 16–20", sot="3 · 6–8",
         ir="Chelsea −1.5 · +2.5", no="−1.5"),
    dict(hora="12:00", pais="España", sexo="F", liga="UWCL",
         local="Real Madrid", visita="Ajax", tens="Baja",
         goles="2–3", ht="1", corn="9–11", tarj="3", rem="14–16 · 8–10", sot="5–6 · 2–3",
         ir="Madrid · +1.5", no="Ajax seco"),
    dict(hora="12:30", pais="Italia", sexo="F", liga="UWCL",
         local="Juventus", visita="St. Pölten", tens="Baja",
         goles="3–4", ht="1–2", corn="9–11", tarj="3", rem="16–20 · 6–8", sot="6–8 · 2",
         ir="Juve −1.5 · +2.5", no="−1.5"),
    dict(hora="11:00", pais="Dinamarca", sexo="F", liga="UWCL",
         local="Køge", visita="PSV", tens="Media",
         goles="2–3", ht="1", corn="9–10", tarj="3–4", rem="11–13 · 12–14", sot="4 · 4–5",
         ir="+1.5", no="−1.5"),
]

# Solo partidos del PDF. PENDIENTE hasta el silbatazo.
CERRADOS = [
    dict(
        partido=f"{m['local']} vs {m['visita']}",
        pick=m["ir"],
        ft="—",
        extra=f"{m['pais']} · {m['liga']} · {m['hora']} PE",
        estado="PENDIENTE",
    )
    for m in MATCHES
]
for c in CERRADOS:
    if c["partido"] == "Sassuolo vs Frosinone":
        c["ft"] = "1-1 (4-3 pen.)"
        c["extra"] = "2 goles · 5 amarillas. −2.5 y −5.5 tarjetas"
        c["estado"] = "VERDE"
    elif c["partido"] == "Marconi vs NWS Spirit":
        c["ft"] = "1-3"
        c["extra"] = "+2.5 y BTTS"
        c["estado"] = "VERDE"
    elif c["partido"] == "Sutherland vs Manly":
        c["ft"] = "1-1 (4-5 pen.)"
        c["extra"] = "90’ = 2 goles. +2.5 no salió"
        c["estado"] = "ROJO"
    elif c["partido"] == "Port Darwin vs Casuarina":
        c["ft"] = "5-2"
        c["extra"] = "+2.5 y +3.5"
        c["estado"] = "VERDE"
    elif c["partido"] == "Marist Fire vs Malaita Kingz":
        c["ft"] = "1-4"
        c["extra"] = "+2.5 y +3.5"
        c["estado"] = "VERDE"
    elif c["partido"] == "Mizoram Police vs Ramthar Veng":
        c["ft"] = "3-3"
        c["extra"] = "6 goles. −5.5 no salió"
        c["estado"] = "ROJO"
    elif c["partido"] == "Austria Viena vs Tirol":
        c["ft"] = "0-1"
        c["extra"] = "+1.5 no · −3.5 sí"
        c["estado"] = "ROJO"
    elif c["partido"] == "Udinese vs Venezia":
        c["ft"] = "2-1"
        c["extra"] = "3 goles. −2.5 no"
        c["estado"] = "ROJO"
    elif c["partido"] == "Slavia Sofia vs Levski":
        c["ft"] = "1-2"
        c["extra"] = "3 goles. −2.5 no · derbi"
        c["estado"] = "ROJO"
    elif c["partido"] == "Sundowns vs Milford":
        c["ft"] = "2-0"
        c["extra"] = "Sundowns −1.5 sí · +2.5 no"
        c["estado"] = "VERDE"
    elif c["partido"] == "Osnabrück vs Bayern":
        c["ft"] = "1-4"
        c["extra"] = "5 goles. +1.5 sí · −3.5 no"
        c["estado"] = "VERDE"
    elif c["partido"] == "Celtic vs Aberdeen":
        c["ft"] = "3-0"
        c["extra"] = "Celtic gana · +1.5 / +2.5"
        c["estado"] = "VERDE"
    elif c["partido"] == "Flamengo vs Mirassol":
        c["ft"] = "2-0"
        c["extra"] = "+1.5 sí · −3.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "Coquimbo vs U. Concepción":
        c["ft"] = "1-0"
        c["extra"] = "+1.5 no · −3.5 sí"
        c["estado"] = "ROJO"
    elif c["partido"] == "Vélez vs Boca":
        c["ft"] = "0-0 (4-3 pen. Boca)"
        c["extra"] = "2 tarjetas. +5.5 cartones no"
        c["estado"] = "ROJO"
    elif c["partido"] == "Rayados vs América":
        c["ft"] = "2-2"
        c["extra"] = "+1.5 sí · 2 tarjetas · córners sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "Toluca vs León":
        c["ft"] = "2-0"
        c["extra"] = "+1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "Millwall vs Wrexham":
        c["ft"] = "0-3"
        c["extra"] = "+1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "QPR vs Cardiff":
        c["ft"] = "2-1"
        c["extra"] = "+1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "Burnley vs Middlesbrough":
        c["ft"] = "1-1"
        c["extra"] = "+1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "West Brom vs Charlton":
        c["ft"] = "1-1"
        c["extra"] = "+1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "Real Sociedad vs Chelsea":
        c["ft"] = "0-1"
        c["extra"] = "Chelsea gana · +1.5 no"
        c["estado"] = "ROJO"
    elif c["partido"] == "Real Madrid vs Ajax":
        c["ft"] = "2-1"
        c["extra"] = "+1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "Juventus vs St. Pölten":
        c["ft"] = "1-1"
        c["extra"] = "+1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "Salzburg vs Rapid":
        c["ft"] = "5-1"
        c["extra"] = "+1.5 sí · 6 goles"
        c["estado"] = "VERDE"
    elif c["partido"] == "Colegiales vs Midland":
        c["ft"] = "3-0"
        c["extra"] = "+1.5 sí · 1X Colegiales"
        c["estado"] = "VERDE"
    elif c["partido"] == "Falkirk vs Rangers":
        c["ft"] = "1-2"
        c["extra"] = "+1.5 sí · gana Rangers"
        c["estado"] = "VERDE"
    elif c["partido"] == "Santa Fe vs Millonarios":
        c["ft"] = "3-2"
        c["extra"] = "+1.5 sí · clásico · 1 roja"
        c["estado"] = "VERDE"
    elif c["partido"] == "Olimpia vs Guaraní":
        c["ft"] = "1-1"
        c["extra"] = "+1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "Barcelona SC vs IDV":
        c["ft"] = "2-1"
        c["extra"] = "+1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "Aarhus vs Midtjylland":
        c["ft"] = "0-2"
        c["extra"] = "+1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "St Truiden vs Union SG":
        c["ft"] = "0-3"
        c["extra"] = "+1.5 sí · gana Union"
        c["estado"] = "VERDE"
    elif c["partido"] == "Inter vs Wolfsburg":
        c["ft"] = "3-1 (5-4 pen.)"
        c["extra"] = "vuelta · global 3-3 · +1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "PSG vs Frankfurt":
        c["ft"] = "5-1 (t.e.)"
        c["extra"] = "vuelta · global 6-2 · +1.5 sí"
        c["estado"] = "VERDE"
    elif c["partido"] == "Køge vs PSV":
        c["ft"] = "1-1"
        c["extra"] = "vuelta · Køge pasa 2-1 · +1.5 sí"
        c["estado"] = "VERDE"

# Resultados 03/09 (hora PE). Se pintan en la misma carta.
CERRADOS += [
    dict(partido="Palermo vs Mantova", pick="1X Palermo · +1.5",
         ft="5-2", extra="+1.5 sí · 1X sí", estado="VERDE"),
    dict(partido="Copenhagen vs Nordsjælland", pick="+1.5 · 1X Copenhague",
         ft="2-0", extra="+1.5 sí · 1X sí", estado="VERDE"),
    dict(partido="Al Fayha vs Al Kholood", pick="+1.5",
         ft="2-2", extra="+1.5 sí", estado="VERDE"),
    dict(partido="NEOM vs Al Khaleej", pick="1X NEOM · +1.5",
         ft="3-0", extra="+1.5 sí · 1X sí", estado="VERDE"),
    dict(partido="Diriyah vs Al Qadsiah", pick="X2 Qadsiah · +1.5",
         ft="0-2", extra="+1.5 sí · X2 sí", estado="VERDE"),
    dict(partido="Mjällby vs Djurgården", pick="+1.5",
         ft="0-2", extra="+1.5 sí", estado="VERDE"),
    dict(partido="Hibernian vs Hearts", pick="+1.5 · +4.5 tarjetas",
         ft="1-3", extra="+1.5 sí · 4 goles", estado="VERDE"),
    dict(partido="Cagliari vs Verona", pick="+1.5 · −3.5",
         ft="1-2", extra="+1.5 sí · −3.5 sí", estado="VERDE"),
    dict(partido="Lech Poznań vs Jagiellonia", pick="+1.5",
         ft="2-1", extra="+1.5 sí", estado="VERDE"),
    dict(partido="Győr vs Ferencváros", pick="X2 Fradi · +1.5",
         ft="0-3", extra="+1.5 sí · X2 sí", estado="VERDE"),
    dict(partido="H. Tel Aviv vs Beitar", pick="+1.5 · +4.5 tarjetas",
         ft="3-0", extra="+1.5 sí", estado="VERDE"),
    dict(partido="U. Católica vs Aucas", pick="+1.5",
         ft="1-1", extra="+1.5 sí", estado="VERDE"),
    dict(partido="Rayo Zuliano vs Carabobo", pick="+1.5 · ficha",
         ft="4-3", extra="+1.5 sí · 7 goles", estado="VERDE"),
    dict(partido="Al Ahly vs Smouha", pick="1X Ahly · +1.5",
         ft="1-0", extra="1X sí · +1.5 no", estado="ROJO"),
    dict(partido="Panathinaikos vs Niki Volos", pick="1 Pana · +1.5",
         ft="1-0", extra="Pana gana · +1.5 no", estado="ROJO"),
    dict(partido="Real Sociedad vs Celta", pick="+1.5 · −3.5",
         ft="0-0", extra="+1.5 no · −3.5 sí", estado="ROJO"),
    dict(partido="Toulouse vs Lille", pick="+1.5 · X2 Lille",
         ft="0-1", extra="X2 sí · +1.5 no", estado="ROJO"),
    dict(partido="Anderlecht vs Kortrijk", pick="1X Anderlecht · +1.5",
         ft="1-0", extra="1X sí · +1.5 no", estado="ROJO"),
    dict(partido="Gent vs OH Leuven", pick="+1.5 · 1X Gent",
         ft="1-0", extra="1X sí · +1.5 no", estado="ROJO"),
    dict(partido="Basel vs Sion", pick="1X Basel · +1.5",
         ft="1-2", extra="+1.5 sí · 1X no", estado="ROJO"),
    dict(partido="Lugano vs Servette", pick="+1.5",
         ft="1-0", extra="+1.5 no", estado="ROJO"),
    dict(partido="Raków vs Górnik", pick="+1.5 · 1X Raków",
         ft="1-2", extra="+1.5 sí · 1X no", estado="ROJO"),
    dict(partido="Grêmio vs Internacional", pick="+1.5 · 12 · +4.5 tarjetas",
         ft="3-1", extra="+1.5 sí · 12 sí · 7 amarillas", estado="VERDE"),
    dict(partido="América Cali vs Alianza", pick="1 América · +0.5 América · +1.5",
         ft="3-0", extra="América gana · +1.5 sí", estado="VERDE"),
    dict(partido="Pereira vs Medellín", pick="+1.5 · +4.5 tarjetas",
         ft="0-3", extra="+1.5 sí", estado="VERDE"),
    dict(partido="Libertad vs Emelec", pick="+1.5",
         ft="1-1", extra="+1.5 sí", estado="VERDE"),
    dict(partido="Leones vs Orense", pick="+1.5 · ficha",
         ft="1-0", extra="+1.5 no", estado="ROJO"),
    dict(partido="Náutico vs Botafogo SP", pick="+1.5",
         ft="1-0", extra="+1.5 no", estado="ROJO"),
]

CERRADOS += [
    dict(partido="Lyon vs Auxerre", pick="1X Lyon · +0.5 1T · +1.5",
         ft="3-1", extra="+1.5 sí · Lyon gana · gol 1T sí", estado="VERDE"),
    dict(partido="Fredrikstad vs Bodø/Glimt", pick="X2 Glimt · +1.5 · +0.5 1T",
         ft="1-2", extra="+1.5 sí · X2 Glimt", estado="VERDE"),
    dict(partido="Aalesund vs Start", pick="+1.5",
         ft="2-0", extra="+1.5 sí", estado="VERDE"),
    dict(partido="London City Lionesses vs Man Utd F", pick="X2 United F · +0.5 1T · +1.5",
         ft="2-1", extra="+1.5 sí · gol 1T sí · United pierde", estado="ROJO"),
    dict(partido="Watford F vs Burnley F", pick="+1.5 · ficha",
         ft="0-0", extra="+1.5 no", estado="ROJO"),
    dict(partido="Hibernian F vs Glasgow City", pick="+1.5 · X2 City",
         ft="2-1", extra="+1.5 sí · City pierde", estado="ROJO"),
    dict(partido="Genoa vs Como", pick="+1.5 · −3.5",
         ft="1-4", extra="+1.5 sí · −3.5 no (5 goles)", estado="ROJO"),
    dict(partido="Lommel vs Club Brugge", pick="X2 Brugge · +1.5 · +0.5 1T",
         ft="0-1", extra="X2 Brugge sí · +1.5 no", estado="ROJO"),
    dict(partido="Ipswich vs Liverpool", pick="X2 Liverpool · +1.5",
         ft="0-2", extra="Liverpool gana · +1.5 sí · Isak 6' y 9'", estado="VERDE"),
    dict(partido="Betis vs Real Madrid", pick="X2 Madrid · +1.5",
         ft="1-0", extra="Madrid pierde · +1.5 no", estado="ROJO"),
    dict(partido="Sparta Rotterdam vs PEC Zwolle", pick="+1.5",
         ft="2-2", extra="+1.5 sí", estado="VERDE"),
    dict(partido="Sandefjord vs Viking", pick="+1.5",
         ft="1-1", extra="+1.5 sí", estado="VERDE"),
    dict(partido="PSG vs Monaco", pick="+1.5 · 1X PSG",
         ft="1-2", extra="+1.5 sí · PSG pierde", estado="ROJO"),
    dict(partido="Porto vs Moreirense", pick="1 Porto · +0.5 1T · +1.5",
         ft="2-1", extra="Porto gana · +1.5 sí · gol 1T sí", estado="VERDE"),
    dict(partido="Stuttgart vs Köln", pick="+1.5",
         ft="4-1", extra="+1.5 sí · 5 goles", estado="VERDE"),
    dict(partido="NYCFC vs Nashville", pick="+1.5 · X2 Nashville",
         ft="0-0", extra="+1.5 no · X2 sí (empate)", estado="ROJO"),
    dict(partido="Viborg vs Lyngby", pick="+1.5",
         ft="0-2", extra="+1.5 sí", estado="VERDE"),
    dict(partido="Juárez vs Pachuca", pick="X2 Pachuca · +1.5 · +0.5 1T",
         ft="0-1", extra="X2 Pachuca sí · +1.5 no · 1T 0-0", estado="ROJO"),
    dict(partido="Utah Royals vs Boston Legacy", pick="+1.5",
         ft="1-2", extra="+1.5 sí", estado="VERDE"),
    dict(partido="Bay FC vs Kansas City Current", pick="+1.5 · X2 Current",
         ft="1-1", extra="+1.5 sí · X2 sí", estado="VERDE"),
]

# Resultados 05/09 — slates MATCHES_05 (IR de la carta)
CERRADOS += [
    dict(partido="Fiorentina vs Torino", pick="−2.5 · Under 2.5",
         ft="1-2", extra="3 goles · HT 0-0 · Under no", estado="ROJO"),
    dict(partido="Athletic vs Atlético Madrid", pick="−2.5 · X2 Atlético",
         ft="3-0", extra="HT 0-0 · 3 goles 2T · Under no · X2 no", estado="ROJO"),
    dict(partido="Fulham vs Crystal Palace", pick="−2.5 · Under 2.5",
         ft="2-3", extra="5 goles · HT 2-1 · Under no", estado="ROJO"),
    dict(partido="Paderborn vs Freiburg", pick="−2.5 · línea 2.5",
         ft="0-1", extra="1 gol · Under sí", estado="VERDE"),
    dict(partido="Gladbach vs Elversberg", pick="−2.5 ficha · +1.5",
         ft="3-4", extra="+1.5 sí · −2.5 no · 7 goles", estado="ROJO"),
    dict(partido="Inter vs Napoli", pick="−2.5 · +1.5",
         ft="3-2", extra="HT 0-0 · 5 goles 2T · +1.5 sí · −2.5 no", estado="ROJO"),
    dict(partido="Newcastle vs Bournemouth", pick="+1.5 · 1X Newcastle",
         ft="2-2", extra="+1.5 sí · 1X sí", estado="VERDE"),
    dict(partido="Brentford vs Sunderland", pick="+1.5",
         ft="1-1", extra="+1.5 sí", estado="VERDE"),
    dict(partido="Brighton vs Leeds", pick="+1.5",
         ft="1-1", extra="+1.5 sí", estado="VERDE"),
    dict(partido="Nottm Forest vs Tottenham", pick="+1.5 · X2 Spurs",
         ft="0-0", extra="X2 sí · +1.5 no · el más cerrado del día", estado="ROJO"),
    dict(partido="Man City vs Coventry", pick="City −1.5 · +2.5 · +0.5 1T",
         ft="1-0", extra="Haaland 26' · −1.5 no · +2.5 no", estado="ROJO"),
    dict(partido="Hull vs Aston Villa", pick="X2 Villa · +1.5",
         ft="0-0", extra="X2 sí · +1.5 no · cerrado", estado="ROJO"),
    dict(partido="Leverkusen vs Union Berlin", pick="1X Leverkusen · +1.5",
         ft="4-0", extra="1X sí · +1.5 sí", estado="VERDE"),
    dict(partido="Bremen vs Leipzig", pick="X2 Leipzig · +1.5",
         ft="3-1", extra="+1.5 sí · Leipzig pierde", estado="ROJO"),
    dict(partido="Schalke vs Bayern", pick="Bayern −1.5 · +2.5",
         ft="0-0", extra="0-0 · −1.5 no · +2.5 no · Under era el pick", estado="ROJO"),
    dict(partido="Roma vs Atalanta", pick="+1.5 · −3.5",
         ft="2-1", extra="+1.5 sí · −3.5 sí · Soulé 93'", estado="VERDE"),
]

# 1 / X / 2 y dobles: 1X local no pierde · X2 visita no pierde · 12 no empate
DC = {
    "Osnabrück": ("2", "X2", "Gana Bayern · visita no pierde"),
    "Flamengo": ("1", "1X", "Gana Flamengo · no pierdas 1.25 seco"),
    "Austria Viena": ("1", "1X", "Gana o empata Austria"),
    "Salzburg": ("1", "1X", "Gana o empata Salzburg"),
    "Vélez": ("X", "12", "Abierto. Mejor 12 o 1X Boca (X2) que 1 seco"),
    "Colegiales": ("1", "1X", "Gana o empata Colegiales"),
    "Marconi": ("1", "1X", "Gana o empata Marconi"),
    "Sutherland": ("X", "12", "Cualquiera · 12 si hay goles"),
    "Port Darwin": ("1", "1X", "Gana o empata Port Darwin"),
    "Burnley": ("X", "1X", "Muy parejo · 1X Burnley"),
    "Millwall": ("1", "1X", "Gana o empata Millwall"),
    "QPR": ("1", "1X", "Gana o empata QPR"),
    "West Brom": ("1", "1X", "Gana o empata West Brom"),
    "Celtic": ("1", "1X", "Gana Celtic"),
    "Falkirk": ("2", "X2", "Gana Rangers · visita no pierde"),
    "Sassuolo": ("1", "1X", "Gana o empata Sassuolo"),
    "Udinese": ("1", "1X", "Gana o empata Udinese"),
    "Santa Fe": ("X", "1X", "Clásico · 1X Santa Fe"),
    "Olimpia": ("1", "1X", "Gana o empata Olimpia"),
    "Barcelona SC": ("X", "X2", "IDV no pierde · X2"),
    "Coquimbo": ("1", "1X", "Gana o empata Coquimbo"),
    "Rayados": ("X", "1X", "Semi · 1X Rayados"),
    "Toluca": ("1", "1X", "Gana o empata Toluca"),
    "Marist Fire": ("X", "12", "Abierto · 12"),
    "Mizoram Police": ("X", "X2", "Live · Ramthar no pierde X2"),
    "Grêmio": ("X", "1X", "Gre-Nal · 1X Grêmio"),
    "Santos": ("X", "X2", "Palmeiras no pierde X2"),
    "Slavia Sofia": ("2", "X2", "Gana Levski · X2"),
    "Aarhus": ("2", "X2", "Midtjylland no pierde"),
    "St Truiden": ("2", "X2", "Gana Union SG"),
    "Sundowns": ("1", "1X", "Gana Sundowns"),
    "Inter": ("2", "X2", "Wolfsburg no pierde"),
    "PSG": ("1", "1X", "Gana o empata PSG"),
    "Real Sociedad": ("2", "X2", "Gana Chelsea"),
    "Real Madrid": ("1", "1X", "Gana Madrid"),
    "Juventus": ("1", "1X", "Gana Juventus"),
    "Køge": ("X", "1X", "Køge no pierde"),
}


MATCHES_03 = [
    dict(hora="17:00", pais="Brasil", sexo="M", liga="Copa do Brasil · vuelta",
         local="Grêmio", visita="Internacional", tens="MÁX",
         goles="1–2", ht="0–1", corn="8–11", tarj="5–7", rem="5–7 · 16–20", sot="2 · 5–8",
         ir="−2.5 · +4.5 tarjetas", no="Bank · +3.5 · −5.5 tarjetas",
         extra="Global 0-0. Clásico. Línea 1.5"),
    dict(hora="13:00", pais="España", sexo="M", liga="La Liga",
         local="Real Sociedad", visita="Celta", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 18–22", sot="2 · 6–9",
         ir="+1.5 · −3.5", no="Bank · 1 seco"),
    dict(hora="12:45", pais="Francia", sexo="M", liga="Ligue 1",
         local="Toulouse", visita="Lille", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 18–22", sot="2 · 6–9",
         ir="+1.5 · X2 Lille", no="Toulouse 1 seco"),
    dict(hora="13:45", pais="Escocia", sexo="M", liga="Premiership",
         local="Hibernian", visita="Hearts", tens="ALTA",
         goles="2–3", ht="1", corn="9–12", tarj="5–6", rem="5–7 · 18–22", sot="2 · 6–9",
         ir="+1.5 · +4.5 tarjetas", no="−5.5 tarjetas · bank"),
    dict(hora="12:30", pais="Bélgica", sexo="M", liga="Pro League",
         local="Anderlecht", visita="Kortrijk", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="6–8 · 20–24", sot="2 · 7–10",
         ir="1X Anderlecht · +1.5", no="Kortrijk ML"),
    dict(hora="12:30", pais="Bélgica", sexo="M", liga="Pro League",
         local="Gent", visita="OH Leuven", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="5–7 · 18–22", sot="2 · 6–9",
         ir="+1.5 · 1X Gent", no="Bank"),
    dict(hora="12:00", pais="Dinamarca", sexo="M", liga="Superliga",
         local="Copenhagen", visita="Nordsjælland", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="5–7 · 18–22", sot="2 · 6–9",
         ir="+1.5 · 1X Copenhague", no="−2.5"),
    dict(hora="11:00", pais="Suecia", sexo="M", liga="Allsvenskan",
         local="Mjällby", visita="Djurgården", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="5–7 · 16–20", sot="2 · 5–8",
         ir="+1.5", no="Bank"),
    dict(hora="12:30", pais="Suiza", sexo="M", liga="Super League",
         local="Basel", visita="Sion", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="6–8 · 20–24", sot="2 · 7–10",
         ir="1X Basel · +1.5", no="Sion ML"),
    dict(hora="12:30", pais="Suiza", sexo="M", liga="Super League",
         local="Lugano", visita="Servette", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 18–22", sot="2 · 6–9",
         ir="+1.5", no="Bank"),
    dict(hora="10:00", pais="Italia", sexo="M", liga="Coppa Italia",
         local="Palermo", visita="Mantova", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="1X Palermo · +1.5", no="Mantova ML"),
    dict(hora="13:00", pais="Italia", sexo="M", liga="Coppa Italia",
         local="Cagliari", visita="Verona", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 18–22", sot="2 · 6–9",
         ir="+1.5 · −3.5", no="1 seco"),
    dict(hora="10:00", pais="Polonia", sexo="M", liga="Ekstraklasa",
         local="Raków", visita="Górnik", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5 · 1X Raków", no="Bank"),
    dict(hora="12:30", pais="Polonia", sexo="M", liga="Ekstraklasa",
         local="Lech Poznań", visita="Jagiellonia", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 18–22", sot="2 · 6–9",
         ir="+1.5", no="Bank"),
    dict(hora="12:30", pais="Hungría", sexo="M", liga="NB I",
         local="Győr", visita="Ferencváros", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 18–22", sot="2 · 6–9",
         ir="X2 Fradi · +1.5", no="Győr ML"),
    dict(hora="19:00", pais="Colombia", sexo="M", liga="Liga BetPlay",
         local="América Cali", visita="Alianza", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5 · 1X América", no="Bank"),
    dict(hora="18:00", pais="Ecuador", sexo="M", liga="LigaPro",
         local="U. Católica", visita="Aucas", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5", no="Bank"),
    dict(hora="16:00", pais="Venezuela", sexo="M", liga="Liga FUTVE",
         local="Rayo Zuliano", visita="Carabobo", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5 · ficha", no="Bank · ligas raras"),
    dict(hora="21:00", pais="Colombia", sexo="M", liga="Liga BetPlay",
         local="Pereira", visita="Medellín", tens="Media+",
         goles="2–3", ht="1", corn="8–11", tarj="4–6", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5 · +4.5 tarjetas", no="Bank · −5.5 tarjetas"),
    dict(hora="20:00", pais="Ecuador", sexo="M", liga="LigaPro",
         local="Libertad", visita="Emelec", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5", no="Bank"),
    dict(hora="17:30", pais="Ecuador", sexo="M", liga="LigaPro",
         local="Leones", visita="Orense", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5 · ficha", no="Bank"),
    dict(hora="08:55", pais="Arabia", sexo="M", liga="Saudi Pro League",
         local="Al Fayha", visita="Al Kholood", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5", no="Bank"),
    dict(hora="09:30", pais="Arabia", sexo="M", liga="Saudi Pro League",
         local="NEOM", visita="Al Khaleej", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="1X NEOM · +1.5", no="Bank"),
    dict(hora="11:00", pais="Arabia", sexo="M", liga="Saudi Pro League",
         local="Diriyah", visita="Al Qadsiah", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="X2 Qadsiah · +1.5", no="Bank"),
    dict(hora="13:00", pais="Israel", sexo="M", liga="Premier League",
         local="H. Tel Aviv", visita="Beitar", tens="ALTA",
         goles="2–3", ht="1", corn="8–11", tarj="5–7", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5 · +4.5 tarjetas", no="−5.5 tarjetas · bank"),
    dict(hora="11:00", pais="Grecia", sexo="M", liga="Copa Grecia",
         local="Panathinaikos", visita="Niki Volos", tens="Baja",
         goles="2–4", ht="1", corn="9–12", tarj="3–4", rem="6–8 · 20–24", sot="2 · 7–10",
         ir="1 Pana · +1.5", no="Niki ML"),
    dict(hora="10:00", pais="Egipto", sexo="M", liga="Premier League",
         local="Al Ahly", visita="Smouha", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–4", rem="6–8 · 20–24", sot="2 · 7–10",
         ir="1X Ahly · +1.5", no="Bank"),
    dict(hora="19:00", pais="Brasil", sexo="M", liga="Serie B",
         local="Náutico", visita="Botafogo SP", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5 · ficha", no="Bank"),
]

NEED03 = {
    "Grêmio": "Ida 0-0. Copa. Los dos necesitan no perder; Inter empuja más fuera.",
    "Real Sociedad": "Puntos de mitad de tabla. Nadie se juega el año.",
    "Toulouse": "Lille pelea Europa. Toulouse no puede seguir abajo.",
    "Hibernian": "Derbi. Los dos necesitan los 3. Tensión alta.",
    "Anderlecht": "Local debe ganar para no perder el tren. Kortrijk hundido.",
    "Gent": "Gent a sumar de a 3. Leuven no exigía.",
    "Copenhagen": "Local líder/arriba. Nordsjælland también pelea arriba.",
    "Mjällby": "Puntos de media tabla. Sin urgencia máxima.",
    "Basel": "Basel no puede pinchar en casa. Sion vino a sumar.",
    "Lugano": "Lugano líder. Servette necesita puntos.",
    "Palermo": "Copa. Palermo favorito y debía pasar.",
    "Cagliari": "Copa. Los dos querían octavos. Abierto.",
    "Raków": "Ambos pelean arriba. Górnik no se conformaba.",
    "Lech Poznań": "Lech local fuerte. Jaga también pelea.",
    "Győr": "Fradi favorito claro. Győr no se jugaba tanto.",
    "América Cali": "Líder invicto. NECESITA ganar para no aflojar. Alianza desesperado (0 wins).",
    "U. Católica": "Ambos viven de sumar. Empate no les sirve del todo.",
    "Rayo Zuliano": "Puntos de liga. Sin final de copa.",
    "Pereira": "Medellín pelea arriba. Pereira necesita no caer en casa.",
    "Libertad": "Emelec urgido. Libertad también suma.",
    "Leones": "Ficha. Sin necesidad extrema.",
    "Al Fayha": "Mitad/abajo. Kholood más arriba, pero no es final.",
    "NEOM": "NEOM quería ganar en casa. Khaleej abajo.",
    "Diriyah": "Qadsiah pelea arriba. Diriyah local.",
    "H. Tel Aviv": "Derbi israelí. Los dos necesitan ganar.",
    "Panathinaikos": "Copa. Pana debía pasar sí o sí.",
    "Al Ahly": "Ahly favorito. Smouha a aguantar.",
    "Náutico": "Serie B. Suma de a 3, no copa.",
}
for m in MATCHES_03:
    m["dia"] = "03/09"
    m["need"] = NEED03.get(m["local"], "Sin urgencia extrema.")
    m["logo_l"] = logo_for(m["local"])
    m["logo_v"] = logo_for(m["visita"])
    m["res"] = "X"
    m["dc"] = "1X"
    m["res_txt"] = "Ficha. Una pata"
    m["gana"] = "Abierto / 1X local"
    if m["local"] in ("Grêmio", "Diriyah"):
        m["ht_gol"], m["ht_pct"] = "baja", "40–45%"
    elif m["local"] in ("Hibernian","H. Tel Aviv","Panathinaikos","Anderlecht","Al Ahly","Copenhagen","Palermo","Toulouse"):
        m["ht_gol"], m["ht_pct"] = "alta", "60–65%"
    else:
        m["ht_gol"], m["ht_pct"] = "media", "52–58%"

MATCHES_04 = [
    dict(hora="13:00", pais="Francia", sexo="M", liga="Ligue 1",
         local="Lyon", visita="Auxerre", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–4", rem="6–8 · 20–24", sot="2 · 7–10",
         ir="1X Lyon · +0.5 1T · +1.5", no="Auxerre ML · bank",
         extra="Auxerre 0-0-2. Lyon casa. Gol 1T viable"),
    dict(hora="13:00", pais="Noruega", sexo="M", liga="Eliteserien",
         local="Fredrikstad", visita="Bodø/Glimt", tens="Baja",
         goles="3", ht="1–2", corn="9–12", tarj="3–4", rem="6–8 · 20–24", sot="2 · 7–10",
         ir="X2 Glimt · +1.5 · +0.5 1T", no="Fredrikstad ML",
         extra="Glimt golea visita. Desbalance"),
    dict(hora="13:00", pais="Noruega", sexo="M", liga="Eliteserien",
         local="Aalesund", visita="Start", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5", no="Bank"),
    dict(hora="13:00", pais="Dinamarca", sexo="M", liga="Superliga",
         local="Viborg", visita="Lyngby", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5", no="Bank"),
    dict(hora="13:00", pais="Inglaterra", sexo="F", liga="WSL",
         local="London City Lionesses", visita="Man Utd F", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="2–4", rem="4–6 · 16–20", sot="1–2 · 6–9",
         ir="X2 United F · +0.5 1T · +1.5", no="Lionesses ML",
         extra="United F favorito claro. Gol 1T viable"),
    dict(hora="13:30", pais="Inglaterra", sexo="F", liga="WSL 2",
         local="Watford F", visita="Burnley F", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="2–4", rem="5–7 · 14–18", sot="2 · 5–8",
         ir="+1.5 · ficha", no="Bank"),
    dict(hora="13:35", pais="Escocia", sexo="F", liga="SWPL",
         local="Hibernian F", visita="Glasgow City", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5 · X2 City", no="Bank"),
    dict(hora="13:45", pais="Italia", sexo="M", liga="Serie A",
         local="Genoa", visita="Como", tens="Media",
         goles="2", ht="0–1", corn="8–11", tarj="4–5", rem="5–7 · 16–20", sot="2 · 5–8",
         ir="+1.5 · −3.5", no="1 seco"),
    dict(hora="13:45", pais="Bélgica", sexo="M", liga="Pro League",
         local="Lommel", visita="Club Brugge", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–4", rem="4–6 · 18–22", sot="1–2 · 7–10",
         ir="X2 Brugge · +1.5 · +0.5 1T", no="Lommel ML",
         extra="Brugge grande vs local de abajo"),
    dict(hora="14:00", pais="Inglaterra", sexo="M", liga="Premier League",
         local="Ipswich", visita="Liverpool", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="3–4", rem="5–7 · 18–22", sot="2 · 7–10",
         ir="X2 Liverpool · +1.5", no="Tratarlo como 7-0 · bank",
         extra="Línea ~3.5. No es Sikkim"),
    dict(hora="14:00", pais="España", sexo="M", liga="La Liga",
         local="Betis", visita="Real Madrid", tens="Media+",
         goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="5–7 · 18–22", sot="2 · 7–10",
         ir="X2 Madrid · +1.5", no="Betis ML · Over 4.5",
         extra="Madrid 3-0-0. Betis no es colero"),
    dict(hora="14:00", pais="Países Bajos", sexo="M", liga="Eredivisie",
         local="Sparta Rotterdam", visita="PEC Zwolle", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5", no="Bank"),
    dict(hora="14:00", pais="Noruega", sexo="M", liga="Eliteserien",
         local="Sandefjord", visita="Viking", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5", no="Bank"),
    dict(hora="14:05", pais="Francia", sexo="M", liga="Ligue 1",
         local="PSG", visita="Monaco", tens="Media+",
         goles="2–4", ht="1", corn="9–12", tarj="3–5", rem="6–8 · 16–20", sot="2 · 6–9",
         ir="+1.5 · 1X PSG", no="Monaco ML seco"),
    dict(hora="14:15", pais="Portugal", sexo="M", liga="Primeira Liga",
         local="Porto", visita="Moreirense", tens="Baja",
         goles="2–4", ht="1–2", corn="9–12", tarj="3–4", rem="6–8 · 20–24", sot="2 · 8–11",
         ir="1 Porto · +0.5 1T · +1.5", no="Moreirense ML · Under 1.5",
         extra="★ GOLEADA: Porto 4-0-0 · 9-0. Último 0-3 Viseu YA EN 1T"),
    dict(hora="14:30", pais="Alemania", sexo="M", liga="Bundesliga",
         local="Stuttgart", visita="Köln", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="5–7 · 18–22", sot="2 · 6–9",
         ir="+1.5", no="Bank"),
    dict(hora="19:30", pais="USA", sexo="M", liga="MLS",
         local="NYCFC", visita="Nashville", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5 · X2 Nashville", no="Bank",
         extra="Nashville 16-4-2 más sólido"),
    dict(hora="21:30", pais="USA", sexo="F", liga="NWSL",
         local="Utah Royals", visita="Boston Legacy", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5", no="Bank"),
    dict(hora="22:00", pais="USA", sexo="F", liga="NWSL",
         local="Bay FC", visita="Kansas City Current", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="+1.5 · X2 Current", no="Bank"),
    dict(hora="23:00", pais="México", sexo="M", liga="Liga MX",
         local="Juárez", visita="Pachuca", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 16–20", sot="2 · 6–9",
         ir="X2 Pachuca · +1.5 · +0.5 1T", no="Juárez ML",
         extra="★ Juárez 0-0-6. Pachuca debe empujar temprano"),
]

NEED04 = {
    "Lyon": "Auxerre sin puntos (0-0-2). Lyon necesita ganar en casa.",
    "Fredrikstad": "Glimt pelea título y golea fuera. Fredrikstad a aguantar.",
    "Aalesund": "Puntos de media. Sin final.",
    "Viborg": "Mitad de tabla. Sin urgencia máxima.",
    "London City Lionesses": "United F favorito. Lionesses no se juegan el año en la 1ª.",
    "Watford F": "WSL2. Suma, no copa.",
    "Hibernian F": "Glasgow City suele exigir. Local necesita no caer.",
    "Genoa": "Genoa 0-0-2 urgido. Como viene mejor.",
    "Lommel": "Brugge debe ganar. Lommel abajo.",
    "Ipswich": "Liverpool necesita despegar (0-2-0). Ipswich local.",
    "Betis": "Madrid 3-0-0 no puede pinchar. Betis pelea Europa.",
    "Sparta Rotterdam": "Puntos. Sin clásico.",
    "Sandefjord": "Viking más arriba. Local suma.",
    "PSG": "PSG 0-2-0 NECESITA ganar. Monaco 2-0-0 también.",
    "Porto": "Porto 4-0-0 · 9-0. Moreirense 11º. Desbalance máximo del día.",
    "Stuttgart": "Ambos arrancan Bundesliga. Puntos.",
    "NYCFC": "Nashville sólido (16-4-2). NYCFC a no perder casa.",
    "Utah Royals": "NWSL. Royals más arriba que Boston.",
    "Bay FC": "Current más arriba. Bay en casa.",
    "Juárez": "Juárez 0-0-6 desesperado. Pachuca a sumar fuera.",
}

HT04_ALTA = {"Lyon", "Fredrikstad", "London City Lionesses", "Lommel", "Porto", "Juárez"}

for m in MATCHES_04:
    m["dia"] = "04/09"
    m["need"] = NEED04.get(m["local"], "Sin urgencia extrema.")
    m["logo_l"] = logo_for(m["local"])
    m["logo_v"] = logo_for(m["visita"])
    m["res"] = "X"
    m["dc"] = "1X"
    m["res_txt"] = "Ficha. Una pata"
    m["gana"] = "Abierto / 1X local"
    if m["local"] in HT04_ALTA:
        m["ht_gol"], m["ht_pct"] = "alta", "60–68%"
    elif m["local"] in ("Ipswich", "Betis", "PSG"):
        m["ht_gol"], m["ht_pct"] = "media", "52–58%"
    else:
        m["ht_gol"], m["ht_pct"] = "media", "50–58%"

MATCHES_05 = [
    dict(hora="08:00", pais="Italia", sexo="M", liga="Serie A",
         local="Fiorentina", visita="Torino", tens="Baja",
         goles="1–2", ht="0–1", corn="8–10", tarj="4–5", rem="5–7 · 12–16", sot="2 · 4–6",
         ir="−2.5 · Under 2.5", no="+3.5 · bank",
         extra="CERRADO. Torino 0-0-2. Fiorentina no abre fácil"),
    dict(hora="08:15", pais="España", sexo="M", liga="La Liga",
         local="Athletic", visita="Atlético Madrid", tens="Media+",
         goles="1–2", ht="0–1", corn="8–11", tarj="4–6", rem="5–7 · 12–16", sot="2 · 4–6",
         ir="−2.5 · X2 Atlético ficha", no="+3.5 · 1 Athletic seco",
         extra="CERRADO. Derbi táctico. Under más sólido que Over"),
    dict(hora="09:00", pais="Inglaterra", sexo="M", liga="Premier League",
         local="Fulham", visita="Crystal Palace", tens="Baja",
         goles="1–2", ht="0–1", corn="8–10", tarj="3–5", rem="5–7 · 10–14", sot="2 · 3–5",
         ir="−2.5 · Under 2.5", no="+3.5",
         extra="CERRADO. Los dos 0-0-2. Arranque seco"),
    dict(hora="07:30", pais="Alemania", sexo="M", liga="Bundesliga",
         local="Paderborn", visita="Freiburg", tens="Baja",
         goles="1–2", ht="0–1", corn="8–11", tarj="3–5", rem="5–7 · 12–16", sot="2 · 4–6",
         ir="−2.5 · línea 2.5", no="+3.5",
         extra="CERRADO. Línea casas 2.5"),
    dict(hora="07:30", pais="Alemania", sexo="M", liga="Bundesliga",
         local="Gladbach", visita="Elversberg", tens="Baja",
         goles="2", ht="1", corn="8–11", tarj="3–4", rem="5–7 · 14–18", sot="2 · 5–7",
         ir="−2.5 ficha · +1.5", no="Over 3.5",
         extra="Más abierto que Paderborn. Under no tan fijo"),
    dict(hora="11:00", pais="Italia", sexo="M", liga="Serie A",
         local="Inter", visita="Napoli", tens="Media+",
         goles="2", ht="0–1", corn="8–11", tarj="4–5", rem="5–7 · 14–18", sot="2 · 5–7",
         ir="−2.5 · +1.5", no="Over 3.5 · bank 1",
         extra="Grande vs grande. Puede 1-0 / 1-1"),
    dict(hora="06:30", pais="Inglaterra", sexo="M", liga="Premier League",
         local="Newcastle", visita="Bournemouth", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="6–8 · 14–18", sot="2 · 5–8",
         ir="+1.5 · 1X Newcastle", no="Under 1.5"),
    dict(hora="09:00", pais="Inglaterra", sexo="M", liga="Premier League",
         local="Brentford", visita="Sunderland", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="5–7 · 14–18", sot="2 · 5–7",
         ir="+1.5", no="Bank"),
    dict(hora="09:00", pais="Inglaterra", sexo="M", liga="Premier League",
         local="Brighton", visita="Leeds", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="6–8 · 14–18", sot="2 · 5–8",
         ir="+1.5", no="Under 1.5"),
    dict(hora="09:00", pais="Inglaterra", sexo="M", liga="Premier League",
         local="Nottm Forest", visita="Tottenham", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 14–18", sot="2 · 5–8",
         ir="+1.5 · X2 Spurs ficha", no="Forest 1 seco"),
    dict(hora="09:00", pais="Inglaterra", sexo="M", liga="Premier League",
         local="Man City", visita="Coventry", tens="Baja",
         goles="3–4", ht="1–2", corn="10–13", tarj="2–4", rem="8–12 · 20–26", sot="3 · 8–12",
         ir="City −1.5 · +2.5 · +0.5 1T", no="Under 2.5 · Coventry ML",
         extra="ABIERTO. No es Under. City 2-0-0"),
    dict(hora="11:30", pais="Inglaterra", sexo="M", liga="Premier League",
         local="Hull", visita="Aston Villa", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="5–7 · 14–18", sot="2 · 5–7",
         ir="X2 Villa · +1.5", no="Hull 1 seco"),
    dict(hora="07:30", pais="Alemania", sexo="M", liga="Bundesliga",
         local="Leverkusen", visita="Union Berlin", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="6–8 · 18–22", sot="2 · 6–9",
         ir="1X Leverkusen · +1.5", no="Union ML"),
    dict(hora="07:30", pais="Alemania", sexo="M", liga="Bundesliga",
         local="Hoffenheim", visita="Dortmund", tens="Media",
         goles="2–4", ht="1", corn="9–12", tarj="3–5", rem="6–8 · 16–20", sot="2 · 6–9",
         ir="+2.5 · X2 Dortmund", no="Under 1.5",
         extra="ABIERTO. Línea 3.5"),
    dict(hora="07:30", pais="Alemania", sexo="M", liga="Bundesliga",
         local="Bremen", visita="Leipzig", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="6–8 · 16–20", sot="2 · 6–9",
         ir="X2 Leipzig · +1.5", no="Bremen ML"),
    dict(hora="10:30", pais="Alemania", sexo="M", liga="Bundesliga",
         local="Schalke", visita="Bayern", tens="Baja",
         goles="3–5", ht="1–2", corn="9–13", tarj="3–4", rem="4–6 · 20–26", sot="1–2 · 8–12",
         ir="Bayern −1.5 · +2.5 · +0.5 1T", no="Under 2.5",
         extra="ABIERTO. Línea 4.5. No Under"),
    dict(hora="13:45", pais="Italia", sexo="M", liga="Serie A",
         local="Roma", visita="Atalanta", tens="Media+",
         goles="2–3", ht="1", corn="8–11", tarj="4–6", rem="5–7 · 16–20", sot="2 · 5–8",
         ir="+1.5 · −3.5", no="Over 3.5"),
    dict(hora="10:00", pais="España", sexo="M", liga="La Liga",
         local="Rayo", visita="Racing Santander", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="5–7 · 14–18", sot="2 · 5–7",
         ir="+1.5", no="Bank"),
    dict(hora="14:00", pais="España", sexo="M", liga="La Liga",
         local="Villarreal", visita="Deportivo", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–4", rem="6–8 · 18–22", sot="2 · 6–9",
         ir="1X Villarreal · +1.5", no="Depor ML"),
    dict(hora="06:30", pais="Inglaterra", sexo="F", liga="WSL",
         local="Chelsea F", visita="Aston Villa F", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="2–4", rem="6–8 · 16–20", sot="2 · 6–9",
         ir="1 Chelsea F · +1.5 · +0.5 1T", no="Villa F ML"),
]

NEED05 = {
    "Fiorentina": "Puntos. Torino sin ganar (0-0-2). Nadie se juega el año.",
    "Athletic": "Atlético pelea arriba. Athletic casa. Táctico.",
    "Fulham": "Los dos 0 puntos. Miedo a perder.",
    "Paderborn": "Freiburg más sólido. Local recién ascendido a no abrir.",
    "Gladbach": "Gladbach debe ganar en casa. Elversberg visita.",
    "Inter": "Inter 2-0-0 vs Napoli. Choque de candidatos.",
    "Newcastle": "Newcastle casa. Bournemouth irregular.",
    "Brentford": "Sunderland recién subido. Brentford casa.",
    "Brighton": "Los dos quieren atacar. No cerrado.",
    "Nottm Forest": "Spurs 0-0-2 urgidos. Forest también.",
    "Man City": "City 2-0-0 debe golear. Coventry 0-0-2.",
    "Hull": "Villa favorito. Hull local sorprendente 2-0-0.",
    "Leverkusen": "Leverkusen debe sumar 3. Union a aguantar.",
    "Hoffenheim": "Dortmund visita. Partido de goles.",
    "Bremen": "Leipzig favorito. Bremen casa.",
    "Schalke": "Bayern no puede pinchar. Schalke abajo.",
    "Roma": "Roma 2-0-0 vs Atalanta 2-0-0. Choque.",
    "Rayo": "Puntos mitad.",
    "Villarreal": "Villarreal favorito vs Depor.",
    "Chelsea F": "Chelsea F favorito claro vs Villa F.",
}
CERRADOS05 = {"Fiorentina", "Athletic", "Fulham", "Paderborn"}
HT05 = {"Man City", "Schalke", "Chelsea F", "Hoffenheim"}

for m in MATCHES_05:
    m["dia"] = "05/09"
    m["need"] = NEED05.get(m["local"], "Sin urgencia extrema.")
    m["logo_l"] = logo_for(m["local"])
    m["logo_v"] = logo_for(m["visita"])
    m["res"] = "X"
    m["dc"] = "1X"
    m["res_txt"] = "Ficha"
    m["gana"] = "Abierto / 1X"
    if m["local"] in CERRADOS05:
        m["ht_gol"], m["ht_pct"] = "baja", "38–45%"
        m["cerrado"] = "1"
    elif m["local"] in HT05:
        m["ht_gol"], m["ht_pct"] = "alta", "60–68%"
        m["cerrado"] = "0"
    else:
        m["ht_gol"], m["ht_pct"] = "media", "50–58%"
        m["cerrado"] = "0"

MATCHES_06 = [
    dict(hora="10:00", pais="Inglaterra", sexo="M", liga="Premier League",
         local="Everton", visita="Man United", tens="Media+",
         goles="2–3", ht="1", corn="9–12", tarj="4–6", rem="11–14 · 12–15", sot="4–5 · 4–5",
         ir="+1.5 · −3.5", no="Under 1.5 · bank 1",
         extra="No es el Under más fijo. Clasico relativo"),
    dict(hora="12:30", pais="Inglaterra", sexo="M", liga="Premier League",
         local="Arsenal", visita="Chelsea", tens="ALTA",
         goles="2–3", ht="1", corn="9–12", tarj="4–6", rem="14–18 · 10–13", sot="5–7 · 3–5",
         ir="+1.5 · −3.5 · +4.5 tarjetas", no="Under 1.5 · −5.5 tarjetas",
         extra="London derby. Goles sí, no candado"),
    dict(hora="10:15", pais="España", sexo="M", liga="La Liga",
         local="Valencia", visita="Barcelona", tens="Baja",
         goles="3–4", ht="1–2", corn="9–13", tarj="3–5", rem="8–11 · 16–22", sot="3 · 6–9",
         ir="Barça −1.5 · +2.5", no="Under 2.5 · Valencia ML",
         extra="ABIERTO. No Under"),
    dict(hora="12:30", pais="España", sexo="M", liga="La Liga",
         local="Alavés", visita="Osasuna", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–6", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Under 1.5",
         extra="No tan cerrado. Se puede ir a 3"),
    dict(hora="12:30", pais="España", sexo="M", liga="La Liga",
         local="Málaga", visita="Levante", tens="Baja",
         goles="1–2", ht="0–1", corn="8–10", tarj="4–5", rem="10–13 · 10–13", sot="3–4 · 3–4",
         ir="−2.5 · Under 2.5", no="+3.5 · bank",
         extra="CERRADO. Dos recién / abajo. El Under más fijo del 06/09"),
    dict(hora="16:00", pais="España", sexo="M", liga="La Liga",
         local="Espanyol", visita="Sevilla", tens="Media",
         goles="2", ht="0–1", corn="8–11", tarj="4–6", rem="11–14 · 11–14", sot="3–5 · 3–5",
         ir="−2.5 ficha · +1.5", no="Over 3.5",
         extra="Mitad cerrado. 1-1 / 1-0"),
    dict(hora="10:00", pais="Italia", sexo="M", liga="Serie A",
         local="Frosinone", visita="Venezia", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="12–15 · 10–13", sot="4–5 · 3–4",
         ir="+1.5 · −3.5", no="Under 1.5",
         extra="Frosinone pega. No es el Under más seco"),
    dict(hora="10:00", pais="Italia", sexo="M", liga="Serie A",
         local="Parma", visita="Monza", tens="Baja",
         goles="1–2", ht="0–1", corn="8–10", tarj="4–5", rem="10–13 · 10–13", sot="3–4 · 3–4",
         ir="−2.5 · Under 2.5", no="+3.5",
         extra="CERRADO. Los dos 0 pts. Miedo"),
    dict(hora="13:00", pais="Italia", sexo="M", liga="Serie A",
         local="Bologna", visita="Sassuolo", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="12–15 · 11–14", sot="4–5 · 4",
         ir="+1.5 · −3.5", no="Under 1.5"),
    dict(hora="15:45", pais="Italia", sexo="M", liga="Serie A",
         local="Juventus", visita="AC Milan", tens="ALTA",
         goles="1–2", ht="0–1", corn="8–11", tarj="4–6", rem="12–15 · 11–14", sot="4–5 · 4",
         ir="−2.5 · Under 2.5 · +4.5 tarjetas", no="+3.5 · −5.5 tarjetas",
         extra="CERRADO relativo. Clásico. 1-0 / 1-1"),
    dict(hora="08:30", pais="Alemania", sexo="M", liga="Bundesliga",
         local="Hamburgo", visita="Mainz", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="11–14 · 12–15", sot="4 · 4–5",
         ir="+1.5 · −3.5", no="Under 1.5",
         extra="Hamburgo 0 goles temporada. Mainz puede abrir"),
    dict(hora="10:30", pais="Alemania", sexo="M", liga="Bundesliga",
         local="Eintracht Frankfurt", visita="Augsburg", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="13–16 · 10–13", sot="5 · 3–4",
         ir="+1.5", no="Under 1.5"),
]

NEED06 = {
    "Everton": "Everton casa vs United irregular. Puntos.",
    "Arsenal": "Derbi Londres. Arsenal 100%. Chelsea responde.",
    "Valencia": "Barça 4-0-0 debe ganar. Valencia 0 pts.",
    "Alavés": "Alavés bien. Osasuna a sumar.",
    "Málaga": "Los dos abajo. Miedo a perder. Under.",
    "Espanyol": "Mitad de tabla. No urgencia extrema.",
    "Frosinone": "Frosinone 2-0. Venezia 0 pts.",
    "Parma": "Parma y Monza sin ganar. Candado.",
    "Bologna": "Bologna 0 pts. Sassuolo mixto.",
    "Juventus": "Clásico. Nadie se tira 4-3.",
    "Hamburgo": "Hamburgo 0-0-2 y 0 goles. Mainz a sumar.",
    "Eintracht Frankfurt": "Frankfurt casa. Augsburg visita.",
}
CERRADOS06 = {"Málaga", "Parma", "Juventus"}
HT06 = {"Valencia", "Arsenal", "Frosinone"}

for m in MATCHES_06:
    m["dia"] = "06/09"
    m["need"] = NEED06.get(m["local"], "Sin urgencia extrema.")
    m["logo_l"] = logo_for(m["local"])
    m["logo_v"] = logo_for(m["visita"])
    m["res"] = "X"
    m["dc"] = "1X"
    m["res_txt"] = "Ficha"
    m["gana"] = "Abierto / 1X"
    if m["local"] in CERRADOS06:
        m["ht_gol"], m["ht_pct"] = "baja", "38–45%"
        m["cerrado"] = "1"
    elif m["local"] in HT06:
        m["ht_gol"], m["ht_pct"] = "alta", "60–68%"
        m["cerrado"] = "0"
    else:
        m["ht_gol"], m["ht_pct"] = "media", "50–58%"
        m["cerrado"] = "0"

CERRADOS += [
    dict(partido="Everton vs Man United", pick="+1.5 · −3.5",
         ft="2-2", extra="+1.5 sí · −3.5 sí · gol 90+6", estado="VERDE"),
    dict(partido="Arsenal vs Chelsea", pick="+1.5 · −3.5 · +4.5 tarjetas",
         ft="2-1", extra="+1.5 sí · −3.5 sí", estado="VERDE"),
    dict(partido="Valencia vs Barcelona", pick="Barça −1.5 · +2.5",
         ft="0-5", extra="−1.5 sí · +2.5 sí · Yamal 2", estado="VERDE"),
    dict(partido="Alavés vs Osasuna", pick="+1.5 · −3.5",
         ft="5-2", extra="+1.5 sí · −3.5 no · 7 goles", estado="ROJO"),
    dict(partido="Málaga vs Levante", pick="−2.5 · Under 2.5",
         ft="0-0", extra="0-0 · Under sí · el más cerrado", estado="VERDE"),
    dict(partido="Espanyol vs Sevilla", pick="−2.5 ficha · +1.5",
         ft="1-1", extra="+1.5 sí · −2.5 sí", estado="VERDE"),
    dict(partido="Frosinone vs Venezia", pick="+1.5 · −3.5",
         ft="3-2", extra="+1.5 sí · −3.5 no", estado="ROJO"),
    dict(partido="Parma vs Monza", pick="−2.5 · Under 2.5",
         ft="1-1", extra="2 goles · Under sí", estado="VERDE"),
    dict(partido="Bologna vs Sassuolo", pick="+1.5 · −3.5",
         ft="2-2", extra="+1.5 sí · −3.5 sí", estado="VERDE"),
    dict(partido="Juventus vs AC Milan", pick="−2.5 · Under 2.5",
         ft="1-1", extra="2 goles · Under sí · clásico", estado="VERDE"),
    dict(partido="Hamburgo vs Mainz", pick="+1.5 · −3.5",
         ft="0-5", extra="+1.5 sí · −3.5 no", estado="ROJO"),
    dict(partido="Eintracht Frankfurt vs Augsburg", pick="+1.5",
         ft="1-4", extra="+1.5 sí", estado="VERDE"),
]

# === 07/09 RESULTADOS ===
CERRADOS += [
    dict(partido="Cagliari vs Lecce", pick="−2.5 · Under 2.5 · 1X Cagliari",
         ft="1-0", extra="Under sí · 1X sí · cerrado", estado="VERDE"),
    dict(partido="Udinese vs Lazio", pick="X2 Lazio · +1.5 · −3.5",
         ft="1-2", extra="X2 sí · +1.5 sí · −3.5 sí", estado="VERDE"),
    dict(partido="Getafe vs Celta Vigo", pick="−2.5 · Under 2.5 · +4.5 tarjetas",
         ft="1-1", extra="Under sí · cerrado Bordalás", estado="VERDE"),
    dict(partido="Elche vs Real Sociedad", pick="X2 Sociedad · +1.5 · −3.5",
         ft="2-3", extra="X2 sí · +1.5 sí · 5 goles −3.5 no", estado="ROJO"),
    dict(partido="Bromley vs AFC Wimbledon", pick="+1.5 · −3.5",
         ft="0-2", extra="+1.5 sí · −3.5 sí", estado="VERDE"),
    dict(partido="Al Khaleej vs Al Riyadh", pick="+1.5 · −3.5",
         ft="0-0", extra="+1.5 no · −3.5 sí", estado="ROJO"),
    dict(partido="Al Hilal vs NEOM", pick="Hilal −1.5 · +2.5 · +0.5 1T",
         ft="0-2", extra="Hilal −1.5 no · +2.5 sí · sorpresa NEOM", estado="ROJO"),
    dict(partido="Estoril vs Arouca", pick="X2 Arouca · +1.5",
         ft="0-0", extra="X2 sí (empate) · +1.5 no", estado="ROJO"),
    dict(partido="Rizespor vs Alanyaspor", pick="+1.5 · −3.5",
         ft="0-1", extra="+1.5 no · −3.5 sí", estado="ROJO"),
    dict(partido="Göztepe vs Gaziantep", pick="+1.5",
         ft="2-4", extra="+1.5 sí · 6 goles", estado="VERDE"),
    dict(partido="Sabadell vs Córdoba", pick="+1.5 · −3.5",
         ft="3-2", extra="+1.5 sí · −3.5 no", estado="ROJO"),
    dict(partido="Palermo vs Sampdoria", pick="+1.5 · +4.5 tarjetas",
         ft="3-1", extra="+1.5 sí", estado="VERDE"),
    dict(partido="Nantes vs Nancy", pick="1X Nantes · +1.5",
         ft="1-0", extra="1X sí · +1.5 no", estado="ROJO"),
    dict(partido="Asteras vs Iraklis", pick="+1.5 · −3.5",
         ft="0-2", extra="+1.5 sí · −3.5 sí", estado="VERDE"),
    dict(partido="Granada F vs Real Sociedad F", pick="X2 Sociedad F · +1.5",
         ft="3-2", extra="X2 no · +1.5 sí", estado="ROJO"),
    dict(partido="Barracas vs Argentinos", pick="−2.5 · +4.5 tarjetas",
         ft="0-0", extra="Under sí · cerrado", estado="VERDE"),
    dict(partido="Vitória vs Grêmio", pick="X2 Grêmio · +1.5",
         ft="1-0", extra="X2 no · +1.5 no · 1X Vitória sí", estado="ROJO"),
    dict(partido="Llaneros vs Tolima", pick="X2 Tolima · −2.5",
         ft="1-2", extra="X2 sí · −2.5 no", estado="ROJO"),
    dict(partido="Nueva Chicago vs Quilmes", pick="−2.5 · +4.5 tarjetas",
         ft="1-0", extra="Under sí", estado="VERDE"),
    dict(partido="Orlando Pride vs Houston Dash", pick="+2.5 · 1X Pride",
         ft="3-1", extra="+2.5 sí · 1X sí", estado="VERDE"),
    dict(partido="Seattle Reign vs San Diego Wave", pick="+1.5 · BTTS ficha",
         ft="1-0", extra="+1.5 no", estado="ROJO"),
    dict(partido="Pafos vs Olympiakos Nicosia", pick="+1.5 · −3.5",
         ft="0-0", extra="+1.5 no · Under sí", estado="ROJO"),
    dict(partido="Unión SF vs Instituto", pick="−2.5 · +4.5 tarjetas",
         ft="3-2", extra="5 goles · −2.5 no", estado="ROJO"),
    dict(partido="Excursionistas vs Ituzaingó", pick="+1.5 · −3.5",
         ft="2-1", extra="+1.5 sí · −3.5 sí", estado="VERDE"),
    dict(partido="Emelec vs Manta", pick="1X Emelec · +1.5",
         ft="1-0", extra="1X sí · +1.5 no", estado="ROJO"),
    dict(partido="Rubin Kazan vs Akhmat", pick="−2.5 · +4.5 tarjetas",
         ft="1-1", extra="Under sí", estado="VERDE"),
]

MATCHES_07 = [
    dict(hora="11:30", pais="Italia", sexo="M", liga="Serie A",
         local="Cagliari", visita="Lecce", tens="Baja",
         goles="1–2", ht="0–1", corn="8–10", tarj="4–5", rem="11–14 · 10–13", sot="3–4 · 3–4",
         ir="−2.5 · Under 2.5 · 1X Cagliari", no="+3.5 · bank",
         extra="CERRADO. Los dos 1-0-1. Miedo a perder"),
    dict(hora="13:45", pais="Italia", sexo="M", liga="Serie A",
         local="Udinese", visita="Lazio", tens="Media",
         goles="2", ht="0–1", corn="8–11", tarj="4–5", rem="10–13 · 13–16", sot="3–4 · 4–5",
         ir="X2 Lazio · +1.5 · −3.5", no="Udinese 1 seco · Over 3.5",
         extra="Lazio 2-0-0. Udinese casa sólida"),
    dict(hora="12:00", pais="España", sexo="M", liga="La Liga",
         local="Getafe", visita="Celta Vigo", tens="Media",
         goles="1–2", ht="0–1", corn="8–10", tarj="4–6", rem="10–13 · 11–14", sot="3–4 · 3–4",
         ir="−2.5 · Under 2.5 · +4.5 tarjetas", no="+3.5 · −5.5 tarjetas",
         extra="CERRADO. Getafe Bordalás. Celta 0-2-2"),
    dict(hora="14:30", pais="España", sexo="M", liga="La Liga",
         local="Elche", visita="Real Sociedad", tens="Baja",
         goles="2", ht="0–1", corn="8–11", tarj="4–5", rem="10–13 · 12–15", sot="3–4 · 4–5",
         ir="X2 Sociedad · +1.5 · −3.5", no="Elche 1 seco",
         extra="Elche 0-1-2. Sociedad irregular"),
    dict(hora="14:00", pais="Inglaterra", sexo="M", liga="League One",
         local="Bromley", visita="AFC Wimbledon", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="12–15 · 11–14", sot="4–5 · 4",
         ir="+1.5 · −3.5", no="Under 1.5 · bank",
         extra="Tercera. Ficha chica"),
    dict(hora="12:00", pais="Dinamarca", sexo="M", liga="Superliga",
         local="Midtjylland", visita="Nordsjælland", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="14–17 · 10–13", sot="5–6 · 3–4",
         ir="1X Midtjylland · +1.5", no="Under 1.5"),
    dict(hora="10:30", pais="Arabia Saudita", sexo="M", liga="Pro League",
         local="Al Khaleej", visita="Al Riyadh", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank"),
    dict(hora="13:00", pais="Arabia Saudita", sexo="M", liga="Pro League",
         local="Al Hilal", visita="NEOM", tens="Baja",
         goles="3–4", ht="1–2", corn="10–13", tarj="3–4", rem="16–20 · 8–11", sot="6–8 · 3",
         ir="Hilal −1.5 · +2.5 · +0.5 1T", no="Under 2.5 · NEOM ML",
         extra="ABIERTO. Hilal 5-0-0"),
    dict(hora="14:15", pais="Portugal", sexo="M", liga="Primeira Liga",
         local="Estoril", visita="Arouca", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="11–14 · 12–15", sot="4 · 4–5",
         ir="X2 Arouca · +1.5", no="Estoril 1 seco",
         extra="Estoril 0-1-3. Arouca 3-0-1"),
    dict(hora="12:00", pais="Suecia", sexo="M", liga="Allsvenskan",
         local="Malmö", visita="AIK", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="14–17 · 9–12", sot="5–6 · 3–4",
         ir="1X Malmö · +1.5", no="AIK seco"),
    dict(hora="12:00", pais="Suecia", sexo="M", liga="Allsvenskan",
         local="Kalmar", visita="Djurgården", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="10–13 · 13–16", sot="3–4 · 4–5",
         ir="X2 Djurgården · +1.5", no="Kalmar 1 seco"),
    dict(hora="12:00", pais="Suecia", sexo="M", liga="Allsvenskan",
         local="Mjällby", visita="IFK Göteborg", tens="Baja",
         goles="2", ht="0–1", corn="8–11", tarj="3–5", rem="12–15 · 10–13", sot="4 · 3–4",
         ir="+1.5 · −3.5", no="Over 3.5"),
    dict(hora="12:00", pais="Turquía", sexo="M", liga="Süper Lig",
         local="Rizespor", visita="Alanyaspor", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="12–15 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank"),
    dict(hora="12:00", pais="Turquía", sexo="M", liga="Süper Lig",
         local="Göztepe", visita="Gaziantep", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5", no="Bank"),
    dict(hora="11:30", pais="Rusia", sexo="M", liga="Premier",
         local="Rubin Kazan", visita="Akhmat", tens="Media",
         goles="2", ht="0–1", corn="8–10", tarj="4–6", rem="11–14 · 10–13", sot="3–4 · 3–4",
         ir="−2.5 · +4.5 tarjetas", no="+3.5"),
    dict(hora="13:30", pais="España", sexo="M", liga="LaLiga 2",
         local="Sabadell", visita="Córdoba", tens="Baja",
         goles="2", ht="0–1", corn="8–11", tarj="4–5", rem="11–14 · 11–14", sot="3–4 · 3–4",
         ir="+1.5 · −3.5", no="Bank"),
    dict(hora="13:30", pais="Italia", sexo="M", liga="Serie B",
         local="Palermo", visita="Sampdoria", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="4–6", rem="12–15 · 11–14", sot="4 · 4",
         ir="+1.5 · +4.5 tarjetas", no="Under 1.5"),
    dict(hora="13:45", pais="Francia", sexo="M", liga="Ligue 2",
         local="Nantes", visita="Nancy", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="13–16 · 9–12", sot="4–5 · 3",
         ir="1X Nantes · +1.5", no="Nancy ML"),
    dict(hora="10:00", pais="Grecia", sexo="M", liga="Super League",
         local="Asteras", visita="Iraklis", tens="Baja",
         goles="2", ht="0–1", corn="8–10", tarj="4–5", rem="12–15 · 9–12", sot="4 · 3",
         ir="+1.5 · −3.5", no="Bank"),
    dict(hora="12:30", pais="España", sexo="F", liga="Liga F",
         local="Granada F", visita="Real Sociedad F", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="9–12 · 13–16", sot="3 · 5",
         ir="X2 Sociedad F · +1.5", no="Granada F ML"),
    dict(hora="12:00", pais="Alemania", sexo="F", liga="Frauen-Bundesliga",
         local="Union Berlin F", visita="Eintracht F", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="9–12 · 14–17", sot="3 · 5–6",
         ir="X2 Eintracht F · +1.5 · +0.5 1T", no="Union F ML"),
    dict(hora="17:00", pais="Argentina", sexo="M", liga="Liga Profesional",
         local="Barracas", visita="Argentinos", tens="Media",
         goles="1–2", ht="0–1", corn="8–10", tarj="4–6", rem="10–13 · 11–14", sot="3–4 · 3–4",
         ir="−2.5 · +4.5 tarjetas", no="+3.5 · −5.5 tarjetas",
         extra="CERRADO relativo. Argentinos visita"),
    dict(hora="19:15", pais="Argentina", sexo="M", liga="Liga Profesional",
         local="Unión SF", visita="Instituto", tens="Media",
         goles="2", ht="0–1", corn="8–11", tarj="4–6", rem="11–14 · 10–13", sot="3–4 · 3–4",
         ir="−2.5 · +4.5 tarjetas", no="+3.5"),
    dict(hora="19:00", pais="Brasil", sexo="M", liga="Serie A",
         local="Vitória", visita="Grêmio", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="4–6", rem="11–14 · 12–15", sot="4 · 4–5",
         ir="X2 Grêmio · +1.5", no="Vitória 1 seco"),
    dict(hora="19:00", pais="Chile", sexo="M", liga="Liga de Primera",
         local="Limache", visita="Cobresal", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank"),
    dict(hora="19:00", pais="Colombia", sexo="M", liga="BetPlay",
         local="Llaneros", visita="Tolima", tens="Media",
         goles="2", ht="0–1", corn="8–11", tarj="4–6", rem="10–13 · 12–15", sot="3–4 · 4",
         ir="X2 Tolima · −2.5", no="Llaneros 1 seco"),
    dict(hora="15:00", pais="Paraguay", sexo="M", liga="Primera",
         local="Guaraní", visita="Recoleta", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="13–16 · 9–12", sot="4–5 · 3",
         ir="1X Guaraní · +1.5", no="Recoleta ML"),
    dict(hora="17:30", pais="Paraguay", sexo="M", liga="Primera",
         local="Cerro Porteño", visita="Nacional", tens="Media+",
         goles="2–3", ht="1", corn="8–11", tarj="4–6", rem="13–16 · 10–13", sot="4–5 · 3–4",
         ir="1X Cerro · +1.5 · +4.5 tarjetas", no="Nacional ML"),
    dict(hora="20:00", pais="Ecuador", sexo="M", liga="LigaPro",
         local="Emelec", visita="Manta", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="13–16 · 9–12", sot="4–5 · 3",
         ir="1X Emelec · +1.5", no="Manta ML"),
    dict(hora="18:00", pais="Venezuela", sexo="M", liga="Liga FUTVE",
         local="Carabobo", visita="Estudiantes Mérida", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="13–16 · 9–12", sot="4–5 · 3",
         ir="1X Carabobo · +1.5", no="Bank"),
    dict(hora="09:30", pais="Noruega", sexo="F", liga="Toppserien",
         local="LSK Kvinner", visita="Bodø/Glimt F", tens="Baja",
         goles="4–6", ht="2", corn="9–13", tarj="2–4", rem="16–22 · 8–12", sot="6–9 · 3–4",
         ir="+3.5 · +2.5 · LSK −1.5", no="Under 2.5 · bank",
         extra="FIESTA. Glimt F encaja 58 en 14. No Under"),
    dict(hora="15:45", pais="México", sexo="F", liga="Liga MX Femenil",
         local="Atlante F", visita="Juárez F", tens="Baja",
         goles="3–4", ht="1–2", corn="8–12", tarj="3–4", rem="12–16 · 12–16", sot="5–7 · 5–7",
         ir="+2.5 · BTTS ficha", no="Under 1.5 · bank",
         extra="Femenil. Techo 4–5"),
    dict(hora="19:00", pais="México", sexo="F", liga="Liga MX Femenil",
         local="Santos F", visita="Puebla F", tens="Baja",
         goles="3–4", ht="1–2", corn="8–12", tarj="3–4", rem="13–17 · 11–15", sot="5–7 · 4–6",
         ir="+2.5 · +0.5 1T", no="Under 1.5",
         extra="Femenil abierta"),
    dict(hora="00:00", pais="EEUU", sexo="F", liga="NWSL",
         local="Orlando Pride", visita="Houston Dash", tens="Baja",
         goles="3", ht="1", corn="8–11", tarj="3–4", rem="13–16 · 10–13", sot="5–6 · 3–4",
         ir="+2.5 · 1X Pride", no="Under 1.5"),
    dict(hora="02:00", pais="EEUU", sexo="F", liga="NWSL",
         local="Seattle Reign", visita="San Diego Wave", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="12–15 · 12–15", sot="4–5 · 4–5",
         ir="+1.5 · BTTS ficha", no="Bank"),
    dict(hora="16:00", pais="Argentina", sexo="M", liga="Primera Nacional",
         local="Nueva Chicago", visita="Quilmes", tens="Media",
         goles="1–2", ht="0–1", corn="8–10", tarj="4–6", rem="10–13 · 10–13", sot="3–4 · 3–4",
         ir="−2.5 · +4.5 tarjetas", no="+3.5 · bank",
         extra="B Nacional. Cerrado + tarjetas"),
    dict(hora="19:00", pais="Argentina", sexo="M", liga="Primera B",
         local="Excursionistas", visita="Ituzaingó", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank"),
]

NEED07 = {
    "Cagliari": "Los dos 3 pts. Nadie se tira.",
    "Udinese": "Lazio 6 pts. Udinese casa.",
    "Getafe": "Bordalás cierra. Celta irregular.",
    "Elche": "Elche sin ganar. Sociedad a sumar.",
    "Bromley": "League One. Sin necesidad extrema.",
    "Midtjylland": "Midtjylland favorito casa.",
    "Al Khaleej": "Fondo tabla vs fondo.",
    "Al Hilal": "Hilal 5-0-0 debe golear.",
    "Estoril": "Estoril 1 pto. Arouca 9 pts.",
    "Malmö": "Malmö favorito. AIK derbi relativo.",
    "Barracas": "Argentino cerrado típico.",
    "Unión SF": "Puntos mitad.",
    "Vitória": "Grêmio visita a sumar.",
    "Cerro Porteño": "Cerro favorito. Tensión media+",
    "Emelec": "Emelec casa debe ganar.",
}
CERRADOS07 = {"Cagliari", "Getafe", "Barracas", "Nueva Chicago"}
HT07 = {"Al Hilal", "Midtjylland", "Malmö", "Cerro Porteño", "LSK Kvinner", "Atlante F", "Santos F"}
GOL07 = {"LSK Kvinner", "Al Hilal", "Atlante F", "Santos F", "Orlando Pride", "Union Berlin F"}

for m in MATCHES_07:
    m["dia"] = "07/09"
    m["need"] = NEED07.get(m["local"], "Sin urgencia extrema.")
    m["logo_l"] = logo_for(m["local"])
    m["logo_v"] = logo_for(m["visita"])
    m["res"] = "X"
    m["dc"] = "1X"
    m["res_txt"] = "Ficha"
    m["gana"] = "Abierto / 1X"
    m["goles_alta"] = "1" if m["local"] in GOL07 else "0"
    if m["local"] in CERRADOS07:
        m["ht_gol"], m["ht_pct"] = "baja", "38–45%"
        m["cerrado"] = "1"
    elif m["local"] in HT07:
        m["ht_gol"], m["ht_pct"] = "alta", "60–68%"
        m["cerrado"] = "0"
    else:
        m["ht_gol"], m["ht_pct"] = "media", "50–58%"
        m["cerrado"] = "0"

MATCHES_08 = [
    # --- UCL ---
    dict(hora="12:45", pais="Grecia", sexo="M", liga="UCL",
         local="AEK Athens", visita="LASK", tens="Baja",
         goles="2–3", ht="1", corn="9–11", tarj="4–5", rem="12–15 · 10–13", sot="4–5 · 3–4",
         ir="1X AEK · +1.5 · −3.5", no="Under 1.5 · LASK ML",
         extra="UCL. Corners 9–11"),
    dict(hora="12:45", pais="Bélgica", sexo="M", liga="UCL",
         local="Club Brugge", visita="Aston Villa", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="11–14 · 12–15", sot="4 · 4–5",
         ir="+1.5 · −3.5 · X2 Villa ficha", no="Under 1.5",
         extra="Corners 9–12"),
    dict(hora="15:00", pais="Alemania", sexo="M", liga="UCL",
         local="Dortmund", visita="Villarreal", tens="Media",
         goles="2–3", ht="1", corn="10–13", tarj="3–5", rem="14–18 · 9–12", sot="5–7 · 3–4",
         ir="1X Dortmund · +1.5 · +0.5 1T", no="Under 1.5",
         extra="Corners BVB alto 10–13"),
    dict(hora="15:00", pais="Portugal", sexo="M", liga="UCL",
         local="Porto", visita="Man City", tens="Media+",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="10–13 · 14–17", sot="3–4 · 5–6",
         ir="X2 City · +1.5 · −3.5", no="Porto 1 seco",
         extra="Corners 9–12"),
    dict(hora="15:00", pais="Francia", sexo="M", liga="UCL",
         local="Lille", visita="Real Betis", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="12–15 · 11–14", sot="4–5 · 4",
         ir="+1.5 · −3.5 · 1X Lille", no="Under 1.5",
         extra="Corners 9–12"),
    dict(hora="15:00", pais="España", sexo="M", liga="UCL",
         local="Real Madrid", visita="Inter", tens="ALTA",
         goles="2–3", ht="1", corn="9–12", tarj="4–6", rem="13–16 · 11–14", sot="5–6 · 4–5",
         ir="+1.5 · −3.5 · +4.5 tarjetas", no="Under 1.5 · −5.5 tarjetas",
         extra="CLÁSICO. Corners 9–12 · tarjetas 4–6"),
    # --- Championship ---
    dict(hora="14:45", pais="Inglaterra", sexo="M", liga="Championship",
         local="Blackburn", visita="Sheffield United", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="12–15 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Under 1.5",
         extra="Championship. Corners 9–12"),
    dict(hora="14:45", pais="Inglaterra", sexo="M", liga="Championship",
         local="Cardiff", visita="Stoke", tens="Baja",
         goles="2", ht="0–1", corn="9–11", tarj="4–5", rem="11–14 · 11–14", sot="3–4 · 3–4",
         ir="+1.5 · −3.5 · −2.5 ficha", no="Over 3.5",
         extra="Cerrado relativo. Corners 9–11"),
    dict(hora="14:45", pais="Inglaterra", sexo="M", liga="Championship",
         local="Southampton", visita="Swansea", tens="Media",
         goles="2–3", ht="1", corn="10–13", tarj="3–5", rem="14–17 · 10–13", sot="5 · 3–4",
         ir="1X Saints · +1.5", no="Under 1.5",
         extra="Derby Gales-Inglaterra. Corners 10–13"),
    dict(hora="14:45", pais="Inglaterra", sexo="M", liga="Championship",
         local="Watford", visita="Preston", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="12–15 · 10–13", sot="4 · 3–4",
         ir="+1.5 · −3.5", no="Bank",
         extra="Corners 9–12"),
    dict(hora="14:45", pais="Inglaterra", sexo="M", liga="Championship",
         local="Wrexham", visita="Burnley", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="11–14 · 12–15", sot="4 · 4–5",
         ir="+1.5 · X2 Burnley ficha", no="Under 1.5",
         extra="Burnley favorito leve. Corners 9–12"),
    dict(hora="14:45", pais="Inglaterra", sexo="M", liga="Championship",
         local="Middlesbrough", visita="Millwall", tens="Media",
         goles="2", ht="0–1", corn="9–11", tarj="4–6", rem="12–15 · 10–13", sot="4 · 3–4",
         ir="+1.5 · −3.5 · +4.5 tarjetas", no="Over 3.5",
         extra="Millwall físico. Corners 9–11"),
    dict(hora="15:00", pais="Inglaterra", sexo="M", liga="Championship",
         local="Bolton", visita="West Ham", tens="Media+",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="10–13 · 13–16", sot="3–4 · 5",
         ir="X2 West Ham · +1.5", no="Bolton ML",
         extra="West Ham calidad. Corners 9–12"),
    # --- League One / Eredivisie ---
    dict(hora="14:45", pais="Inglaterra", sexo="M", liga="League One",
         local="Oxford", visita="Reading", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="12–15 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank",
         extra="League One. Corners 9–12"),
    dict(hora="12:45", pais="Holanda", sexo="M", liga="Eredivisie",
         local="NEC Nijmegen", visita="Excelsior", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="13–16 · 10–13", sot="4–5 · 3–4",
         ir="1X NEC · +1.5", no="Under 1.5",
         extra="Eredivisie. Corners 9–12"),
    # --- Finland / Korea / Egypt sample ---
    dict(hora="11:00", pais="Finlandia", sexo="M", liga="Veikkausliiga",
         local="HJK", visita="KuPS", tens="Media",
         goles="2–3", ht="1", corn="9–11", tarj="3–4", rem="12–15 · 10–13", sot="4 · 3–4",
         ir="1X HJK · +1.5", no="Under 1.5",
         extra="Finlandia. Corners 9–11"),
    dict(hora="06:00", pais="Corea", sexo="M", liga="K League 1",
         local="Ulsan", visita="Jeonbuk", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="12–15 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank",
         extra="K League. Corners 9–12"),
    dict(hora="12:00", pais="Egipto", sexo="M", liga="Premier",
         local="Al Ahly", visita="Zamalek", tens="ALTA",
         goles="2–3", ht="1", corn="9–12", tarj="5–7", rem="12–15 · 11–14", sot="4–5 · 4",
         ir="+1.5 · +5.5 tarjetas", no="−4.5 tarjetas · Under 1.5",
         extra="CLÁSICO Egipto. Tarjetas altas. Corners 9–12"),
    # --- FEMENINAS 08/09 (1ª + 2ª división / regionales) ---
    dict(hora="14:00", pais="México", sexo="F", liga="Liga MX Femenil",
         local="Atlante F", visita="Juárez F", tens="Baja",
         goles="2–3", ht="1", corn="8–12", tarj="3–4", rem="11–15 · 11–15", sot="4–6 · 4–6",
         ir="+2.5 · BTTS ficha", no="Under 1.5 · bank",
         extra="Reprogramado. Femenil abierta. Corners 8–12"),
    dict(hora="15:00", pais="Chile", sexo="F", liga="Amistoso U20 F",
         local="Chile U20 F", visita="Uruguay U20 F", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="11–14 · 10–13", sot="4 · 3–4",
         ir="+1.5 · −3.5", no="Under 1.5",
         extra="Sub-20 F. Corners 8–11"),
    dict(hora="11:00", pais="Brasil", sexo="F", liga="Brasileirão F A1",
         local="Ferroviária F", visita="Palmeiras F", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="3–4", rem="12–15 · 11–14", sot="4–5 · 4",
         ir="+1.5 · −3.5 · 1X Ferro", no="Under 1.5",
         extra="Serie A1 F. Corners 9–12"),
    dict(hora="12:00", pais="Brasil", sexo="F", liga="Brasileirão F A1",
         local="Corinthians F", visita="Flamengo F", tens="Media+",
         goles="2–3", ht="1", corn="9–13", tarj="3–5", rem="13–16 · 10–13", sot="5 · 3–4",
         ir="1X Corinthians F · +1.5", no="Under 1.5",
         extra="Top BR F. Corners 9–13"),
    dict(hora="16:00", pais="Argentina", sexo="F", liga="Primera F AFA",
         local="Boca F", visita="Racing F", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="12–15 · 10–13", sot="4 · 3–4",
         ir="1X Boca F · +1.5", no="Under 1.5",
         extra="Primera F ARG. Corners 8–11"),
    dict(hora="16:00", pais="Argentina", sexo="F", liga="Primera F AFA",
         local="River F", visita="San Lorenzo F", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="12–15 · 10–13", sot="4 · 3–4",
         ir="1X River F · +1.5", no="Under 1.5",
         extra="Primera F ARG. Corners 8–11"),
    dict(hora="14:00", pais="Colombia", sexo="F", liga="Liga Femenina",
         local="Santa Fe F", visita="América Cali F", tens="Media",
         goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank",
         extra="Liga Femenina COL. Corners 8–11"),
    dict(hora="10:00", pais="Noruega", sexo="F", liga="Toppserien",
         local="Rosenborg F", visita="Vålerenga F", tens="Media",
         goles="3–4", ht="1–2", corn="9–12", tarj="2–4", rem="12–16 · 12–16", sot="5 · 5",
         ir="+2.5 · BTTS", no="Under 1.5",
         extra="Toppserien abierta. Corners 9–12"),
    dict(hora="11:00", pais="Suecia", sexo="F", liga="Damallsvenskan",
         local="Hammarby F", visita="Häcken F", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="2–4", rem="12–15 · 11–14", sot="4–5 · 4",
         ir="+1.5 · −3.5", no="Under 1.5",
         extra="Damallsvenskan. Corners 9–12"),
    dict(hora="12:00", pais="Inglaterra", sexo="F", liga="Championship F",
         local="Charlton F", visita="London City Lionesses", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–4", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank",
         extra="Div 2 Inglaterra F. Corners 9–12"),
    dict(hora="12:00", pais="Inglaterra", sexo="F", liga="Championship F",
         local="Southampton F", visita="Birmingham F", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="3–4", rem="12–15 · 10–13", sot="4 · 3–4",
         ir="+1.5 · −3.5", no="Bank",
         extra="Div 2 Inglaterra F. Corners 9–12"),
    dict(hora="13:00", pais="España", sexo="F", liga="Primera Federación F",
         local="Madrid CFF B", visita="Fundación Albacete", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="11–14 · 10–13", sot="4 · 3–4",
         ir="+1.5 · −3.5", no="Bank",
         extra="2ª división F ESP. Corners 8–11"),
    dict(hora="11:00", pais="Alemania", sexo="F", liga="2. Frauen-Bundesliga",
         local="Werder II F", visita="Freiburg II F", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank",
         extra="2. Bundesliga F. Corners 8–11"),
    dict(hora="14:00", pais="Italia", sexo="F", liga="Serie B Femminile",
         local="Parma F", visita="Brescia F", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="11–14 · 10–13", sot="4 · 3–4",
         ir="+1.5 · −3.5", no="Bank",
         extra="Serie B F. Corners 8–11"),
    dict(hora="15:00", pais="EEUU", sexo="F", liga="USL Super League F",
         local="Brooklyn FC F", visita="Dallas Trinity F", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank",
         extra="USL Super League (div 2 USA). Corners 8–11"),
    # --- LIGAS ÁRABES 08/09 ---
    dict(hora="11:30", pais="Arabia Saudita", sexo="M", liga="Pro League",
         local="Al Ettifaq", visita="Al Faisaly", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="12–15 · 10–13", sot="4 · 3–4",
         ir="1X Ettifaq · +1.5 · −3.5", no="Under 1.5",
         extra="Roshan. Corners 9–12"),
    dict(hora="11:55", pais="Arabia Saudita", sexo="M", liga="Pro League",
         local="Al Hazem", visita="Al Taawoun", tens="Baja",
         goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="11–14 · 12–15", sot="3–4 · 4",
         ir="+1.5 · −3.5 · X2 Taawoun ficha", no="Under 1.5",
         extra="Roshan. Corners 9–12"),
    dict(hora="14:00", pais="Arabia Saudita", sexo="M", liga="Pro League",
         local="Al Ittihad", visita="Al Fayha", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="14–17 · 9–12", sot="5–6 · 3",
         ir="1X Ittihad · +1.5 · +0.5 1T", no="Under 1.5 · Fayha ML",
         extra="Ittihad favorito casa. Corners 9–12"),
    dict(hora="14:00", pais="Arabia Saudita", sexo="M", liga="Pro League",
         local="Al Qadsiah", visita="Al Ahli", tens="Media+",
         goles="2–3", ht="1", corn="9–13", tarj="3–5", rem="12–15 · 12–15", sot="4–5 · 4–5",
         ir="+1.5 · −3.5 · BTTS ficha", no="Under 1.5",
         extra="Qadsiah vs Ahli. Corners 9–13"),
    dict(hora="11:50", pais="Arabia Saudita", sexo="M", liga="Yelo League (1ª)",
         local="Damac", visita="AlUla", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank",
         extra="Primera Saudí. Corners 8–11"),
    dict(hora="11:50", pais="Arabia Saudita", sexo="M", liga="Yelo League (1ª)",
         local="Al Zulfi", visita="Hajer", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="11–14 · 10–13", sot="4 · 3–4",
         ir="+1.5 · −3.5", no="Bank",
         extra="Primera Saudí. Corners 8–11"),
    dict(hora="13:20", pais="Arabia Saudita", sexo="M", liga="Yelo League (1ª)",
         local="Al Anwar", visita="Al Tai", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank",
         extra="Primera Saudí. Corners 8–11"),
    dict(hora="13:00", pais="Egipto", sexo="M", liga="Premier",
         local="Smouha", visita="Ceramica Cleopatra", tens="Baja",
         goles="2–3", ht="1", corn="8–11", tarj="4–5", rem="11–14 · 11–14", sot="4 · 4",
         ir="+1.5 · −3.5", no="Bank",
         extra="Premier Egipto. Corners 8–11"),
    dict(hora="13:00", pais="Egipto", sexo="M", liga="Premier",
         local="Zamalek", visita="Abu Qir", tens="Media",
         goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="14–17 · 9–12", sot="5–6 · 3",
         ir="1X Zamalek · +1.5 · +0.5 1T", no="Under 1.5 · Abu Qir ML",
         extra="Zamalek favorito. Corners 9–12"),
]

NEED08 = {
    "AEK Athens": "Casa UCL.",
    "Club Brugge": "Villa calidad.",
    "Dortmund": "Casa debe sumar.",
    "Porto": "City favorito.",
    "Lille": "Paridad.",
    "Real Madrid": "Clásico. Tensión ALTA.",
    "Blackburn": "Championship puntos.",
    "Southampton": "Saints favorito casa.",
    "Wrexham": "Burnley nivel superior.",
    "Bolton": "West Ham favorito.",
    "Al Ahly": "Clásico Egipto. Tensión ALTA.",
    "Al Ittihad": "Ittihad debe ganar en casa.",
    "Al Qadsiah": "Choque top-mid tabla saudí.",
    "Zamalek": "Zamalek favorito vs Abu Qir.",
    "Al Ettifaq": "3 pts Roshan.",
}
GOL08 = {"Dortmund", "Real Madrid", "Porto", "Southampton", "Rosenborg F", "Corinthians F", "Atlante F", "Al Ittihad", "Al Qadsiah"}
HT08 = {"Dortmund", "Real Madrid", "Porto", "Club Brugge", "Southampton", "Rosenborg F", "Corinthians F", "Al Ittihad", "Zamalek"}
CERRADOS08 = {"Cardiff", "Middlesbrough"}

for m in MATCHES_08:
    m["dia"] = "08/09"
    m["need"] = NEED08.get(m["local"], "Puntos de jornada.")
    m["logo_l"] = logo_for(m["local"])
    m["logo_v"] = logo_for(m["visita"])
    m["res"] = "X"
    m["dc"] = "1X"
    m["res_txt"] = m.get("liga", "")
    m["gana"] = "Abierto"
    m["goles_alta"] = "1" if m["local"] in GOL08 else "0"
    if m["local"] in CERRADOS08:
        m["cerrado"] = "1"
        m["ht_gol"], m["ht_pct"] = "baja", "38–45%"
    elif m["local"] in HT08:
        m["cerrado"] = "0"
        m["ht_gol"], m["ht_pct"] = "alta", "58–65%"
    else:
        m["cerrado"] = "0"
        m["ht_gol"], m["ht_pct"] = "media", "50–58%"


# === 09/09 + 10/09 RESULTADOS (córners / tarjetas) ===
CERRADOS += [
    dict(partido="Midtjylland vs Nordsjælland", pick="+1.5 · −3.5",
         ft="2-2", extra="+1.5 sí · −3.5 no", estado="ROJO",
         corn_pick="9–11", corn_ft="10", corn_ok="SÍ",
         tarj_pick="3–5", tarj_ft="6", tarj_ok="NO"),
    dict(partido="Pumas vs León", pick="+1.5 · 1X Pumas",
         ft="3-1", extra="+1.5 SÍ · 1X SÍ · 4 goles −3.5 NO · Juninho/Morales/Vite", estado="VERDE",
         corn_pick="9–12", corn_ft="—", corn_ok="PEND",
         tarj_pick="4–6", tarj_ft="—", tarj_ok="PEND"),
]


CERRADOS += [
    # 09/09 UCL + copas + B + fem/juvenil donde hay FT
    dict(partido="Barcelona vs Feyenoord", pick="Barça −1.5 · +2.5", ft="5-1", extra="+2.5 SÍ · −1.5 SÍ · 6 goles", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Stuttgart vs Viking", pick="Stuttgart −1.5 · +2.5", ft="3-1", extra="+2.5 SÍ · −1.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Liverpool vs Atlético Madrid", pick="+1.5 · 1X Liverpool", ft="2-1", extra="+1.5 SÍ · 1X SÍ · −3.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="PSG vs Slovan Bratislava", pick="PSG −1.5 · +2.5", ft="6-1", extra="Goleada · +2.5 SÍ · −1.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Sporting vs Galatasaray", pick="+1.5 · 1X Sporting", ft="3-1", extra="+1.5 SÍ · 1X SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Napoli vs Arsenal", pick="X2 Arsenal · −2.5", ft="0-1", extra="X2 SÍ · −2.5 SÍ · +1.5 NO", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Chelsea vs Leeds", pick="+2.5 · 1X Chelsea", ft="6-3", extra="+2.5 SÍ · 9 goles · Carabao", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Botafogo-SP vs Novorizontino", pick="+1.5", ft="1-3", extra="+1.5 SÍ · Série B", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Fortaleza vs Avaí", pick="1X Fortaleza · −2.5", ft="1-0", extra="1X SÍ · −2.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="América Mineiro vs Náutico", pick="+1.5", ft="2-1", extra="+1.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Operário PR vs CRB", pick="1X Operário · +1.5", ft="3-0", extra="+1.5 SÍ · 1X SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Atlético Goianiense vs Ceará", pick="+1.5", ft="2-1", extra="+1.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Atlanta United vs Orlando City", pick="+1.5", ft="2-3", extra="+1.5 SÍ · 5 goles", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    # 10/09
    dict(partido="Bayern vs Bodø/Glimt", pick="Bayern −1.5 · +2.5", ft="5-0", extra="+2.5 SÍ · −1.5 SÍ · 2T goleada", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Manchester United vs Sabah", pick="United −1.5 · +2.5", ft="4-0", extra="+2.5 SÍ · −1.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Como vs RB Leipzig", pick="+1.5 · 12", ft="4-1", extra="+1.5 SÍ · 5 goles", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Slavia Prague vs Lens", pick="+1.5 · BTTS", ft="2-3", extra="+1.5 SÍ · BTTS SÍ · 5 goles", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Fenerbahce vs Roma", pick="+1.5 · X2 Roma", ft="1-1", extra="+1.5 SÍ · X2 SÍ · −2.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="PSV vs Shakhtar", pick="+1.5 · 1X PSV", ft="1-1", extra="+1.5 SÍ · 1X SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Vila Nova vs Goiás", pick="1X Vila · −2.5", ft="2-0", extra="1X SÍ · −2.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="São Bernardo vs Londrina", pick="+1.5", ft="1-2", extra="+1.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Sport Recife vs Ponte Preta", pick="1X Sport · −2.5", ft="2-0", extra="1X SÍ · −2.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Stevenage vs Luton", pick="+1.5 · 1X Stevenage", ft="2-1", extra="+1.5 SÍ · 1X SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Estrela vs Braga", pick="+1.5 · X2 Braga", ft="2-1", extra="+1.5 SÍ · X2 NO", estado="ROJO", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Estudiantes vs Corinthians", pick="−2.5 · +4.5 tarjetas", ft="1-1", extra="Under SÍ · Libertadores", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Panathinaikos vs Kifisia", pick="Pana −1.5 · +2.5", ft="3-1", extra="+2.5 SÍ · −1.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Spain W U20 vs New Caledonia W U20", pick="España −2.5 · +3.5", ft="11-0", extra="Goleada fem sub-20", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="Colombia W U20 vs Portugal W U20", pick="−2.5 · Under", ft="0-0", extra="Under SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
    dict(partido="North Korea W U20 vs Costa Rica W U20", pick="RPD −1.5 · +2.5", ft="4-0", extra="+2.5 SÍ · −1.5 SÍ", estado="VERDE", corn_ok="PEND", tarj_ok="PEND"),
]

MATCHES_09 = [
    dict(hora="13:00", pais="Dinamarca", sexo="M", liga="Superliga",
         local="Midtjylland", visita="Nordsjælland", tens="Media",
         goles="2–3", ht="1", corn="9–11", tarj="3–5", rem="13–15 · 12–14", sot="5 · 4–5",
         ir="+1.5 · −3.5", no="−1.5", extra="Top-3 danés. Empate 2-2 real"),
]
MATCHES_09 += [
    dict(hora="13:45", pais="Europa", sexo="M", liga="UCL J1", local="Barcelona", visita="Feyenoord", tens="Baja", goles="4–5", ht="2", corn="10–13", tarj="3–4", rem="18–22 · 8–10", sot="8–10 · 3", ir="Barça −1.5 · +2.5", no="Feyenoord +0.5"),
    dict(hora="13:45", pais="Europa", sexo="M", liga="UCL J1", local="Stuttgart", visita="Viking", tens="Baja", goles="3–4", ht="2", corn="10–12", tarj="3–4", rem="16–18 · 8–10", sot="6–8 · 3", ir="Stuttgart −1.5 · +2.5", no="Viking +0.5"),
    dict(hora="16:00", pais="Europa", sexo="M", liga="UCL J1", local="Liverpool", visita="Atlético Madrid", tens="Media+", goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="14–16 · 11–13", sot="5–6 · 4", ir="+1.5 · 1X Liverpool", no="Atlético seco"),
    dict(hora="16:00", pais="Europa", sexo="M", liga="UCL J1", local="PSG", visita="Slovan Bratislava", tens="Baja", goles="4–5", ht="2", corn="10–13", tarj="2–4", rem="20–24 · 6–8", sot="9–11 · 2", ir="PSG −1.5 · +2.5", no="Slovan +0.5"),
    dict(hora="16:00", pais="Europa", sexo="M", liga="UCL J1", local="Sporting", visita="Galatasaray", tens="Media", goles="3", ht="1", corn="9–12", tarj="4–5", rem="14–16 · 11–13", sot="5–6 · 4", ir="+1.5 · 1X Sporting", no="−1.5"),
    dict(hora="16:00", pais="Europa", sexo="M", liga="UCL J1", local="Napoli", visita="Arsenal", tens="Media+", goles="1–2", ht="0–1", corn="8–11", tarj="4–5", rem="11–13 · 12–14", sot="3–4 · 4–5", ir="X2 Arsenal · −2.5", no="+3.5"),
    dict(hora="14:45", pais="Inglaterra", sexo="M", liga="EFL Cup", local="Chelsea", visita="Leeds", tens="Media", goles="3–4", ht="1–2", corn="10–13", tarj="3–5", rem="16–18 · 12–14", sot="6–8 · 4–5", ir="+2.5 · 1X Chelsea", no="under 1.5"),
    dict(hora="18:00", pais="Brasil", sexo="M", liga="Série B", local="Botafogo-SP", visita="Novorizontino", tens="Media", goles="2–3", ht="1", corn="9–11", tarj="4–5", rem="11–13 · 12–14", sot="4 · 4–5", ir="+1.5", no="−1.5"),
    dict(hora="18:00", pais="Brasil", sexo="M", liga="Série B", local="Fortaleza", visita="Avaí", tens="Media", goles="2", ht="0–1", corn="9–11", tarj="4–5", rem="13–15 · 9–11", sot="4–5 · 3", ir="1X Fortaleza · −2.5", no="+3.5"),
    dict(hora="18:00", pais="Brasil", sexo="M", liga="Série B", local="América Mineiro", visita="Náutico", tens="Media", goles="2–3", ht="1", corn="9–11", tarj="4–5", rem="12–14 · 11–13", sot="4 · 3–4", ir="+1.5", no="−1.5"),
    dict(hora="18:00", pais="Brasil", sexo="M", liga="Série B", local="Operário PR", visita="CRB", tens="Media", goles="2–3", ht="1", corn="9–11", tarj="4–5", rem="13–15 · 10–12", sot="4–5 · 3–4", ir="1X Operário · +1.5", no="−1.5"),
    dict(hora="18:00", pais="Brasil", sexo="M", liga="Série B", local="Atlético Goianiense", visita="Ceará", tens="Media", goles="2–3", ht="1", corn="9–11", tarj="4–5", rem="12–14 · 11–13", sot="4 · 4", ir="+1.5", no="−1.5"),
]
for m in MATCHES_09:
    m.update(dia="09/09", need="No perder el tren del liderato.", logo_l=logo_for(m["local"]), logo_v=logo_for(m["visita"]), res="X", dc="12", res_txt="Abierto", gana="Abierto", goles_alta="0", cerrado="0", ht_gol="media", ht_pct="50–58%")

MATCHES_10 = [
    dict(hora="21:05", pais="México", sexo="M", liga="Liga MX Apertura J7",
         local="Pumas", visita="León", tens="Media+",
         goles="2–3", ht="1", corn="9–12", tarj="4–6", rem="12–14 · 11–13", sot="4–5 · 4–5",
         ir="+1.5 · +4.5 tarjetas · 1X Pumas", no="−5.5 tarjetas · León seco",
         extra="Pumas 12° 8pts 6 sin ganar. León 8° 10pts + 3er LC. Juninho"),
]
MATCHES_10 += [
    dict(hora="13:45", pais="Europa", sexo="M", liga="UCL J1", local="Bayern", visita="Bodø/Glimt", tens="Baja", goles="4–5", ht="1–2", corn="10–13", tarj="2–4", rem="20–24 · 6–8", sot="8–10 · 2", ir="Bayern −1.5 · +2.5", no="Bodø +0.5"),
    dict(hora="14:00", pais="Europa", sexo="M", liga="UCL J1", local="Manchester United", visita="Sabah", tens="Baja", goles="4", ht="2", corn="10–13", tarj="2–4", rem="18–22 · 5–7", sot="7–9 · 2", ir="United −1.5 · +2.5", no="Sabah +0.5"),
    dict(hora="15:00", pais="Europa", sexo="M", liga="UCL J1", local="Como", visita="RB Leipzig", tens="Media", goles="3–4", ht="1–2", corn="9–12", tarj="3–5", rem="13–15 · 12–14", sot="5–6 · 4–5", ir="+1.5 · 12", no="under 1.5"),
    dict(hora="15:00", pais="Europa", sexo="M", liga="UCL J1", local="Slavia Prague", visita="Lens", tens="Media", goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="12–14 · 12–14", sot="4–5 · 4–5", ir="+1.5 · BTTS", no="0-0"),
    dict(hora="13:45", pais="Europa", sexo="M", liga="UCL J1", local="Fenerbahce", visita="Roma", tens="Media+", goles="2", ht="1", corn="9–11", tarj="4–6", rem="12–14 · 11–13", sot="4 · 4", ir="+1.5 · X2 Roma", no="+3.5"),
    dict(hora="12:45", pais="Europa", sexo="M", liga="UCL J1", local="PSV", visita="Shakhtar", tens="Media", goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="14–16 · 11–13", sot="5 · 4", ir="+1.5 · 1X PSV", no="−1.5"),
    dict(hora="18:00", pais="Brasil", sexo="M", liga="Série B", local="Vila Nova", visita="Goiás", tens="Media", goles="2", ht="0–1", corn="9–11", tarj="4–5", rem="12–14 · 10–12", sot="4 · 3", ir="1X Vila · −2.5", no="+3.5"),
    dict(hora="18:00", pais="Brasil", sexo="M", liga="Série B", local="São Bernardo", visita="Londrina", tens="Media", goles="2–3", ht="1", corn="9–11", tarj="4–5", rem="12–14 · 11–13", sot="4 · 4", ir="+1.5", no="−1.5"),
    dict(hora="18:00", pais="Brasil", sexo="M", liga="Série B", local="Sport Recife", visita="Ponte Preta", tens="Baja", goles="2", ht="1", corn="9–11", tarj="4–5", rem="14–16 · 8–10", sot="5 · 2–3", ir="1X Sport · −2.5", no="+3.5"),
    dict(hora="15:00", pais="Inglaterra", sexo="M", liga="League One", local="Stevenage", visita="Luton", tens="Media", goles="2–3", ht="1", corn="9–11", tarj="4–5", rem="12–14 · 12–14", sot="4 · 4", ir="+1.5 · 1X Stevenage", no="−1.5"),
    dict(hora="14:00", pais="Portugal", sexo="M", liga="Primeira Liga", local="Estrela", visita="Braga", tens="Media", goles="2–3", ht="1", corn="9–11", tarj="4–5", rem="10–12 · 14–16", sot="3–4 · 5", ir="+1.5 · X2 Braga", no="−1.5"),
    dict(hora="19:00", pais="Sudamérica", sexo="M", liga="Libertadores", local="Estudiantes", visita="Corinthians", tens="ALTA", goles="1–2", ht="0–1", corn="8–11", tarj="5–7", rem="11–13 · 11–13", sot="3–4 · 3–4", ir="−2.5 · +4.5 tarjetas", no="+3.5"),
    dict(hora="14:15", pais="Grecia", sexo="M", liga="Super League", local="Panathinaikos", visita="Kifisia", tens="Baja", goles="3", ht="1–2", corn="9–12", tarj="3–4", rem="16–18 · 8–10", sot="6–7 · 3", ir="Pana −1.5 · +2.5", no="Kifisia +0.5"),
    dict(hora="12:00", pais="Mundial", sexo="F", liga="Mundial sub-20 F", local="Spain W U20", visita="New Caledonia W U20", tens="Baja", goles="5+", ht="3", corn="10–14", tarj="1–3", rem="22–28 · 3–5", sot="10–14 · 1", ir="España −2.5 · +3.5", no="under 2.5"),
    dict(hora="15:00", pais="Mundial", sexo="F", liga="Mundial sub-20 F", local="Colombia W U20", visita="Portugal W U20", tens="Media", goles="1–2", ht="0–1", corn="8–11", tarj="3–4", rem="11–13 · 11–13", sot="3–4 · 3–4", ir="−2.5 · Under", no="+3.5"),
    dict(hora="12:00", pais="Mundial", sexo="F", liga="Mundial sub-20 F", local="North Korea W U20", visita="Costa Rica W U20", tens="Baja", goles="3–4", ht="2", corn="9–12", tarj="2–3", rem="16–20 · 6–8", sot="7–9 · 2", ir="RPD −1.5 · +2.5", no="Costa Rica +0.5"),
]
for m in MATCHES_10:
    m.update(dia="10/09", need="3 pts en CU. Bennevendo baja. León caliente de LC.", logo_l="", logo_v="", res="1", dc="1X", res_txt="1X Pumas", gana="Pumas gana o empata", goles_alta="0", cerrado="0", ht_gol="media", ht_pct="52–58%")

MATCHES_11 = [
    dict(hora="12:00", pais="Dinamarca", sexo="M", liga="Superliga J8", local="Copenhagen", visita="Horsens", tens="Baja", goles="3–4", ht="1–2", corn="10–13", tarj="3–4", rem="15–18 · 8–11", sot="6–8 · 3–4", ir="FCK −1.5 · +2.5", no="Horsens seco · under 1.5", extra="FCK 1° 18pts 20-8. Horsens 6° 10pts 13-12. FCK 5-0 OB. Horsens 5-2"),
    dict(hora="14:00", pais="España", sexo="M", liga="La Liga J5", local="Sevilla", visita="Valencia", tens="Media", goles="2", ht="1", corn="9–11", tarj="4–5", rem="13–15 · 9–11", sot="4–5 · 3", ir="1X Sevilla · −2.5", no="+3.5 · Valencia −1", extra="Sevilla 7pts. Valencia colista 1pt 1-9"),
    dict(hora="13:00", pais="Países Bajos", sexo="M", liga="Eredivisie", local="AZ Alkmaar", visita="Willem II", tens="Baja", goles="3–4", ht="2", corn="10–13", tarj="3–4", rem="16–20 · 7–9", sot="6–8 · 2–3", ir="AZ −1.5 · +2.5", no="Willem II +0.5"),
    dict(hora="15:00", pais="Perú", sexo="M", liga="Liga 1 Clausura", local="UTC Cajamarca", visita="Juan Pablo II", tens="Media", goles="2", ht="0–1", corn="8–11", tarj="4–6", rem="12–14 · 10–12", sot="4 · 3–4", ir="1X UTC · −2.5 · +4.5 tarjetas", no="+3.5"),
    dict(hora="19:00", pais="Perú", sexo="M", liga="Liga 1 Clausura J9", local="Cusco FC", visita="Melgar", tens="ALTA", goles="2–3", ht="1", corn="9–12", tarj="4–6", rem="12–14 · 12–14", sot="4–5 · 4–5", ir="+1.5 · 1X Cusco · +4.5 tarjetas", no="Melgar seco", extra="Cusco 15 / Melgar 14. Altura. Callejo vs Cuesta"),
    dict(hora="12:00", pais="Turquía", sexo="M", liga="Süper Lig", local="Besiktas", visita="Erzurum BB", tens="Baja", goles="3", ht="1–2", corn="10–12", tarj="3–5", rem="16–19 · 7–9", sot="6–7 · 2–3", ir="BJK −1.5 · +2.5", no="Erzurum +0.5"),
    dict(hora="13:45", pais="Francia", sexo="M", liga="Ligue 1", local="Rennes", visita="Marseille", tens="Media+", goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="12–14 · 12–14", sot="4–5 · 4–5", ir="+1.5 · BTTS · 12", no="under 1.5"),
    dict(hora="13:00", pais="Arabia Saudita", sexo="M", liga="Saudi Pro League", local="Al Ahli", visita="Al Hazem", tens="Baja", goles="3–4", ht="1–2", corn="10–12", tarj="3–4", rem="16–19 · 7–9", sot="6–8 · 2–3", ir="Ahli −1.5 · +2.5", no="Hazem +0.5"),
    dict(hora="19:30", pais="Argentina", sexo="M", liga="Liga Profesional", local="Boca", visita="Central Córdoba", tens="Media", goles="1–2", ht="0–1", corn="8–11", tarj="4–6", rem="14–16 · 8–10", sot="4–5 · 2–3", ir="1X Boca · −2.5 · +4.5 tarjetas", no="+3.5"),
    dict(hora="13:30", pais="Alemania", sexo="M", liga="Bundesliga", local="Union Berlin", visita="Schalke", tens="Media", goles="1–2", ht="0–1", corn="8–11", tarj="4–6", rem="11–13 · 10–12", sot="3–4 · 3–4", ir="−2.5 · +4.5 tarjetas · 1X Union", no="+3.5"),
    dict(hora="14:00", pais="Inglaterra", sexo="M", liga="Championship", local="West Ham", visita="Wrexham", tens="Media", goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="14–16 · 10–12", sot="5 · 3–4", ir="+1.5 · 1X West Ham", no="Wrexham −1"),
    dict(hora="13:45", pais="Italia", sexo="M", liga="Serie A", local="Venezia", visita="Fiorentina", tens="Media+", goles="1–2", ht="0–1", corn="8–10", tarj="4–6", rem="10–12 · 12–14", sot="3 · 4", ir="−2.5 · X2 Fiorentina · +4.5 tarjetas", no="+3.5"),
    dict(hora="10:25", pais="Arabia Saudita", sexo="M", liga="Saudi Pro League", local="Al Qadsiah", visita="Al Ettifaq", tens="Baja", goles="3", ht="1–2", corn="9–12", tarj="3–4", rem="15–18 · 8–10", sot="5–7 · 3", ir="Qadsiah −1.5 · +2.5", no="Ettifaq +0.5"),
    dict(hora="10:45", pais="Arabia Saudita", sexo="M", liga="Saudi Pro League", local="Al Faisaly", visita="Al Ittihad", tens="Baja", goles="3", ht="1–2", corn="9–12", tarj="3–5", rem="8–10 · 15–18", sot="3 · 6–8", ir="Ittihad −1.5 · +2.5", no="Faisaly +0.5"),
    dict(hora="12:30", pais="Austria", sexo="M", liga="Bundesliga AT", local="SV Ried", visita="Salzburg", tens="Baja", goles="3", ht="1–2", corn="9–12", tarj="3–4", rem="7–9 · 16–19", sot="2–3 · 6–8", ir="Salzburg −1.5 · +2.5", no="Ried +0.5"),
    dict(hora="19:00", pais="Brasil", sexo="M", liga="Brasileirão", local="Coritiba", visita="Athletico PR", tens="ALTA", goles="2", ht="0–1", corn="9–12", tarj="5–7", rem="11–13 · 12–14", sot="3–4 · 4–5", ir="−2.5 · +4.5 tarjetas · X2 Athletico", no="−5.5 tarjetas"),
    dict(hora="16:00", pais="Argentina", sexo="M", liga="Liga Profesional", local="Newell's", visita="Vélez", tens="ALTA", goles="1–2", ht="0–1", corn="8–11", tarj="5–7", rem="11–13 · 11–13", sot="3–4 · 3–4", ir="−2.5 · +5.5 tarjetas · 12", no="+3.5 · 1 seco"),
    dict(hora="17:15", pais="Argentina", sexo="M", liga="Liga Profesional", local="Defensa y Justicia", visita="Gimnasia Mendoza", tens="Media", goles="2", ht="1", corn="9–11", tarj="4–6", rem="12–14 · 10–12", sot="4 · 3–4", ir="1X Defensa · −2.5 · +4.5 tarjetas", no="+3.5"),
    dict(hora="13:45", pais="Bélgica", sexo="M", liga="Pro League", local="Mechelen", visita="Anderlecht", tens="Media", goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="10–12 · 14–16", sot="3–4 · 5–6", ir="X2 Anderlecht · +1.5", no="Mechelen −1"),
    dict(hora="13:45", pais="España", sexo="F", liga="Liga F", local="Deportivo F", visita="Real Madrid F", tens="Baja", goles="3–4", ht="1–2", corn="9–12", tarj="2–4", rem="7–9 · 16–20", sot="2–3 · 6–9", ir="Madrid F −1.5 · +2.5", no="Depor +0.5"),
    dict(hora="12:00", pais="Italia", sexo="F", liga="Serie A Femminile", local="Roma F", visita="Juventus F", tens="Media+", goles="2–3", ht="1", corn="8–11", tarj="3–4", rem="11–13 · 13–15", sot="4 · 5", ir="+1.5 · X2 Juve F", no="−1.5"),
    dict(hora="11:00", pais="Alemania", sexo="F", liga="Frauen-Bundesliga", local="Wolfsburg F", visita="Hoffenheim F", tens="Baja", goles="3", ht="1–2", corn="9–12", tarj="2–4", rem="16–19 · 8–10", sot="6–8 · 3", ir="Wolfsburg F −1.5 · +2.5", no="Hoffenheim F +0.5"),
    dict(hora="12:30", pais="Inglaterra", sexo="F", liga="WSL", local="Arsenal F", visita="Everton F", tens="Baja", goles="3–4", ht="2", corn="10–13", tarj="2–3", rem="18–22 · 6–8", sot="7–9 · 2", ir="Arsenal F −1.5 · +2.5", no="Everton F +0.5"),
    dict(hora="14:00", pais="Francia", sexo="F", liga="D1 Arkema", local="Lyon F", visita="Paris FC F", tens="Media", goles="3", ht="1–2", corn="9–12", tarj="2–4", rem="16–20 · 8–10", sot="6–8 · 3", ir="Lyon F −1.5 · +2.5", no="−1.5 goles"),
    dict(hora="13:00", pais="España", sexo="M", liga="LaLiga2", local="Oviedo", visita="Racing Santander", tens="Media", goles="2", ht="1", corn="9–11", tarj="4–5", rem="12–14 · 11–13", sot="4 · 3–4", ir="+1.5 · −3.5 · 1X Oviedo", no="+3.5"),
    dict(hora="13:00", pais="Italia", sexo="M", liga="Serie B", local="Palermo", visita="Spezia", tens="Media", goles="2", ht="0–1", corn="9–11", tarj="4–6", rem="12–14 · 11–13", sot="4 · 3–4", ir="+1.5 · −3.5 · +4.5 tarjetas", no="+3.5"),
    dict(hora="13:30", pais="Alemania", sexo="M", liga="2. Bundesliga", local="Nürnberg", visita="Hannover", tens="Media", goles="2–3", ht="1", corn="9–12", tarj="4–5", rem="12–14 · 12–14", sot="4–5 · 4", ir="+1.5 · −3.5", no="−1.5"),
    dict(hora="13:30", pais="Alemania", sexo="M", liga="2. Bundesliga", local="Darmstadt", visita="Arminia", tens="Media", goles="2–3", ht="1", corn="9–11", tarj="4–5", rem="13–15 · 10–12", sot="4–5 · 3–4", ir="+1.5 · 1X Darmstadt", no="−1.5"),
    dict(hora="14:00", pais="Inglaterra", sexo="M", liga="League One", local="Bolton", visita="Huddersfield", tens="Media", goles="2–3", ht="1", corn="9–12", tarj="3–5", rem="13–15 · 11–13", sot="4–5 · 4", ir="+1.5 · −3.5", no="+4.5"),
    dict(hora="14:00", pais="Escocia", sexo="M", liga="Championship SCO", local="Morton", visita="Livingston", tens="Media", goles="2", ht="1", corn="9–11", tarj="4–5", rem="11–13 · 12–14", sot="3–4 · 4", ir="+1.5 · X2 Livingston", no="+3.5"),
    dict(hora="19:00", pais="Colombia", sexo="M", liga="BetPlay", local="Jaguares", visita="Fortaleza CEIF", tens="Media", goles="2", ht="0–1", corn="8–11", tarj="4–6", rem="11–13 · 11–13", sot="3–4 · 3–4", ir="−2.5 · +4.5 tarjetas", no="+3.5"),
    dict(hora="20:30", pais="Colombia", sexo="M", liga="BetPlay", local="Santa Fe", visita="Tolima", tens="Media+", goles="2", ht="0–1", corn="8–11", tarj="5–7", rem="11–13 · 11–13", sot="3–4 · 3–4", ir="−2.5 · +5.5 tarjetas · 1X Santa Fe", no="−5.5 tarjetas"),
    dict(hora="15:00", pais="Argentina", sexo="F", liga="Primera Femenina", local="Boca F", visita="Racing F", tens="Media", goles="2–3", ht="1", corn="8–11", tarj="3–5", rem="13–15 · 10–12", sot="5 · 3–4", ir="+1.5 · 1X Boca F", no="−1.5"),
    dict(hora="16:00", pais="Brasil", sexo="F", liga="Brasileirão Fem", local="Corinthians F", visita="Palmeiras F", tens="ALTA", goles="2–3", ht="1", corn="8–11", tarj="4–6", rem="12–14 · 12–14", sot="4–5 · 4–5", ir="+1.5 · +4.5 tarjetas · 12", no="0-0"),
]
NEED11 = {
    "Copenhagen": "Afirmar liderato (18pts) antes de Brøndby. 20 goles en 7.",
    "Sevilla": "Seguir racha ante colista (Valencia 1 gol a favor).",
    "AZ Alkmaar": "Meter diferencia. Willem II otro nivel.",
    "UTC Cajamarca": "Puntos de casa Clausura. Partido trabado.",
    "Cusco FC": "Pegarse arriba. Altura vs Melgar que viene de golear.",
    "Besiktas": "No fallar ante fondo de tabla. −1.5.",
    "Rennes": "3 pts casa. Marsella 1-0-2. Abierto.",
    "Al Ahli": "Ganar y gol-average.",
    "Boca": "No fallar en Bombonera.",
    "Union Berlin": "Primer triunfo. Partido bajo.",
    "West Ham": "Imponerse en Championship.",
    "Venezia": "Salir del 0-0-3. Under vive.",
    "Al Qadsiah": "Favorito corto y goles.",
    "Al Faisaly": "Ittihad visita-favorito.",
    "SV Ried": "Salzburg debe resolver.",
    "Coritiba": "Clásico PR. Cards + under 2.5.",
    "Newell's": "El más 50-50. Under y tarjetas.",
    "Defensa y Justicia": "1X local.",
    "Mechelen": "Anderlecht favorito visita.",
    "Deportivo F": "Madrid F debe golear.",
    "Roma F": "Clásico fem IT.",
    "Wolfsburg F": "Favorita Frauen.",
    "Arsenal F": "WSL volumen y −1.5.",
    "Lyon F": "D1 no fallar en casa.",
    "Oviedo": "LaLiga2 1X + under 3.5.",
    "Palermo": "Serie B cards + 2 goles.",
    "Nürnberg": "2.BL +1.5 −3.5.",
    "Darmstadt": "1X casa 2.BL.",
    "Bolton": "League One goles medios.",
    "Morton": "Livingston un tick arriba.",
    "Jaguares": "BetPlay under + cards.",
    "Santa Fe": "Colombia cards altas.",
    "Boca F": "Localía fem ARG.",
    "Corinthians F": "Clásico fem BR.",
}
GOL11 = {"Copenhagen","AZ Alkmaar","Besiktas","Al Ahli","Al Qadsiah","Al Faisaly","SV Ried","Deportivo F","Wolfsburg F","Arsenal F","Lyon F"}
HT11 = GOL11
CERR11 = {"Newell's","Union Berlin","Venezia","Sevilla","Boca","UTC Cajamarca","Coritiba","Oviedo"}
for m in MATCHES_11:
    m["dia"] = "11/09"
    m["need"] = NEED11.get(m["local"], "Puntos de jornada.")
    m["logo_l"] = logo_for(m["local"])
    m["logo_v"] = logo_for(m["visita"])
    if m["local"] in CERR11:
        m["res"], m["dc"], m["gana"], m["res_txt"] = "X", "1X", "Cerrado / 1X local", "Under + dobles"
        m["cerrado"] = "1"; m["ht_gol"], m["ht_pct"] = "baja", "38–48%"
    elif m["visita"] in ("Salzburg","Al Ittihad","Anderlecht","Real Madrid F","Athletico PR","Fiorentina"):
        m["res"], m["dc"], m["gana"], m["res_txt"] = "2", "X2", m["visita"]+" gana", "Visita favorita · X2"
        m["cerrado"] = "0"; m["ht_gol"], m["ht_pct"] = "media", "52–60%"
    else:
        m["res"], m["dc"], m["gana"], m["res_txt"] = "1", "1X", m["local"]+" gana o empata", "1X local"
        m["cerrado"] = "0"; m["ht_gol"], m["ht_pct"] = ("alta","58–65%") if m["local"] in HT11 else ("media","50–58%")
    m["goles_alta"] = "1" if m["local"] in GOL11 else "0"

ALL_MATCHES = MATCHES + MATCHES_03 + MATCHES_04 + MATCHES_05 + MATCHES_06 + MATCHES_07 + MATCHES_08 + MATCHES_09 + MATCHES_10 + MATCHES_11

for m in ALL_MATCHES:
    if "goles_alta" not in m:
        g = str(m.get("goles") or "")
        m["goles_alta"] = "1" if g[:1] in "3456" else "0"

for m in MATCHES:
    m["dia"] = "02/09"
    m["logo_l"] = logo_for(m["local"])
    m["logo_v"] = logo_for(m["visita"])
    code, dc, txt = DC.get(m["local"], ("X", "1X", "Sin lean fuerte"))
    m["res"] = code
    m["dc"] = dc
    m["res_txt"] = txt
    if code == "1":
        m["gana"] = m["local"] + " gana"
    elif code == "2":
        m["gana"] = m["visita"] + " gana"
    else:
        m["gana"] = "Empate / abierto"
    m.setdefault("ht_gol","media")
    m.setdefault("ht_pct","52–58%")
    m.setdefault("need","Mirar tabla: si pelea título, descenso o copa.")


# Horarios de calendario: la fuente de calendario entrega las horas en UTC.
# La interfaz las muestra siempre en hora de Perú (America/Lima, UTC-5).
def _peru_hhmm_from_utc_hhmm(value):
    try:
        raw=str(value or '').strip()
        if not raw or ':' not in raw or not raw[:2].isdigit():
            return raw
        hh,mm=map(int,raw[:5].split(':'))
        total=(hh*60+mm-300) % (24*60)
        return f"{total//60:02d}:{total%60:02d}"
    except Exception:
        return str(value or '')

def _peru_datetime_from_timestamp(ts):
    """Convierte un timestamp UNIX (UTC) a America/Lima.
    Se usa una zona IANA real para evitar errores de doble conversión/DST.
    Perú permanece en UTC-5 todo el año.
    """
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone(_pe_tz())
    except Exception:
        return None

def _peru_datetime_from_iso(value):
    """Convierte una fecha ISO de una API (normalmente UTC) a hora Perú."""
    try:
        raw=str(value or "").strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw=raw[:-1]+"+00:00"
        dt=datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_pe_tz())
    except Exception:
        return None



def is_cup_competition(league, country=""):
    """Identifica copas y torneos eliminatorios masculinos para marcarlos en el calendario."""
    x=(str(league or "")+" "+str(country or "")).lower().strip()
    if any(k in x for k in ("women", "femen", "female", "ladies", "u21", "u23", "reserve", "reserves")):
        return False
    return any(k in x for k in ("cup", "copa", "trophy", "challenge cup", "beker", "coupe", "pokal", "coppa", "taça", "taca"))


def _league_display(name, country=""):
    raw=" ".join(str(x or "") for x in (name, country)).lower()
    if any(k in raw for k in ("primera a","betplay","dimayor")) and any(k in raw for k in ("col","colombia","primera a","betplay","dimayor")):
        return "Liga BetPlay Dimayor"
    return name or "Fútbol"

def is_top_flight_league(league, country=""):
    """Marca únicamente competiciones de primera división/élite masculina.
    No marca copas, segundas divisiones, reservas, juveniles ni competiciones femeninas.
    """
    x=(str(league or "")+" "+str(country or "")).lower().strip()
    if any(k in x for k in ("women", "femen", "female", "ladies", "u21", "u23", "reserve", "reserves", "ii", " 2", "cup", "copa", "trophy", "challenge", "beker", "champions league")):
        # Excepción: Champions League masculina sí es una competición de élite, aunque no sea liga.
        if "champions league" not in x:
            return False
    patterns=(
        "premier league", "la liga", "laliga", "primera división", "primera a", "betplay", "dimayor", "indian super league", "isl", "i-league", "copa auf", "liga auf", "primera division",
        "primera a", "liga 1", "liga mx", "liga betplay", "liga bet play", "liga pro",
        "serie a", "bundesliga", "ligue 1", "eredivisie", "primeira liga", "premiership",
        "superliga", "super league", "pro league", "allsvenskan", "eliteserien",
        "super lig", "first league", "liga profesional", "primera categoría", "primera categoria",
        "jupiler pro league", "champions league"
    )
    return any(k in x for k in patterns)

def _calendar_row_from_event(ev, n, selected_date):
    dt=_peru_datetime_from_timestamp(ev.get('startTimestamp'))
    if not dt or dt.strftime('%Y-%m-%d') != selected_date:
        return None
    home=(ev.get('homeTeam') or {}).get('name') or '—'
    away=(ev.get('awayTeam') or {}).get('name') or '—'
    tournament=ev.get('uniqueTournament') or ev.get('tournament') or {}
    category=tournament.get('category') or {}
    status=ev.get('status') or {}
    status_type=status.get('type') or ''
    if status_type in ('finished','canceled','postponed'):
        return None
    estado='Programado'
    if status_type in ('inprogress','halftime'):
        estado='EN VIVO'
    return {
        'n': n,
        'event_id': ev.get('id'),
        'pais': category.get('name') or 'Internacional',
        'liga': tournament.get('name') or 'Fútbol',
        'hora': dt.strftime('%H:%M'),
        'local': home, 'visita': away, 'estado': (dt.strftime('%H:%M') if estado == 'Programado' else estado),
        'timestamp': ev.get('startTimestamp'), 'fecha': selected_date,
        'logo_l': logo_for(home), 'logo_v': logo_for(away),
        'top_flight': is_top_flight_league(tournament.get('name'), category.get('name')),
        'is_cup': is_cup_competition(tournament.get('name'), category.get('name')),
    }

CCODE_NAME={
    "ARG":"Argentina","BRA":"Brasil","CHI":"Chile","COL":"Colombia","PER":"Perú","URU":"Uruguay","PAR":"Paraguay","BOL":"Bolivia","ECU":"Ecuador","VEN":"Venezuela","MEX":"México","USA":"Estados Unidos","CAN":"Canadá",
    "ENG":"Inglaterra","ESP":"España","ITA":"Italia","GER":"Alemania","FRA":"Francia","POR":"Portugal","NED":"Países Bajos","BEL":"Bélgica","SCO":"Escocia","TUR":"Turquía","GRE":"Grecia","SUI":"Suiza","AUT":"Austria",
    "DEN":"Dinamarca","SWE":"Suecia","NOR":"Noruega","POL":"Polonia","CZE":"Chequia","ROU":"Rumania","HUN":"Hungría","CRO":"Croacia","SRB":"Serbia","UKR":"Ucrania","RUS":"Rusia","INT":"Internacional","EUR":"Europa",
    "JPN":"Japón","KOR":"Corea del Sur","CHN":"China","AUS":"Australia","KSA":"Arabia Saudita","UAE":"Emiratos","QAT":"Qatar","EGY":"Egipto","MAR":"Marruecos","IND":"India","RSA":"Sudáfrica","NGA":"Nigeria","CIV":"Costa de Marfil",
}

IMPORTANT_WOMEN_MARKERS=(
    "women's champions league","womens champions league","uwcl","uefa women's champions",
    "liga f","primera division femenina","primera femenina","liga femenina",
    "women's super league","wsl","barclays women's","barclays wsl",
    "frauen-bundesliga","frauen bundesliga","google pixel frauen",
    "serie a women","serie a femminile",
    "arkema","d1 femin","division 1 femin","premiere ligue femin",
    "nwsl",
    "liga mx femenil","femenil",
    "brasileirao feminino","brasileirão feminino","brasileirao feminina",
    "libertadores femenina","copa libertadores women",
    "women's world cup","womens world cup","world cup women",
    "women's euro","womens euro","euro femenina",
    "copa america femenina","copa américa femenina",
    "olympic","olimpi",
    "we league","we-league","nadeshiko","empress cup","empress's cup",
    "copa de la liga (f)","copa de la liga f",
)

def _is_women_competition(league, *names):
    blob=" ".join(str(x or "") for x in (league,)+names).lower()
    return any(k in blob for k in ("women","womens","femen","femin","female","ladies","nwsl","femenil","femminile","frauen","(w)"))

def _is_important_women(league, *names):
    blob=" ".join(str(x or "") for x in (league,)+names).lower()
    if any(k in blob for k in ("we league","nadeshiko","empress")):
        return True
    if any(k in blob for k in ("u17","u18","u19","u20","u21","youth","sub-17","sub-20","college","ncaa","europa cup","subway")):
        if "champions league" not in blob:
            return False
    if "league cup" in blob and not any(k in blob for k in ("we league","japan","jpn","nadeshiko")):
        return False
    return any(k in blob for k in IMPORTANT_WOMEN_MARKERS)

@lru_cache(maxsize=32)
def calendar_for_date(date_str):
    """Calendario rápido: una sola fuente (FotMob). Hombres todas las ligas; mujeres solo élite."""
    target=datetime.strptime(date_str,'%Y-%m-%d').date()
    days=[(target+timedelta(days=off)).strftime('%Y%m%d') for off in (-1,0,1)]
    rows=[]; seen=set()
    payloads=[]
    from concurrent.futures import ThreadPoolExecutor, as_completed
    def _pull(ds):
        data=_fotmob_get(f"{FOTMOB}/matches?date={ds}", timeout=8)
        try:
            for lg in data.get("leagues") or []:
                for ev in lg.get("matches") or []:
                    for side in ("home","away"):
                        t=ev.get(side) or {}
                        tid=t.get("id"); nm=t.get("name") or t.get("longName")
                        if tid and nm:
                            _FOTMOB_INDEX[_logo_key(nm)]=int(tid)
                            _FOTMOB_INDEX[_norm_team_name(nm)]=int(tid)
        except Exception:
            pass
        return data
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs=[pool.submit(_pull, ds) for ds in days]
        for fut in as_completed(futs):
            try:
                payloads.append(fut.result())
            except Exception:
                pass
    for data in payloads:
        for lg in data.get("leagues") or []:
            lname=lg.get("name") or "Fútbol"
            ccode=str(lg.get("ccode") or "")
            pais=CCODE_NAME.get(ccode.upper(), ccode or "Internacional")
            if ccode.upper()=="COL" and any(k in lname.lower() for k in ("primera a","clausura","apertura","betplay")):
                lname="Liga BetPlay Dimayor"; pais="Colombia"
            low_lg=lname.lower()
            if ccode.upper() in ("IND","IN","INDIA") or any(k in low_lg for k in ("indian super","i-league","mumbai super","bangalore super","bengaluru super","mdfa","bdfa","ksfa")):
                pais="India"
                if any(k in low_lg for k in ("mumbai super","mdfa")):
                    lname="Mumbai Super Division"
                elif any(k in low_lg for k in ("bangalore super","bengaluru super","bdfa","ksfa")):
                    lname="Bangalore Super Division"
                elif "indian super" in low_lg or low_lg=="isl":
                    lname="Indian Super League"
                elif "i-league" in low_lg or "i league" in low_lg:
                    lname="I-League"
            if ccode.upper() in ("JPN","JAP","JAPAN") and _is_women_competition(lname) and any(k in lname.lower() for k in ("cup","copa","we league")):
                lname="Copa de la Liga (F)"; pais="Japón"
            if ccode.upper() in ("URU","UY","URUGUAY") or "uruguay" in lname.lower():
                if any(k in lname.lower() for k in ("copa","cup","auf uruguay")) and "liga auf" not in lname.lower() and "clausura" not in lname.lower() and "apertura" not in lname.lower():
                    lname="Copa AUF Uruguay"; pais="Uruguay"
            sample_names=[]
            for ev0 in (lg.get("matches") or [])[:3]:
                sample_names.append(((ev0.get("home") or {}).get("name") or ""))
                sample_names.append(((ev0.get("away") or {}).get("name") or ""))
            women=_is_women_competition(lname, *sample_names)
            women_top=bool(women and _is_important_women(lname, *sample_names))
            for ev in lg.get("matches") or []:
                st=ev.get("status") or {}
                if st.get("cancelled"):
                    continue
                utc=st.get("utcTime")
                dt_pe=_peru_datetime_from_iso(utc)
                if not dt_pe or dt_pe.strftime("%Y-%m-%d")!=date_str:
                    continue
                home=ev.get("home") or {}; away=ev.get("away") or {}
                hn=home.get("name") or home.get("longName")
                an=away.get("name") or away.get("longName")
                if not hn or not an:
                    continue
                eid=str(ev.get("id") or "")
                pair="|".join(sorted([_norm_team_name(hn), _norm_team_name(an)]))
                if eid in seen or pair in seen:
                    continue
                seen.add(eid); seen.add(pair)
                hora=dt_pe.strftime("%H:%M")
                live=bool(st.get("started") and not st.get("finished"))
                estado="EN VIVO" if live else hora
                row_women=women or _is_women_competition(lname, hn, an)
                row_top=women_top or (row_women and _is_important_women(lname, hn, an))
                rows.append({
                    "n":0,"event_id":ev.get("id"),"pais":pais,"liga":lname,
                    "hora":hora,"local":hn,"visita":an,"estado":estado,
                    "timestamp":utc,"fecha":date_str,
                    "logo_l":fotmob_logo_url(home.get("id")),
                    "logo_v":fotmob_logo_url(away.get("id")),
                    "top_flight":is_top_flight_league(lname, pais) or row_top,
                    "is_cup":is_cup_competition(lname, pais),
                    "sexo":"F" if row_women else "M",
                    "gender":"female" if row_women else "male",
                    "women_top":bool(row_top) if row_women else False,
                })
    # WE League Cup / Copa de la Liga (F) Japón: FotMob a veces la lista solo como "Cup".
    JPN_WE_CUP = {
        "2026-09-23":[
            ("00:00","NTV Beleza (F)","Albirex Niigata (F)"),
            ("00:00","Nojima (F)","Chifure AS Elfen Saitama (F)"),
            ("02:00","JEF United Ichihara Chiba (F)","INAC Leonessa (F)"),
            ("02:00","Omiya Ardija (F)","Mynavi Sendai (F)"),
            ("02:00","Urawa Red Diamonds (F)","AC Nagano Parceiro (F)"),
            ("04:00","Cerezo Osaka (F)","Sanfrecce Hiroshima (F)"),
        ],
    }
    have=set("|".join(sorted([_norm_team_name(r.get("local")), _norm_team_name(r.get("visita"))])) for r in rows)
    for home,away in [(a,b) for a,b,_ in []]:
        pass
    for hora,home,away in JPN_WE_CUP.get(date_str) or []:
        pair="|".join(sorted([_norm_team_name(home), _norm_team_name(away)]))
        if pair in have:
            # si ya está como "Cup", renombrar
            for r in rows:
                if "|".join(sorted([_norm_team_name(r.get("local")), _norm_team_name(r.get("visita"))]))==pair:
                    r["liga"]="Copa de la Liga (F)"; r["pais"]="Japón"
                    r["sexo"]="F"; r["gender"]="female"; r["women_top"]=True
            continue
        have.add(pair)
        rows.append({
            "n":0,"event_id":None,"pais":"Japón","liga":"Copa de la Liga (F)",
            "hora":hora,"local":home,"visita":away,"estado":hora,
            "timestamp":None,"fecha":date_str,
            "logo_l":logo_for(home),"logo_v":logo_for(away),
            "top_flight":True,"is_cup":True,"sexo":"F","gender":"female","women_top":True,
        })
    INDIA_STATE={
        "2026-09-23":[
            ("03:30","Mumbai Super Division","CFCI U19","Kopana FC"),
            ("00:30","Bangalore Super Division","Parikrma FC","FC Real Bengaluru"),
            ("03:00","Bangalore Super Division","Bangalore Dream United","Stride FC"),
            ("05:30","Bangalore Super Division","Bengaluru FC","FC Agniputhra"),
        ],
        "2026-09-24":[
            ("00:30","Bangalore Super Division","HAL SC","Kickstart FC"),
            ("03:00","Bangalore Super Division","South United FC","ASC FC"),
            ("05:30","Bangalore Super Division","Rebels FC","Roots FC"),
        ],
        "2026-09-25":[
            ("00:30","Bangalore Super Division","Bangalore City FC","Kodagu FC"),
            ("03:00","Bangalore Super Division","SC Bengaluru","Technico FF"),
            ("05:30","Bangalore Super Division","United Stars FC","MEG & Centre FC"),
        ],
    }
    COPA_AUF={
        "2026-09-23":[
            ("13:30","Boston River","Fénix"),
            ("13:30","Liverpool FC","Colón"),
            ("18:00","Cerro","Deportivo Maldonado"),
            ("18:00","Montevideo Wanderers","Cerrito"),
        ],
        "2026-09-24":[
            ("13:30","Danubio","Peñarol"),
            ("13:30","Montevideo City Torque","Atenas"),
        ],
        "2026-09-30":[
            ("13:30","Lito","Durazno"),
            ("17:00","Defensor Sporting","Plaza Colonia"),
            ("17:00","Cerro Largo","Rentistas"),
        ],
        "2026-09-26":[
            ("15:30","Nacional","Rincón"),
        ],
        "2026-09-27":[
            ("13:00","Ferro Carril","Real Montevideo"),
            ("16:00","Gladiador","Sportivo Barracas"),
        ],
    }
    for hora,home,away in COPA_AUF.get(date_str) or []:
        pair="|".join(sorted([_norm_team_name(home), _norm_team_name(away)]))
        if pair in have:
            for r in rows:
                if "|".join(sorted([_norm_team_name(r.get("local")), _norm_team_name(r.get("visita"))]))==pair:
                    r["liga"]="Copa AUF Uruguay"; r["pais"]="Uruguay"; r["is_cup"]=True
            continue
        have.add(pair)
        hid=resolve_fotmob_id(home, away); aid=resolve_fotmob_id(away, home)
        rows.append({
            "n":0,"event_id":None,"pais":"Uruguay","liga":"Copa AUF Uruguay",
            "hora":hora,"local":home,"visita":away,"estado":hora,
            "timestamp":None,"fecha":date_str,
            "logo_l":fotmob_logo_url(hid) or logo_for(home, hid),
            "logo_v":fotmob_logo_url(aid) or logo_for(away, aid),
            "top_flight":True,"is_cup":True,"sexo":"M","gender":"male","women_top":False,
        })
    for hora,liga,home,away in INDIA_STATE.get(date_str) or []:
        pair="|".join(sorted([_norm_team_name(home), _norm_team_name(away)]))
        if pair in have:
            continue
        have.add(pair)
        rows.append({
            "n":0,"event_id":None,"pais":"India","liga":liga,
            "hora":hora,"local":home,"visita":away,"estado":hora,
            "timestamp":None,"fecha":date_str,
            "logo_l":logo_for(home),"logo_v":logo_for(away),
            "top_flight":False,"is_cup":False,"sexo":"M","gender":"male","women_top":False,
        })
    rows.sort(key=lambda x:(x.get("hora") or "99:99", x.get("pais") or "", x.get("local") or ""))
    for i,row in enumerate(rows,1):
        row["n"]=i
    return rows

# Partidos del día 22/09/2026 cargados en el listado de la aplicación.
# La fuente de calendario entrega horas en UTC; este bloque de respaldo ya está
# convertido a hora de Perú (America/Lima, UTC-5). Las estadísticas históricas
# se consultan en tiempo real.
TODAY_22_09 = [{"n": 1, "pais": "Argelia", "liga": "Ligue 1", "hora": "12:00", "local": "US Biskra", "visita": "Saoura", "estado": "12:00"}, {"n": 2, "pais": "Argelia", "liga": "Ligue 1", "hora": "14:00", "local": "MC Alger", "visita": "MC Oran", "estado": "14:00"}, {"n": 3, "pais": "Argentina", "liga": "Primera División", "hora": "", "local": "Lanús", "visita": "Estudiantes", "estado": "Resultado publicado / hora no indicada"}, {"n": 4, "pais": "Austria", "liga": "Regionalliga", "hora": "12:30", "local": "Traiskirchen", "visita": "Krems / Rehberg", "estado": "12:30"}, {"n": 5, "pais": "Austria", "liga": "Regionalliga", "hora": "12:45", "local": "Austria Klagenfurt", "visita": "Donau Klagenfurt", "estado": "12:45"}, {"n": 6, "pais": "Brasil", "liga": "Serie B", "hora": "", "local": "Cuiabá", "visita": "Náutico FC", "estado": "Resultado publicado / hora no indicada"}, {"n": 7, "pais": "Brasil", "liga": "Série B", "hora": "17:30", "local": "Criciúma", "visita": "Operário-PR", "estado": "17:30"}, {"n": 7, "pais": "Chile", "liga": "Copa Chile", "hora": "16:00", "local": "Puerto Montt", "visita": "Ñublense", "estado": "16:00"}, {"n": 8, "pais": "Chile", "liga": "Copa Chile", "hora": "18:30", "local": "Audax Italiano", "visita": "Colo Colo", "estado": "18:30"}, {"n": 9, "pais": "Chile", "liga": "Copa Chile", "hora": "18:30", "local": "Cobreloa", "visita": "Coquimbo Unido", "estado": "18:30"}, {"n": 10, "pais": "Colombia", "liga": "Primera A", "hora": "18:00", "local": "Independiente Medellín", "visita": "Jaguares de Córdoba FC", "estado": "18:00"}, {"n": 11, "pais": "Colombia", "liga": "Primera B", "hora": "", "local": "Real Cartagena", "visita": "Envigado FC", "estado": "Resultado publicado / hora no indicada"}, {"n": 12, "pais": "Colombia", "liga": "Primera B", "hora": "16:00", "local": "Atlético FC", "visita": "Tigres FC", "estado": "16:00"}, {"n": 13, "pais": "Colombia", "liga": "Primera B", "hora": "16:00", "local": "Ind. Yumbo", "visita": "Internacional Palmira", "estado": "16:00"}, {"n": 14, "pais": "Colombia", "liga": "Primera B", "hora": "16:00", "local": "Real Santander", "visita": "Orsomarso", "estado": "16:00"}, {"n": 15, "pais": "Ecuador", "liga": "Liga Pro", "hora": "", "local": "Barcelona", "visita": "Independiente Valle", "estado": "Aplazado"}, {"n": 16, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Alloa Athletic", "visita": "Hibernian II", "estado": "13:45"}, {"n": 17, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Banks O' Dee", "visita": "Aberdeen II", "estado": "13:45"}, {"n": 18, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Berwick Rangers", "visita": "Stranraer", "estado": "13:45"}, {"n": 19, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Bonnyrigg Rose", "visita": "Airdrieonians", "estado": "13:45"}, {"n": 20, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Clachnacuddin", "visita": "Ross County", "estado": "13:45"}, {"n": 21, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Clyde", "visita": "Rangers II", "estado": "13:45"}, {"n": 22, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Clydebank", "visita": "St. Mirren II", "estado": "13:45"}, {"n": 23, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Dumbarton", "visita": "Kilmarnock II", "estado": "13:45"}, {"n": 24, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "East Kilbride", "visita": "Celtic II", "estado": "13:45"}, {"n": 25, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Edinburgh City", "visita": "Dundee United II", "estado": "13:45"}, {"n": 26, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Elgin City", "visita": "Dundee II", "estado": "13:45"}, {"n": 27, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Forfar Athletic", "visita": "Peterhead", "estado": "13:45"}, {"n": 28, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Formartine United", "visita": "Montrose", "estado": "13:45"}, {"n": 29, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Fraserburgh", "visita": "Cove Rangers", "estado": "13:45"}, {"n": 30, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Gala Fairydean Rovers", "visita": "Spartans", "estado": "13:45"}, {"n": 31, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Kelty Hearts", "visita": "Hearts II", "estado": "13:45"}, {"n": 32, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Queen of the South", "visita": "Annan Athletic", "estado": "13:45"}, {"n": 33, "pais": "Escocia", "liga": "Challenge Cup", "hora": "13:45", "local": "Stirling Albion", "visita": "Cumbernauld Colts", "estado": "13:45"}, {"n": 34, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "ACV", "visita": "Hoogeveen", "estado": "13:00"}, {"n": 35, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "Eemdijk", "visita": "RBC", "estado": "13:00"}, {"n": 36, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "EVV", "visita": "Halsteren", "estado": "13:00"}, {"n": 37, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "Excelsior '31", "visita": "AFC '34", "estado": "13:00"}, {"n": 38, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "Groene Ster", "visita": "AFC", "estado": "13:00"}, {"n": 39, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "GVVV", "visita": "DVS '33", "estado": "13:00"}, {"n": 40, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "HHC", "visita": "Barendrecht", "estado": "13:00"}, {"n": 41, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "Koninklijke HFC", "visita": "DOVO", "estado": "13:00"}, {"n": 42, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "Kloetinge", "visita": "Achilles Veen", "estado": "13:00"}, {"n": 43, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "Noordwijk", "visita": "Frisia", "estado": "13:00"}, {"n": 44, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "Rijnvogels", "visita": "VVSB", "estado": "13:00"}, {"n": 45, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "RKAV Volendam", "visita": "Spakenburg", "estado": "13:00"}, {"n": 46, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "Sportlust '46", "visita": "Excelsior Maassluis", "estado": "13:00"}, {"n": 47, "pais": "Holanda", "liga": "KNVB Beker", "hora": "13:00", "local": "Staphorst", "visita": "Genemuiden", "estado": "13:00"}, {"n": 48, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Accrington Stanley", "visita": "Sunderland U21", "estado": "13:00"}, {"n": 49, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Barnsley", "visita": "Leeds United U21", "estado": "13:00"}, {"n": 50, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Wigan Athletic", "visita": "Blackpool", "estado": "13:00"}, {"n": 51, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Burton Albion", "visita": "Nottingham Forest U21", "estado": "13:00"}, {"n": 52, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Gillingham", "visita": "Cambridge United", "estado": "13:00"}, {"n": 53, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Cheltenham Town", "visita": "Exeter City", "estado": "13:00"}, {"n": 54, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Chesterfield", "visita": "Port Vale", "estado": "13:00"}, {"n": 55, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Peterborough United", "visita": "Colchester United", "estado": "13:00"}, {"n": 56, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Milton Keynes Dons", "visita": "Crawley Town", "estado": "13:00"}, {"n": 57, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Crewe Alexandra", "visita": "Aston Villa U21", "estado": "13:00"}, {"n": 58, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Oldham Athletic", "visita": "Fleetwood Town", "estado": "13:00"}, {"n": 59, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Notts County", "visita": "Grimsby Town", "estado": "13:00"}, {"n": 60, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Leicester City", "visita": "Fulham U21", "estado": "13:00"}, {"n": 61, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Luton Town", "visita": "Ipswich Town U21", "estado": "13:00"}, {"n": 62, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Swindon Town", "visita": "Newport County", "estado": "13:00"}, {"n": 63, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Plymouth Argyle", "visita": "Crystal Palace U21", "estado": "13:00"}, {"n": 64, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Rochdale", "visita": "Liverpool U21", "estado": "13:00"}, {"n": 65, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "York City", "visita": "Rotherham United", "estado": "13:00"}, {"n": 66, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Salford City", "visita": "Sheffield Wednesday", "estado": "13:00"}, {"n": 67, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Tranmere Rovers", "visita": "Shrewsbury Town", "estado": "13:00"}, {"n": 68, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:00", "local": "Walsall", "visita": "Stevenage", "estado": "13:00"}, {"n": 69, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:30", "local": "Bradford City", "visita": "Newcastle United U21", "estado": "13:30"}, {"n": 70, "pais": "Inglaterra", "liga": "EFL Trophy", "hora": "13:30", "local": "Bromley", "visita": "Brentford U21", "estado": "13:30"}, {"n": 71, "pais": "Inglaterra", "liga": "FA Cup", "hora": "13:45", "local": "Chippenham Town", "visita": "Yate Town", "estado": "13:45"}, {"n": 72, "pais": "Rumania", "liga": "Liga II", "hora": "09:30", "local": "Dumbrăviţa", "visita": "CSM Reşiţa", "estado": "09:30"}, {"n": 73, "pais": "Rumania", "liga": "Liga II", "hora": "12:00", "local": "ASA Târgu Mureş", "visita": "CS Dinamo București", "estado": "12:00"}, {"n": 74, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "CSM Adjud", "visita": "USV Iaşi", "estado": "09:00"}, {"n": 75, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "ARO Campulung", "visita": "Băicoi", "estado": "09:00"}, {"n": 76, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Carpati Covasna", "visita": "ACS Mediaş 2022", "estado": "09:00"}, {"n": 77, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Tricolorul Breaza", "visita": "Corona Braşov", "estado": "09:00"}, {"n": 78, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Berca", "visita": "Progresul Draganesti", "estado": "09:00"}, {"n": 79, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Plopeni", "visita": "Blejoi", "estado": "09:00"}, {"n": 80, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Pucioasa", "visita": "Flacăra Moreni", "estado": "09:00"}, {"n": 81, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Păuleşti", "visita": "Tunari", "estado": "09:00"}, {"n": 82, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Adunatii-Copaceni", "visita": "Oxigen Bucuresti", "estado": "09:00"}, {"n": 83, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Dinamo Bucureşti II", "visita": "Cetatea Turnu Magurele", "estado": "09:00"}, {"n": 84, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "FCSB II", "visita": "Alexandria", "estado": "09:00"}, {"n": 85, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Voluntari II", "visita": "LPS HD Clinceni", "estado": "09:00"}, {"n": 86, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Academica Balș", "visita": "Jiul Petroşani", "estado": "09:00"}, {"n": 87, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Filiaşi", "visita": "CS U Craiova 2", "estado": "09:00"}, {"n": 88, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Minerul Lupeni", "visita": "CSM Targu Jiu", "estado": "09:00"}, {"n": 89, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Pausesti-Otasau", "visita": "Oltul Curtişoara", "estado": "09:00"}, {"n": 90, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "CSM Deva", "visita": "Santana", "estado": "09:00"}, {"n": 91, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "ACS Poli Timisoara II", "visita": "Blaj", "estado": "09:00"}, {"n": 92, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Progresul Pecica", "visita": "Univ. Alba Iulia", "estado": "09:00"}, {"n": 93, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Unirea Alba Iulia", "visita": "Timişul Şag", "estado": "09:00"}, {"n": 94, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Lotus Băile Felix", "visita": "Crişul Sântandrei", "estado": "09:00"}, {"n": 95, "pais": "Rumania", "liga": "Liga III", "hora": "09:00", "local": "Sănătatea Cluj", "visita": "Minaur Baia Mare", "estado": "09:00"}]

# Vista principal: solo partidos que todavía se jugarán hoy.
TODAY_22_09 = [m for m in TODAY_22_09 if not str(m.get("estado","")).lower().startswith(("resultado publicado","aplazado"))]
for m in TODAY_22_09:
    # El listado manual del 22/09 ya está expresado en hora peruana.
    # No volver a convertirlo: la conversión UTC→Perú se hizo al cargar
    # el respaldo y los calendarios dinámicos usan timestamp/ISO.
    m["fecha"] = "2026-09-22"
    if m.get("hora") and str(m.get("estado", "")).strip() == str(m.get("hora", "")).strip():
        m["estado"] = m["hora"]

for m in TODAY_22_09:
    m["top_flight"] = is_top_flight_league(m.get("liga"),m.get("pais"))
    m["logo_l"] = logo_for(m.get("local",""))
    m["logo_v"] = logo_for(m.get("visita",""))


def upcoming_dates(n=8):
    today=now_pe().date()
    return [(today+timedelta(days=i)).strftime("%Y-%m-%d") for i in range(0,n)]
NEXT_DAYS = upcoming_dates(8)

def calendar_range(dates):
    out={}
    from concurrent.futures import ThreadPoolExecutor, as_completed
    dates=[d for d in dates if d]
    if not dates:
        return out
    with ThreadPoolExecutor(max_workers=min(6,len(dates))) as pool:
        futs={pool.submit(calendar_for_date,d):d for d in dates}
        for fut in as_completed(futs):
            d=futs[fut]
            try:
                out[d]=fut.result() or []
            except Exception:
                out[d]=[]
    return out

def _warm_upcoming_calendars():
    today=now_pe().date()
    for i in range(0,3):
        try:
            calendar_for_date((today+timedelta(days=i)).strftime("%Y-%m-%d"))
        except Exception:
            pass

def is_womens_match(m):
    vals=[]
    for k in ("liga","league","competition","name","pais","country","sexo","gender","home","away","local","visita"):
        if isinstance(m, dict) and m.get(k) is not None:
            vals.append(str(m.get(k)))
    s=" ".join(vals).lower()
    markers=("women","women's","womens","femen","femin","fem.","female","nwsl",
              "women super league","champions league women","uefa women's")
    if any(x in s for x in markers):
        return True
    for k in ("sexo","gender"):
        v=str(m.get(k,"")).strip().lower() if isinstance(m,dict) else ""
        if v in ("f","female","women","w","femenino","femenina"):
            return True
    return False



# ---------------- Contexto competitivo / Prematch ----------------
@lru_cache(maxsize=64)
def _scheduled_events_day(date_str):
    """Calendario de SofaScore para una fecha; se usa solo para contexto prematch."""
    return _json_get(f"{SOFASCORE}/sport/football/scheduled-events/{date_str}", timeout=10).get("events", []) or []

def _find_scheduled_event(home_name, away_name, date_str="2026-09-22"):
    hn=_norm_team_name(home_name); an=_norm_team_name(away_name)
    try:
        for ev in _scheduled_events_day(date_str):
            ht=_norm_team_name((ev.get("homeTeam") or {}).get("name"))
            at=_norm_team_name((ev.get("awayTeam") or {}).get("name"))
            if ((hn in ht or ht in hn) and (an in at or at in an)):
                return ev
    except Exception:
        pass
    return None

def _standings_context(team_id, tournament_id, season_id):
    if not team_id or not tournament_id or not season_id:
        return None
    try:
        data=_json_get(f"{SOFASCORE}/unique-tournament/{tournament_id}/season/{season_id}/standings/overall", timeout=10)
        rows=[]
        for group in data.get("standings",[]) or []:
            rows.extend(group.get("rows",[]) or [])
        row=next((r for r in rows if (r.get("team") or {}).get("id")==team_id),None)
        if not row:
            return None
        return {
            "position":row.get("position"),"points":row.get("points"),"played":row.get("matches"),
            "wins":row.get("wins"),"draws":row.get("draws"),"losses":row.get("losses"),
            "goal_diff":row.get("scoresFor",0)-row.get("scoresAgainst",0),
            "goals_for":row.get("scoresFor"),"goals_against":row.get("scoresAgainst"),
            "table_rows":rows
        }
    except Exception:
        return None

def _competition_objective(stand, rows):
    """Resume el contexto de tabla sin afirmar una necesidad psicológica."""
    if not stand or not rows:
        return {"label":"Tabla no disponible","detail":"No se pudo verificar la clasificación actual."}
    pos=stand.get("position")
    pts=stand.get("points")
    if pos is None or pts is None:
        return {"label":"Tabla disponible parcialmente","detail":"La posición o los puntos no fueron entregados por la fuente."}
    ordered=sorted([r for r in rows if r.get("position") is not None], key=lambda r:r.get("position"))
    above=next((r for r in ordered if r.get("position")==pos-1),None)
    below=next((r for r in ordered if r.get("position")==pos+1),None)
    gaps=[]
    if above and above.get("points") is not None: gaps.append(f"a {max(0, above['points']-pts)} pts del puesto {pos-1}")
    if below and below.get("points") is not None: gaps.append(f"{max(0, pts-below['points'])} pts sobre el puesto {pos+1}")
    # Indicador puramente descriptivo: cuanto más cerca esté de otro puesto,
    # más sensible es un partido a cambios de posición.
    nearest=min([abs(above['points']-pts) for above in [above] if above and above.get('points') is not None] +
                [abs(pts-below['points']) for below in [below] if below and below.get('points') is not None] + [99])
    pressure="Alta" if nearest<=2 else ("Media" if nearest<=4 else "Baja")
    return {"label":f"{pos}.º · {pts} pts", "detail":" · ".join(gaps) or "Sin puesto contiguo verificable", "pressure":pressure}

def _offensive_profile(summary):
    m=summary.get("metrics",{}) if summary else {}
    vals=[]
    for k,w in (("goals_for",3.0),("shots",1.0),("sot",1.6)):
        v=(m.get(k) or {}).get("average")
        if v is not None: vals.append(v*w)
    if not vals: return {"label":"No disponible","detail":"No hay suficientes métricas ofensivas verificables."}
    score=sum(vals)/len(vals)
    label="Muy ofensivo" if score>=9 else ("Ofensivo" if score>=6 else ("Equilibrado" if score>=3.5 else "Conservador"))
    detail=f"Goles {((m.get('goals_for') or {}).get('average') or 0):.2f} · remates {((m.get('shots') or {}).get('average') or 0):.2f} · al arco {((m.get('sot') or {}).get('average') or 0):.2f}"
    return {"label":label,"detail":detail}

def _card_tension(home_summary, away_summary, h2h=None):
    vals=[]
    for s in (home_summary,away_summary):
        v=(s.get("metrics",{}).get("yellow") or {}).get("average")
        if v is not None: vals.append(v)
    if h2h and h2h.get("available"):
        for r in h2h.get("matches",[]):
            # H2H endpoint no trae tarjetas por defecto; no se inventan.
            pass
    if len(vals)<2:
        return {"label":"No verificable","detail":"No hay datos suficientes de amarillas de ambos equipos."}
    avg=sum(vals)/len(vals)
    label="Alta" if avg>=4.5 else ("Media" if avg>=3.0 else "Baja")
    return {"label":label,"detail":f"Promedio reciente de amarillas: {avg:.2f} por equipo/partido", "avg":round(avg,2)}

def _fotmob_table_for_team(name):
    """Clasificación real del equipo desde la ficha FotMob."""
    tid=fotmob_team_id(name)
    data=_fotmob_get(f"{FOTMOB}/teams?id={tid}", timeout=16)
    blocks=data.get("table") or (data.get("overview") or {}).get("table") or []
    if isinstance(blocks, dict):
        blocks=[blocks]
    for block in blocks:
        payload=(block or {}).get("data") or {}
        table=((payload.get("table") or {}).get("all") or payload.get("all") or [])
        if not table:
            for sub in payload.get("tables") or []:
                table=((sub.get("table") or {}).get("all") or [])
                if table:
                    payload=dict(payload)
                    payload["leagueName"]=sub.get("leagueName") or payload.get("leagueName")
                    payload["legend"]=sub.get("legend") or payload.get("legend")
                    break
        if not table:
            continue
        if any(k in str(payload.get("leagueName") or "").lower() for k in ("primera a","clausura","apertura")) and str(payload.get("ccode") or "").upper() in ("COL","COLOMBIA"):
            payload["leagueName"]="Liga BetPlay Dimayor"
        legend=payload.get("legend") or []
        row=next((r for r in table if int(r.get("id") or 0)==int(tid) or _names_compatible(name, r.get("name") or "")), None)
        if not row:
            continue
        pos=int(row.get("idx") or 0)
        zone="Media tabla"
        zone_key="mid"
        for lg in legend:
            indices=lg.get("indices") or []
            # FotMob usa índice 0-based sobre la tabla ordenada.
            if pos-1 in indices or row.get("qualColor") and lg.get("color")==row.get("qualColor"):
                title=str(lg.get("title") or lg.get("tKey") or "")
                low=title.lower()
                if "releg" in low:
                    zone,zone_key="Descenso","relegation"
                elif "promot" in low and "qual" in low:
                    zone,zone_key="Puestos de repechaje / G4-G6","playoff"
                elif "promot" in low or "title" in low or "champion" in low:
                    zone,zone_key="Ascenso / título","promotion"
                elif "europ" in low or "champions" in low:
                    zone,zone_key="Zona Europa","europe"
                else:
                    zone,zone_key=title or zone, low or zone_key
                break
        gf,ga=None,None
        scores=str(row.get("scoresStr") or "")
        if "-" in scores:
            try:
                gf,ga=map(int, scores.replace(" ","").split("-")[:2])
            except Exception:
                pass
        return {
            "team":row.get("name") or name,
            "league":payload.get("leagueName") or "—",
            "position":pos,
            "played":row.get("played"),
            "wins":row.get("wins"),"draws":row.get("draws"),"losses":row.get("losses"),
            "points":row.get("pts"),
            "goal_diff":row.get("goalConDiff"),
            "goals_for":gf,"goals_against":ga,
            "zone":zone,"zone_key":zone_key,
            "table":table,"legend":legend,
        }
    return None

def _need_from_table(stand):
    if not stand:
        return {"label":"No verificable","detail":"Sin tabla actual.","level":"Baja"}
    pos=stand.get("position"); pts=stand.get("points"); zone_key=stand.get("zone_key") or "mid"
    table=stand.get("table") or []
    detail=f"{pos}.º · {pts} pts · {stand.get('wins',0)}G-{stand.get('draws',0)}E-{stand.get('losses',0)}P"
    neighbors=[]
    for r in table:
        if r.get("idx") in (pos-1, pos+1) and r.get("pts") is not None and pts is not None:
            neighbors.append(abs(int(r["pts"])-int(pts)))
    gap=min(neighbors) if neighbors else 99
    if zone_key=="relegation":
        return {"label":"Alta · permanencia","detail":detail+f" · zona de descenso · {stand.get('zone')}","level":"Alta"}
    if zone_key=="promotion":
        return {"label":"Alta · ascenso/título","detail":detail+f" · {stand.get('zone')}","level":"Alta"}
    if zone_key in ("playoff","europe"):
        level="Alta" if gap<=3 else "Media"
        return {"label":f"{level} · {stand.get('zone')}","detail":detail+f" · {gap if gap<99 else '—'} pts al vecino","level":level}
    # Media tabla: la necesidad sube si está a 3 pts o menos de un corte.
    cuts=[]
    for lg in stand.get("legend") or []:
        for idx in lg.get("indices") or []:
            if 0<=idx<len(table) and table[idx].get("pts") is not None and pts is not None:
                cuts.append(abs(int(table[idx]["pts"])-int(pts)))
    nearest=min(cuts) if cuts else gap
    if nearest<=3:
        return {"label":"Media · corte cerca","detail":detail+f" · a {nearest} pts de un corte de tabla","level":"Media"}
    return {"label":"Baja · media tabla","detail":detail,"level":"Baja"}

def _intensity_profile(home_need, away_need, home_sum, away_sum, h2h, competition=""):
    score=20
    reasons=[]
    for need,tag in ((home_need,"local"),(away_need,"visita")):
        if need.get("level")=="Alta":
            score+=28; reasons.append(f"necesidad alta {tag}")
        elif need.get("level")=="Media":
            score+=14; reasons.append(f"necesidad media {tag}")
    yellows=[]
    fouls=[]
    for sm in (home_sum, away_sum):
        y=((sm.get("metrics") or {}).get("yellow") or {}).get("average")
        f=((sm.get("metrics") or {}).get("fouls") or {}).get("average")
        if y is not None: yellows.append(y)
        if f is not None: fouls.append(f)
    if yellows:
        yavg=sum(yellows)/len(yellows)
        if yavg>=3.2:
            score+=16; reasons.append(f"amarillas altas ({yavg:.1f}/eq)")
        elif yavg>=2.2:
            score+=8; reasons.append(f"amarillas medias ({yavg:.1f}/eq)")
    if fouls:
        favg=sum(fouls)/len(fouls)
        if favg>=14:
            score+=10; reasons.append(f"faltas altas ({favg:.1f})")
    if h2h and h2h.get("available") and (h2h.get("matches") or []):
        n=len(h2h["matches"])
        draws=sum(1 for r in h2h["matches"] if r.get("home_goals")==r.get("away_goals"))
        if draws/n<=0.25 and n>=4:
            score+=6; reasons.append("H2H poco empatado")
        cards=[]
        for r in h2h["matches"]:
            pair=(r.get("stats") or {}).get("yellow") or {}
            if pair.get("home") is not None and pair.get("away") is not None:
                cards.append(pair["home"]+pair["away"])
        if cards and sum(cards)/len(cards)>=4.5:
            score+=10; reasons.append("H2H con muchas amarillas")
    low=str(competition or "").lower()
    if any(k in low for k in ("copa","cup","pokal","knockout","final","derbi","clásico","clasico")):
        score+=12; reasons.append("copa o cruce de eliminación")
    score=max(0,min(100,score))
    if score>=75:
        label,tone="MUY CALIENTE","hot"
    elif score>=55:
        label,tone="CALIENTE","warm"
    elif score>=35:
        label,tone="NORMAL","normal"
    else:
        label,tone="FRÍO","cold"
    return {"score":score,"label":label,"tone":tone,"detail":" · ".join(reasons) or "Sin señales extra de roce"}


@lru_cache(maxsize=16)
def fotmob_league_table(league_id=274):
    data=_fotmob_get(f"{FOTMOB}/leagues?id={int(league_id)}", timeout=14)
    details=data.get("details") or {}
    blocks=data.get("table") or []
    if isinstance(blocks, dict):
        blocks=[blocks]
    rows=[]
    league="Liga BetPlay Dimayor" if int(league_id)==274 else (details.get("name") or "Liga")
    season=details.get("selectedSeason") or ""
    legend=[]
    for block in blocks:
        payload=(block or {}).get("data") or {}
        legend=payload.get("legend") or legend
        table=((payload.get("table") or {}).get("all") or [])
        if not table:
            for sub in payload.get("tables") or []:
                table=((sub.get("table") or {}).get("all") or [])
                if table:
                    if int(league_id)==274:
                        league="Liga BetPlay Dimayor"
                    else:
                        league=sub.get("leagueName") or league
                    legend=sub.get("legend") or legend
                    break
        for r in table:
            gf=ga=None
            sc=str(r.get("scoresStr") or "")
            if "-" in sc:
                try:
                    gf,ga=map(int, sc.replace(" ","").split("-")[:2])
                except Exception:
                    pass
            rows.append({
                "position":r.get("idx"),"team":r.get("name"),"id":r.get("id"),
                "played":r.get("played"),"wins":r.get("wins"),"draws":r.get("draws"),
                "losses":r.get("losses"),"gf":gf,"ga":ga,"gd":r.get("goalConDiff"),
                "points":r.get("pts"),"logo":fotmob_logo_url(r.get("id")),
                "zone":"Clasifica a cuadrangulares" if (r.get("idx") or 99)<=8 else "Fuera del 8",
            })
    return {"league":league,"season":season,"legend":legend,"rows":rows,"available":bool(rows)}


def _metric_avg(summary, key):
    try:
        v=((summary or {}).get("metrics") or {}).get(key) or {}
        return v.get("average")
    except Exception:
        return None

def _form_line(summary):
    rec=((summary or {}).get("records") or {}).get("all") or {}
    w,d,l=rec.get("wins",0),rec.get("draws",0),rec.get("losses",0)
    n=w+d+l
    pts=3*w+d
    rate=(100*w/n) if n else None
    return {"wins":w,"draws":d,"losses":l,"played":n,"points":pts,
            "win_rate":round(rate,1) if rate is not None else None,
            "ppg":round(pts/n,2) if n else None,
            "label":f"{w}G-{d}E-{l}P"}

def _style_profile(summary):
    poss=_metric_avg(summary,"possession")
    shots=_metric_avg(summary,"shots")
    sot=_metric_avg(summary,"sot")
    att=_metric_avg(summary,"dangerousattacks") or _metric_avg(summary,"attacks")
    gf=_metric_avg(summary,"goals_for")
    ga=_metric_avg(summary,"goals_against")
    bits=[]
    style="Sin estilo verificable"
    detail="Faltan posesión o remates en la fuente."
    if poss is None and shots is None and att is None:
        return {"label":style,"detail":detail,"possession":None,"shots":shots,"kind":"na"}
    if poss is not None:
        bits.append(f"posesión {poss:.1f}%")
    if shots is not None:
        bits.append(f"remates {shots:.1f}")
    if sot is not None:
        bits.append(f"al arco {sot:.1f}")
    if att is not None:
        bits.append(f"ataques {att:.1f}")
    # Clasificación solo con umbrales de dato real.
    if poss is not None and poss>=56:
        if shots is not None and shots>=12:
            style,kind="Posesión ofensiva / combinativo","posesion"
        else:
            style,kind="Control y posesión","posesion"
    elif poss is not None and poss<=44:
        if (gf or 0)>=1.2:
            style,kind="Contragolpe","contra"
        else:
            style,kind="Bloque bajo / transición defensiva","contra"
    elif shots is not None and shots>=13 and (poss is None or 46<=poss<=55):
        style,kind="Transición vertical","transicion"
    elif shots is not None and shots<=8:
        style,kind="Juego directo / pocos remates","directo"
    else:
        style,kind="Equilibrado / mixto","mixto"
    detail=" · ".join(bits) if bits else detail
    return {"label":style,"detail":detail,"possession":poss,"shots":shots,"kind":kind}

def _level_compare(home_name, away_name, home_table, away_table, hs, aws):
    hf=_form_line(hs); af=_form_line(aws)
    notes=[]
    home_pts=away_pts=None
    if home_table and home_table.get("position") is not None:
        notes.append(f"{home_name} {home_table.get('position')}º · {home_table.get('points')} pts")
        home_pts=home_table.get("points")
    if away_table and away_table.get("position") is not None:
        notes.append(f"{away_name} {away_table.get('position')}º · {away_table.get('points')} pts")
        away_pts=away_table.get("points")
    winner=None
    why=[]
    same_table=bool(home_table and away_table and home_table.get("league")==away_table.get("league"))
    if same_table and home_table.get("position") and away_table.get("position"):
        if home_table["position"]<away_table["position"]:
            winner=home_name; why.append("mejor puesto en la misma tabla")
        elif away_table["position"]<home_table["position"]:
            winner=away_name; why.append("mejor puesto en la misma tabla")
    if hf.get("ppg") is not None and af.get("ppg") is not None:
        if hf["ppg"]>af["ppg"]+0.15:
            if winner is None: winner=home_name
            why.append(f"mejor racha reciente ({hf['label']} · {hf['ppg']} pts/pj)")
        elif af["ppg"]>hf["ppg"]+0.15:
            if winner is None: winner=away_name
            why.append(f"mejor racha reciente ({af['label']} · {af['ppg']} pts/pj)")
        else:
            why.append("rendimiento reciente parejo")
    hgf=_metric_avg(hs,"goals_for"); agf=_metric_avg(aws,"goals_for")
    if winner is None:
        label="Nivel parejo o no comparable"
    else:
        label=f"Mayor nivel / rendimiento: {winner}"
    return {
        "label":label,
        "winner":winner,
        "detail":" · ".join(why+notes) or "Sin tabla comparable; se usa solo la racha de los últimos partidos.",
        "home_form":hf,"away_form":af,
        "home_gf":hgf,"away_gf":agf,
    }

def prematch_context(home_name, away_name, date_str="2026-09-22"):
    from concurrent.futures import ThreadPoolExecutor
    result={"available":False,"competition":"—","home":{"name":home_name},"away":{"name":away_name},"tension":{},"builder":{}}
    with ThreadPoolExecutor(max_workers=5) as pool:
        f_hs=pool.submit(summarize_team, home_name, RECENT_LIMIT)
        f_as=pool.submit(summarize_team, away_name, RECENT_LIMIT)
        f_h2h=pool.submit(h2h_summary, home_name, away_name)
        f_ht=pool.submit(_fotmob_table_for_team, home_name)
        f_at=pool.submit(_fotmob_table_for_team, away_name)
        hs=f_hs.result(); aws=f_as.result(); h2h=f_h2h.result()
        try: home_table=f_ht.result()
        except Exception: home_table=None
        try: away_table=f_at.result()
        except Exception: away_table=None
    result["competition"]=(home_table or {}).get("league") or (away_table or {}).get("league") or "—"
    home_need=_need_from_table(home_table)
    away_need=_need_from_table(away_table)
    result["home"]={
        "name":home_name,
        "standings":home_table,
        "table_context":{
            "label":(f"{home_table['position']}.º · {home_table['points']} pts" if home_table else "Tabla no disponible"),
            "detail":home_need.get("detail") or "",
            "pressure":home_need.get("level") or "Baja",
            "zone":(home_table or {}).get("zone") or "—",
        },
        "need":home_need,
        "offensive":_offensive_profile(hs),
    }
    result["away"]={
        "name":away_name,
        "standings":away_table,
        "table_context":{
            "label":(f"{away_table['position']}.º · {away_table['points']} pts" if away_table else "Tabla no disponible"),
            "detail":away_need.get("detail") or "",
            "pressure":away_need.get("level") or "Baja",
            "zone":(away_table or {}).get("zone") or "—",
        },
        "need":away_need,
        "offensive":_offensive_profile(aws),
    }
    result["tension"]=_card_tension(hs,aws,h2h)
    result["intensity"]=_intensity_profile(home_need,away_need,hs,aws,h2h,result["competition"])
    always=[]
    for item in (h2h or {}).get("universal") or []:
        if isinstance(item, dict):
            always.append({"label":item.get("label"),"hits":item.get("hits"),"sample":item.get("sample"),"rate":100})
        elif item:
            always.append({"label":str(item),"hits":h2h.get("sample"),"sample":h2h.get("sample"),"rate":100})
    # Picks posibles: frecuencia alta en últimos 20, que no estén ya en el 100% H2H.
    always_labels={x["label"].lower() for x in always}
    possible=[]
    def consider(label, hits, sample, detail):
        if not sample or hits is None: return
        rate=round(100*hits/sample)
        if rate<62 or sample<6: return
        if any(label.lower() in a or a in label.lower() for a in always_labels):
            return
        possible.append({"label":label,"hits":hits,"sample":sample,"rate":rate,"detail":detail})
    hr=_team_rows(hs); ar=_team_rows(aws); both=hr+ar
    h,n=_rate(both, lambda r:(r["goals_for"]+r["goals_against"])>=2)
    consider("Más de 1.5 goles",h,n,f"{h}/{n} en los últimos partidos de ambos")
    h,n=_rate(both, lambda r:(r["goals_for"]+r["goals_against"])<=3)
    consider("Menos de 3.5 goles",h,n,f"{h}/{n} en los últimos partidos de ambos")
    h,n=_rate(both, lambda r:r["goals_for"]>=1 and r["goals_against"]>=1)
    consider("Ambos marcan",h,n,f"{h}/{n} recientes combinados")
    for team,rows,tag in ((home_name,hr,"Local"),(away_name,ar,"Visitante")):
        h,n=_rate(rows, lambda r:r["goals_for"]>=1)
        consider(f"{tag} marca (más 0.5)",h,n,f"{h}/{n} del {team}")
        vals=[r.get("corners") for r in rows if r.get("corners") is not None]
        if vals:
            consider(f"{tag} más 3.5 córners", sum(1 for v in vals if v>=4), len(vals), f"{team}: córners recientes")
        vals=[r.get("shots") for r in rows if r.get("shots") is not None]
        if vals:
            consider(f"{tag} más 9.5 remates", sum(1 for v in vals if v>=10), len(vals), f"{team}: remates recientes")
        vals=[r.get("yellow") for r in rows if r.get("yellow") is not None]
        if vals:
            consider(f"{tag} más 1.5 amarillas", sum(1 for v in vals if v>=2), len(vals), f"{team}: amarillas recientes")
    possible.sort(key=lambda x:(-x["rate"],-x["sample"]))
    # Builder: SIEMPRE (H2H 100%) + posibles (≥62%) + combo conservador.
    combo=[x["label"] for x in always[:3]]
    for x in possible:
        if x["rate"]>=78 and x["label"] not in combo and len(combo)<5:
            combo.append(x["label"])
    result["builder"]={
        "always":always,
        "possible":possible[:10],
        "combo":combo,
        "h2h_sample":(h2h or {}).get("sample") or 0,
        "form_home":len(hr),"form_away":len(ar),
    }
    # Si el cruce es colombiano, adjuntar tabla BetPlay completa.
    comp=" ".join([
        str(result.get("competition") or ""),
        str((home_table or {}).get("league") or ""),
        str((away_table or {}).get("league") or ""),
    ]).lower()
    if any(k in comp for k in ("betplay","dimayor","primera a","clausura","apertura")) or any(
        _norm_team_name(x) in ("independiente medellin","america de cali","millonarios","atletico nacional","santa fe","deportivo cali","junior","tolima")
        for x in (home_name, away_name)
    ):
        try:
            result["league_table"]=fotmob_league_table(274)
            result["competition"]="Liga BetPlay Dimayor"
        except Exception:
            result["league_table"]={"available":False}
    result["home"]["style"]=_style_profile(hs)
    result["away"]["style"]=_style_profile(aws)
    result["home"]["form"]=_form_line(hs)
    result["away"]["form"]=_form_line(aws)
    result["home"]["possession"]=_metric_avg(hs,"possession")
    result["away"]["possession"]=_metric_avg(aws,"possession")
    result["reading"]=_level_compare(home_name,away_name,home_table,away_table,hs,aws)
    result["available"]=True
    return result

# ---------------- Enfrentamientos directos (H2H) ----------------
def _h2h_matches(home_name, away_name, max_pages=12):
    """Busca H2H verificables y recupera las estadísticas disponibles de cada choque."""
    hid=sofascore_team_id(home_name); aid=sofascore_team_id(away_name)
    wanted={hid,aid}; seen=set(); rows=[]
    for team_id in (hid, aid):
        for page in range(max_pages):
            data=_json_get(f"{SOFASCORE}/team/{team_id}/events/last/{page}")
            evs=data.get("events",[]) or []
            if not evs: break
            for ev in evs:
                ht=ev.get("homeTeam",{}) or {}; at=ev.get("awayTeam",{}) or {}
                if {ht.get("id"),at.get("id")} != wanted: continue
                hs=ev.get("homeScore",{}).get("current"); vs=ev.get("awayScore",{}).get("current")
                if hs is None or vs is None or ev.get("status",{}).get("type")!="finished": continue
                eid=ev.get("id")
                if eid in seen: continue
                seen.add(eid)
                rows.append({"event_id":eid,"date":ev.get("startTimestamp"),"home":ht.get("name","—"),"away":at.get("name","—"),
                             "home_id":ht.get("id"),"away_id":at.get("id"),"home_goals":hs,"away_goals":vs,"home_goals_1t":(ev.get("homeScore") or {}).get("period1"),"away_goals_1t":(ev.get("awayScore") or {}).get("period1"),
                             "competition":(ev.get("tournament") or {}).get("name") or (ev.get("uniqueTournament") or {}).get("name") or "—"})
            if len(evs)<1: break
    rows.sort(key=lambda x:x.get("date") or 0, reverse=True)

    # Estadísticas de los últimos H2H: se consulta en paralelo para no bloquear la UI.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs={pool.submit(event_stat_values,r["event_id"]):r["event_id"] for r in rows[:20]}
        statmap={}
        for fut in as_completed(futs):
            eid=futs[fut]
            try: statmap[eid]=fut.result()
            except Exception: statmap[eid]={}
    stat_keys=("shots","sot","corners","yellow","red","possession","fouls","throwins","tackles","offsides","freekicks","goalkicks","saves","crosses","blockedshots","woodwork","attacks","dangerousattacks")
    for r in rows[:20]:
        sv=statmap.get(r["event_id"],{})
        pair_fields={}
        for key in stat_keys:
            pair=sv.get(key)
            if pair is not None:
                pair_fields[key]={"home":pair[0],"away":pair[1]}
        r["stats"]=pair_fields
    return rows

def _h2h_metric(rows, key, side=None):
    vals=[]
    for r in rows:
        pair=(r.get("stats") or {}).get(key)
        if not pair: continue
        v=pair.get(side) if side else None
        if v is not None: vals.append(v)
    return _metric(vals)

def _ts_from_iso(value):
    if not value: return None
    try: return int(datetime.fromisoformat(str(value).replace("Z","+00:00")).timestamp())
    except Exception: return None

def _h2h_matches_espn(home_name, away_name, days_back=730, limit=20):
    """Fallback H2H usando los partidos recientes que ESPN expone por fecha.
    Se usa cuando SofaScore bloquea la consulta; solo acepta partidos finalizados
    donde ambos equipos coinciden por nombre normalizado.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import datetime as _dt
    home_norm=_norm_team_name(home_name); away_norm=_norm_team_name(away_name)
    today=_dt.datetime.now(_dt.timezone.utc).date()
    dates=[today-_dt.timedelta(days=i) for i in range(days_back)]
    found={}
    def fetch(day):
        ds=day.strftime("%Y%m%d"); last=None
        for base in (ESPN_SITE, ESPN_SITE_FALLBACK):
            try:
                return _espn_get(f"{base}/all/scoreboard?dates={ds}",timeout=12)
            except Exception as e: last=e
        raise last or RuntimeError("ESPN no entregó el marcador")
    for pos in range(0,len(dates),14):
        batch=dates[pos:pos+14]
        with ThreadPoolExecutor(max_workers=min(8,len(batch))) as pool:
            futs={pool.submit(fetch,d):d for d in batch}
            for fut in as_completed(futs):
                try: data=fut.result()
                except Exception: continue
                for ev in data.get("events",[]) or []:
                    comp=(ev.get("competitions") or [{}])[0]
                    status=comp.get("status") or ev.get("status") or {}
                    st=status.get("type") or {}
                    if not (st.get("completed") or st.get("state")=="post" or st.get("name","").startswith("STATUS_FINAL")): continue
                    cs=comp.get("competitors") or []
                    if len(cs)<2: continue
                    a=cs[0].get("team") or {}; b=cs[1].get("team") or {}
                    an=_norm_team_name(a.get("displayName") or a.get("name")); bn=_norm_team_name(b.get("displayName") or b.get("name"))
                    if not ((home_norm in an or an in home_norm) and (away_norm in bn or bn in away_norm)) and not ((home_norm in bn or bn in home_norm) and (away_norm in an or an in away_norm)): continue
                    home_c=next((c for c in cs if c.get("homeAway")=="home"),cs[0]); away_c=next((c for c in cs if c.get("homeAway")=="away"),cs[1])
                    hs=_num(home_c.get("score")); aws=_num(away_c.get("score"))
                    if hs is None or aws is None: continue
                    eid=str(ev.get("id"));
                    if eid in found: continue
                    found[eid]={"event_id":eid,"date":_ts_from_iso(ev.get("date")),"home":(home_c.get("team") or {}).get("displayName","—"),"away":(away_c.get("team") or {}).get("displayName","—"),"home_goals":hs,"away_goals":aws,"home_goals_1t":None,"away_goals_1t":None,"competition":((comp.get("league") or {}).get("name") or (ev.get("league") or {}).get("name") or "—"),"_espn":True}
        if len(found)>=limit: break
    rows=sorted(found.values(),key=lambda x:x.get("date") or 0,reverse=True)[:limit]
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs={pool.submit(espn_event_stats,r["event_id"]):r["event_id"] for r in rows}
        statmap={}
        for fut in as_completed(futs):
            try: statmap[futs[fut]]=fut.result()
            except Exception: statmap[futs[fut]]={}
    keys=("shots","sot","corners","yellow","red","possession","fouls","throwins","tackles","offsides","freekicks","goalkicks","saves","crosses","blockedshots","woodwork","attacks","dangerousattacks")
    for r in rows:
        sv=statmap.get(r["event_id"],{}); hp=sv.get("home") or {}; ap=sv.get("away") or {}; r["stats"]={}
        for k in keys:
            if hp.get(k) is not None or ap.get(k) is not None: r["stats"][k]={"home":hp.get(k),"away":ap.get(k)}
    return rows

# H2H comprobados desde páginas históricas públicas cuando los feeds automáticos
# de SofaScore/ESPN no están disponibles. Se usan únicamente como respaldo y
# no sustituyen una consulta exitosa de la fuente principal.
KNOWN_H2H = {
    frozenset((_norm_team_name("PSG F"), _norm_team_name("Real Madrid F"))): [
        {"date": int(datetime(2025,10,16,tzinfo=timezone.utc).timestamp()), "home":"PSG F", "away":"Real Madrid F", "home_goals":1, "away_goals":2, "home_goals_1t":0, "away_goals_1t":2, "competition":"UEFA Women's Champions League", "stats":{}},
        {"date": int(datetime(2022,12,16,tzinfo=timezone.utc).timestamp()), "home":"PSG F", "away":"Real Madrid F", "home_goals":2, "away_goals":1, "home_goals_1t":1, "away_goals_1t":0, "competition":"UEFA Women's Champions League", "stats":{}},
        {"date": int(datetime(2022,10,26,tzinfo=timezone.utc).timestamp()), "home":"Real Madrid F", "away":"PSG F", "home_goals":0, "away_goals":0, "home_goals_1t":0, "away_goals_1t":0, "competition":"UEFA Women's Champions League", "stats":{}},
        {"date": int(datetime(2021,11,18,tzinfo=timezone.utc).timestamp()), "home":"Real Madrid F", "away":"PSG F", "home_goals":0, "away_goals":2, "home_goals_1t":0, "away_goals_1t":1, "competition":"UEFA Women's Champions League", "stats":{}},
        {"date": int(datetime(2021,11,9,tzinfo=timezone.utc).timestamp()), "home":"PSG F", "away":"Real Madrid F", "home_goals":4, "away_goals":0, "home_goals_1t":2, "away_goals_1t":0, "competition":"UEFA Women's Champions League", "stats":{}},
    ]
}

def _known_h2h_matches(home_name, away_name):
    keys={frozenset((_norm_team_name(home_name), _norm_team_name(away_name)))}
    aliases={
        _norm_team_name("PSG F"): {"psg f","psg women","paris saint germain women","paris saint germain f","paris saint germain"},
        _norm_team_name("Real Madrid F"): {"real madrid f","real madrid women","real madrid femenino","real madrid"},
    }
    def canonical(n):
        n=_norm_team_name(n)
        for canon, vals in aliases.items():
            if n==canon or n in vals: return canon
        return n
    keys.add(frozenset((canonical(home_name), canonical(away_name))))
    rows=None
    for key in keys:
        rows=KNOWN_H2H.get(key)
        if rows: break
    if not rows:
        return []
    # Devuelve copias para no contaminar el caché global con estadísticas añadidas.
    return [dict(r, stats=dict(r.get("stats") or {})) for r in rows]

def _iso_to_ts(value):
    if value is None:
        return None
    if isinstance(value,(int,float)):
        return int(value)
    try:
        raw=str(value).strip()
        if raw.endswith("Z"):
            raw=raw[:-1]+"+00:00"
        return int(datetime.fromisoformat(raw).timestamp())
    except Exception:
        return None

def _fotmob_team_fixture_events(team_id):
    data=_fotmob_get(f"{FOTMOB}/teams?id={team_id}", timeout=16)
    return (((data.get("fixtures") or {}).get("allFixtures") or {}).get("fixtures") or [])

def _fotmob_pair_match_ids(hid, aid):
    ids=[]
    seen=set()
    for tid in (hid, aid):
        try:
            events=_fotmob_team_fixture_events(tid)
        except Exception:
            events=[]
        for ev in events:
            home=ev.get("home") or {}; away=ev.get("away") or {}
            pair={int(home.get("id") or 0), int(away.get("id") or 0)}
            if {int(hid), int(aid)} != pair:
                continue
            eid=ev.get("id")
            if eid and eid not in seen:
                seen.add(eid); ids.append(eid)
    # También el calendario de hoy y días próximos/pasados cercanos.
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    today=_dt.now(_tz.utc).date()
    for delta in range(-3,4):
        ds=(today+_td(days=delta)).strftime("%Y%m%d")
        try:
            data=_fotmob_get(f"{FOTMOB}/matches?date={ds}", timeout=10)
        except Exception:
            continue
        for lg in data.get("leagues") or []:
            for ev in lg.get("matches") or []:
                home=ev.get("home") or {}; away=ev.get("away") or {}
                pair={int(home.get("id") or 0), int(away.get("id") or 0)}
                if {int(hid), int(aid)}==pair and ev.get("id") and ev.get("id") not in seen:
                    seen.add(ev.get("id")); ids.append(ev.get("id"))
    return ids

def _h2h_matches_fotmob(home_name, away_name):
    hid=fotmob_team_id(home_name); aid=fotmob_team_id(away_name)
    seed_ids=_fotmob_pair_match_ids(hid, aid)
    meetings=[]
    seen=set()
    # Un partido entre ambos (vivo, programado o ya jugado) trae el bloque H2H completo.
    for sid in seed_ids[:4]:
        try:
            data=_fotmob_get(f"{FOTMOB}/matchDetails?matchId={sid}", timeout=14)
        except Exception:
            continue
        block=((data.get("content") or {}).get("h2h") or {}).get("matches") or []
        for m in block:
            url=str(m.get("matchUrl") or "")
            eid=None
            if "#" in url:
                tail=url.split("#")[-1]
                if tail.isdigit():
                    eid=int(tail)
            st=m.get("status") or {}
            if not st.get("finished") or st.get("cancelled"):
                continue
            score=str(st.get("scoreStr") or "").replace(" ","").split("-")
            if len(score)<2:
                continue
            try:
                hg=int(float(score[0])); ag=int(float(score[1]))
            except Exception:
                continue
            key=eid or (st.get("utcTime"), (m.get("home") or {}).get("id"), (m.get("away") or {}).get("id"))
            if key in seen:
                continue
            seen.add(key)
            meetings.append({
                "event_id":eid,
                "date":_iso_to_ts(st.get("utcTime") or (m.get("time") or {}).get("utcTime")),
                "home":(m.get("home") or {}).get("name") or "—",
                "away":(m.get("away") or {}).get("name") or "—",
                "home_id":(m.get("home") or {}).get("id"),
                "away_id":(m.get("away") or {}).get("id"),
                "home_goals":hg,"away_goals":ag,
                "home_goals_1t":None,"away_goals_1t":None,
                "competition":(m.get("league") or {}).get("name") or "—",
                "stats":{},
            })
    # Si el bloque H2H no vino, usar los fixtures cruzados ya finalizados.
    if not meetings:
        for tid in (hid, aid):
            try:
                events=_fotmob_team_fixture_events(tid)
            except Exception:
                events=[]
            for ev in events:
                st=ev.get("status") or {}
                if not st.get("finished") or st.get("cancelled"):
                    continue
                home=ev.get("home") or {}; away=ev.get("away") or {}
                if {int(home.get("id") or 0), int(away.get("id") or 0)} != {int(hid), int(aid)}:
                    continue
                eid=ev.get("id")
                if eid in seen:
                    continue
                seen.add(eid)
                meetings.append({
                    "event_id":eid,"date":_iso_to_ts(st.get("utcTime")),
                    "home":home.get("name") or "—","away":away.get("name") or "—",
                    "home_id":home.get("id"),"away_id":away.get("id"),
                    "home_goals":home.get("score"),"away_goals":away.get("score"),
                    "home_goals_1t":None,"away_goals_1t":None,
                    "competition":(ev.get("tournament") or {}).get("name") or "—","stats":{},
                })
    meetings.sort(key=lambda r:r.get("date") or 0, reverse=True)
    # Estadísticas reales de cada duelo.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    need=[r for r in meetings if r.get("event_id")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs={pool.submit(_fotmob_pair_stats, r["event_id"]): r["event_id"] for r in need}
        statmap={}
        for fut in as_completed(futs):
            eid=futs[fut]
            try:
                statmap[eid]=fut.result()
            except Exception:
                statmap[eid]={}
    keys=("shots","sot","corners","yellow","red","possession","fouls","throwins","tackles","offsides","freekicks","goalkicks","saves","crosses","blockedshots","woodwork","attacks","dangerousattacks")
    for r in meetings:
        det=statmap.get(r.get("event_id")) or {}
        if det.get("home_ht") is not None:
            r["home_goals_1t"]=det.get("home_ht")
        if det.get("away_ht") is not None:
            r["away_goals_1t"]=det.get("away_ht")
        pair=det.get("stats") or {}
        stats={}
        for k in keys:
            pr=pair.get(k)
            if pr:
                stats[k]={"home":pr[0],"away":pr[1]}
        if det.get("red_home") is not None or det.get("red_away") is not None:
            stats.setdefault("red",{"home":det.get("red_home"),"away":det.get("red_away")})
        r["stats"]=stats
    return meetings

def h2h_summary(home_name, away_name):
    # Un 403/bloqueo de una fuente NO significa que no existan H2H.
    # Cada proveedor se intenta de forma independiente y se cae al siguiente.
    rows=[]
    source=None

    try:
        rows=_h2h_matches_fotmob(home_name,away_name) or []
        if rows:
            source="FotMob"
    except Exception:
        rows=[]

    if not rows:
        try:
            rows=_h2h_matches(home_name,away_name) or []
            if rows:
                source="SofaScore"
        except Exception:
            rows=[]

    if not rows:
        try:
            rows=_h2h_matches_espn(home_name,away_name) or []
            if rows:
                source="ESPN"
        except Exception:
            rows=[]

    if not rows:
        try:
            rows=_known_h2h_matches(home_name,away_name) or []
            if rows:
                source="Histórico H2H comprobado (respaldo)"
        except Exception:
            rows=[]

    n=len(rows)
    if n==0:
        return {"available":False,"has_previous":False,"matches":[],"reason":"NO HAN TENIDO DUELOS ANTERIORES."}

    tests=[
        ("Al menos 1 gol",lambda r:(r["home_goals"]+r["away_goals"])>=1),
        ("Más de 0.5 goles",lambda r:(r["home_goals"]+r["away_goals"])>=1),
        ("Más de 1.5 goles",lambda r:(r["home_goals"]+r["away_goals"])>=2),
        ("Menos de 2.5 goles",lambda r:(r["home_goals"]+r["away_goals"])<=2),
        ("Menos de 3.5 goles",lambda r:(r["home_goals"]+r["away_goals"])<=3),
        ("Menos de 4.5 goles",lambda r:(r["home_goals"]+r["away_goals"])<=4),
        ("Ambos marcan",lambda r:r["home_goals"]>0 and r["away_goals"]>0),
        ("No ambos marcan",lambda r:r["home_goals"]==0 or r["away_goals"]==0),
        ("Sin empate",lambda r:r["home_goals"]!=r["away_goals"]),
        ("Empate",lambda r:r["home_goals"]==r["away_goals"]),
    ]
    scored=[]; universal=[]
    for label,fn in tests:
        hits=sum(1 for r in rows if fn(r)); scored.append((hits/n,hits,label))
        if hits==n: universal.append({"label":label,"hits":hits,"sample":n})
    # Patrones de volumen: solo si el dato existe en TODOS los duelos.
    stat_always=[
        ("Al menos 1 córner en el duelo","corners",lambda h,a:(h or 0)+(a or 0)>=1),
        ("Al menos 5 córners en el duelo","corners",lambda h,a:(h or 0)+(a or 0)>=5),
        ("Al menos 1 amarilla en el duelo","yellow",lambda h,a:(h or 0)+(a or 0)>=1),
        ("Sin rojas","red",lambda h,a:(h or 0)+(a or 0)==0),
        ("Al menos 10 remates en el duelo","shots",lambda h,a:(h or 0)+(a or 0)>=10),
        ("Al menos 5 remates al arco en el duelo","sot",lambda h,a:(h or 0)+(a or 0)>=5),
        ("Al menos 1 falta en el duelo","fouls",lambda h,a:(h or 0)+(a or 0)>=1),
    ]
    for label,key,fn in stat_always:
        pairs=[]
        ok=True
        for r in rows:
            pair=(r.get("stats") or {}).get(key)
            if not pair or pair.get("home") is None or pair.get("away") is None:
                ok=False; break
            pairs.append((pair["home"],pair["away"]))
        if ok and pairs and all(fn(h,a) for h,a in pairs):
            universal.append({"label":label,"hits":len(pairs),"sample":len(pairs)})
    scored.sort(key=lambda z:(z[0],z[1]),reverse=True); rate,hits,label=scored[0]
    stat_keys=[("Goles","goals"),("Córners","corners"),("Faltas","fouls"),("Amarillas","yellow"),("Rojas","red"),("Tackles","tackles"),("Saques de banda","throwins"),("Offsides","offsides"),("Remates","shots"),("Remates al arco","sot")]
    totals={"goals":_metric([r["home_goals"]+r["away_goals"] for r in rows])}
    for label2,key in stat_keys:
        if key == "goals": continue
        vals=[]
        for r in rows:
            pair=(r.get("stats") or {}).get(key)
            if pair and pair.get("home") is not None and pair.get("away") is not None:
                vals.append(pair["home"]+pair["away"])
        totals[key]=_metric(vals)
    home_avg={key:_h2h_metric(rows,key,"home") for _,key in stat_keys}
    away_avg={key:_h2h_metric(rows,key,"away") for _,key in stat_keys}
    return {"available":True,"has_previous":True,"matches":rows[:20],"sample":n,"pattern":label,"hits":hits,"rate":round(rate*100),"always":bool(universal),
            "universal":universal,"totals":totals,"source":source,"home_stats":home_avg,"away_stats":away_avg,
            "stats_sample":sum(1 for r in rows if r.get("stats"))}

# ---------------- Calendario femenino dinámico ----------------
# La consulta anterior dependía de un único endpoint de SofaScore y, cuando
# ese endpoint devolvía 0/403/timeout, la interfaz terminaba mostrando 0.
# Ahora usamos dos fuentes en paralelo y una reserva oficial de UWCL para
# evitar que una fuente caída deje la sección femenina vacía.

# Horas YA en Perú (UTC−5). 18:45/21:00 CEST = 11:45/14:00 PE.
UWCL_FALLBACK_2026_09_22 = [
    {"event_id":74371784,"pais":"Europa","liga":"UEFA Women's Champions League","hora":"11:45","local":"Bayern München","visita":"Manchester City","estado":"11:45","sexo":"F","gender":"female","timestamp":"2026-09-22T16:45:00Z"},
    {"event_id":74371782,"pais":"Europa","liga":"UEFA Women's Champions League","hora":"11:45","local":"Inter","visita":"Häcken","estado":"11:45","sexo":"F","gender":"female","timestamp":"2026-09-22T16:45:00Z"},
    {"event_id":74371790,"pais":"Europa","liga":"UEFA Women's Champions League","hora":"14:00","local":"Arsenal","visita":"HB Køge","estado":"14:00","sexo":"F","gender":"female","timestamp":"2026-09-22T19:00:00Z"},
    {"event_id":74403624,"pais":"Europa","liga":"UEFA Women's Champions League","hora":"14:00","local":"Juventus","visita":"Benfica","estado":"14:00","sexo":"F","gender":"female","timestamp":"2026-09-22T19:00:00Z"},
    {"event_id":74371786,"pais":"Europa","liga":"UEFA Women's Champions League","hora":"14:00","local":"Real Madrid","visita":"Paris Saint-Germain","estado":"14:00","sexo":"F","gender":"female","timestamp":"2026-09-22T19:00:00Z"},
]
for _m in UWCL_FALLBACK_2026_09_22:
    _m["n"] = 900000 + int(_m["event_id"])
    _m["logo_l"] = logo_for(_m["local"])
    _m["logo_v"] = logo_for(_m["visita"])

@lru_cache(maxsize=32)
def _espn_womens_scoreboard_day(date_str):
    """Una sola consulta ESPN para el día; mucho más rápida que recorrer fechas."""
    last=None
    for base in (ESPN_SITE, ESPN_SITE_FALLBACK):
        try:
            ds=str(date_str).replace("-","")
            return _espn_get(f"{base}/all/scoreboard?dates={ds}", timeout=7)
        except Exception as e:
            last=e
    raise last or RuntimeError("ESPN no entregó el calendario")

def _espn_womens_event(ev):
    comp=(ev.get("competitions") or [{}])[0]
    league=ev.get("league") or comp.get("league") or {}
    season=ev.get("season") or {}
    text=json.dumps({"league":league,"season":season,"event":ev},ensure_ascii=False).lower()
    # ESPN usa nombres como 'Women's Champions League', 'NWSL', 'Liga MX Femenil', etc.
    markers=("women", "women's", "womens", "femen", "nwsl", "liga mx femenil",
             "women super league", "liga f", "division 1 fem", "frauen", "damallsvenskan",
             "arkema", "super league women", "serie a women", "serie a femminile")
    if any(x in text for x in markers):
        return True
    # Algunas respuestas marcan el sexo en la liga/competición.
    gender=str(league.get("gender") or league.get("genderName") or season.get("gender") or "").lower()
    return gender in ("female","women","woman","f")

def _espn_women_matches_for_date(date_str):
    data=_espn_womens_scoreboard_day(date_str)
    out=[]; seen=set()
    for ev in data.get("events",[]) or []:
        if not _espn_womens_event(ev): continue
        comp=(ev.get("competitions") or [{}])[0]
        competitors=comp.get("competitors") or []
        if len(competitors)<2: continue
        home=next((c for c in competitors if c.get("homeAway")=="home"),competitors[0])
        away=next((c for c in competitors if c.get("homeAway")=="away"),competitors[1])
        ht=home.get("team") or {}; at=away.get("team") or {}
        hn=ht.get("displayName") or ht.get("name"); an=at.get("displayName") or at.get("name")
        if not hn or not an: continue
        eid=ev.get("id")
        if eid in seen: continue
        seen.add(eid)
        league=ev.get("league") or comp.get("league") or {}
        category=league.get("country") or league.get("countryName") or "Internacional"
        lname=league.get("name") or league.get("displayName") or "Competición femenina"
        dt_pe=_peru_datetime_from_iso(ev.get("date"))
        out.append({"n":900000+int(eid) if str(eid).isdigit() else 990000+len(out),"event_id":eid,
                    "pais":category,"liga":lname,"hora":dt_pe.strftime("%H:%M") if dt_pe else "","timestamp":ev.get("date"),
                    "fecha":dt_pe.strftime("%Y-%m-%d") if dt_pe else date_str,
                    "local":hn,"visita":an,"estado":(dt_pe.strftime("%H:%M") if dt_pe else ""),"sexo":"F","gender":"female",
                    "logo_l":logo_for(hn),"logo_v":logo_for(an)})
    return out

def _sofa_women_matches_for_date(date_str):
    data=_json_get(f"{SOFASCORE}/sport/football/scheduled-events/{date_str}",timeout=6)
    out=[]; seen=set()
    for ev in data.get("events",[]):
        if not _is_womens_event(ev): continue
        status=(ev.get("status") or {}).get("type")
        if status in ("finished","canceled","postponed"): continue
        home=(ev.get("homeTeam") or {}).get("name"); away=(ev.get("awayTeam") or {}).get("name")
        if not home or not away: continue
        eid=ev.get("id")
        if eid in seen: continue
        seen.add(eid)
        tourn=ev.get("tournament") or ev.get("uniqueTournament") or {}; cat=tourn.get("category") or {}
        dt_pe=_peru_datetime_from_timestamp(ev.get("startTimestamp"))
        if not dt_pe or dt_pe.strftime("%Y-%m-%d") != str(date_str):
            continue
        out.append({"n":900000+int(eid),"event_id":eid,"pais":cat.get("name") or "Internacional",
                    "liga":tourn.get("name") or "Competición femenina","hora":dt_pe.strftime("%H:%M"),"timestamp":ev.get("startTimestamp"),
                    "local":home,"visita":away,"estado":(dt_pe.strftime("%H:%M") if dt_pe else ""),"sexo":"F","gender":"female",
                    "logo_l":logo_for(home),"logo_v":logo_for(away)})
    out.sort(key=lambda x:x.get("timestamp") or 0)
    return out

def _is_womens_text(*parts):
    s=" ".join(str(p or "") for p in parts).lower()
    return any(x in s for x in ("women","womens","femen","female","ladies","nwsl","femenil","femminile","frauen","damer","feminina","femenina","uwcl"))

def _fotmob_women_matches_for_date(date_str):
    """Calendario femenino FotMob, recortado a la fecha de Perú."""
    target=str(date_str)
    # Un día UTC puede caer en dos fechas PE; pedimos el día pedido y el siguiente UTC.
    days=[target.replace("-","")]
    try:
        base=datetime.strptime(target,"%Y-%m-%d").date()
        days.append((base+timedelta(days=1)).strftime("%Y%m%d"))
        days.append((base-timedelta(days=1)).strftime("%Y%m%d"))
    except Exception:
        pass
    out=[]; seen=set()
    for ds in days:
        try:
            data=_fotmob_get(f"{FOTMOB}/matches?date={ds}", timeout=12)
        except Exception:
            continue
        for lg in data.get("leagues") or []:
            lname=lg.get("name") or "Competición femenina"
            if not _is_womens_text(lname, lg.get("ccode")):
                # aún así aceptar partidos con (W) en el nombre
                pass
            for ev in lg.get("matches") or []:
                home=ev.get("home") or {}; away=ev.get("away") or {}
                hn=home.get("name") or home.get("longName"); an=away.get("name") or away.get("longName")
                if not hn or not an: continue
                if not _is_womens_text(lname, hn, an):
                    continue
                st=ev.get("status") or {}
                if st.get("cancelled"):
                    continue
                utc=st.get("utcTime")
                dt_pe=_peru_datetime_from_iso(utc)
                if not dt_pe or dt_pe.strftime("%Y-%m-%d")!=target:
                    continue
                eid=ev.get("id")
                if eid in seen: continue
                seen.add(eid)
                hora=dt_pe.strftime("%H:%M")
                out.append({
                    "n":900000+int(eid) if str(eid).isdigit() else 990000+len(out),
                    "event_id":eid,"pais":lg.get("ccode") or "Internacional","liga":lname,
                    "hora":hora,"timestamp":utc,"fecha":target,
                    "local":hn,"visita":an,"estado":hora,"sexo":"F","gender":"female",
                    "logo_l":logo_for(hn),"logo_v":logo_for(an),
                })
    out.sort(key=lambda x:(x.get("hora") or "99:99", x.get("liga") or "", x.get("local") or ""))
    return out

def women_matches_for_date(date_str):
    """Femenino: FotMob (hora Perú) + ESPN + respaldo solo si falta el partido."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs=[
            pool.submit(_fotmob_women_matches_for_date,date_str),
            pool.submit(_espn_women_matches_for_date,date_str),
            pool.submit(_sofa_women_matches_for_date,date_str),
        ]
        for fut in as_completed(futs):
            try:
                rows=fut.result()
                if rows: results.extend(rows)
            except Exception:
                pass
    # Respaldo UWCL: no pisa un horario ya convertido a Perú.
    if str(date_str)=="2026-09-22":
        have=set()
        for r in results:
            have.add((_norm_team_name(r.get("local")), _norm_team_name(r.get("visita"))))
            have.add((_norm_team_name(r.get("visita")), _norm_team_name(r.get("local"))))
        for fb in UWCL_FALLBACK_2026_09_22:
            key=(_norm_team_name(fb.get("local")), _norm_team_name(fb.get("visita")))
            if key in have:
                continue
            results.append(dict(fb, fecha=date_str))
    def _wk(name):
        n=_norm_team_name(name)
        for tok in ("women","womens","femenino","femenina","feminino","wfc","ladies"):
            n=n.replace(tok," ")
        parts=[t for t in n.split() if t not in {"w","fc","cf","bk","sk"}]
        if not parts:
            return ""
        aliases={"internazionale":"inter","munich":"bayern","munchen":"bayern","haecken":"hacken","koge":"koge","lyonnes":"lyon"}
        head=aliases.get(parts[0], parts[0])
        return head
    unique={}
    def quality(r):
        ts=str(r.get("timestamp") or "")
        liga=str(r.get("liga") or "")
        q=0
        if "T" in ts or str(ts).endswith("Z"): q+=3
        if "fotmob" in liga.lower() or "champions" in liga.lower() or "nwsl" in liga.lower(): q+=1
        if "(W)" in str(r.get("local") or "") or "(W)" in str(r.get("visita") or ""): q+=1
        return q
    for r in results:
        pair="|".join(sorted([_wk(r.get("local")), _wk(r.get("visita"))]))
        key=pair or str(r.get("event_id") or "")
        prev=unique.get(key)
        if prev is None or quality(r)>quality(prev):
            unique[key]=r
    out=list(unique.values())
    out.sort(key=lambda x:(x.get("hora") or "99:99", x.get("liga") or "", x.get("local") or ""))
    return out


# ---------------- PREMATCH APOSTADOR · análisis histórico ----------------
def _bet_leg(label, market, hits, sample, detail, family, min_sample=5):
    if sample is None or sample < min_sample or hits is None:
        return None
    rate=round((hits/sample)*100)
    return {"label":label,"market":market,"hits":hits,"sample":sample,"rate":rate,
            "detail":detail,"family":family}

def _team_rows(summary):
    return list((summary or {}).get("recent") or [])

def _rate(rows, predicate):
    vals=[r for r in rows if r.get("goals_for") is not None and r.get("goals_against") is not None]
    if not vals: return (None,0)
    return (sum(1 for r in vals if predicate(r)), len(vals))

def bettor_prematch(home_name, away_name):
    """Genera un filtro histórico de mercados, sin cuotas ni predicción.
    Las tasas son descriptivas de los últimos 20 partidos disponibles de cada equipo.
    """
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as pool:
        fh=pool.submit(summarize_team,home_name,RECENT_LIMIT)
        fa=pool.submit(summarize_team,away_name,RECENT_LIMIT)
        hs=fh.result(); aws=fa.result()
    hr=_team_rows(hs); ar=_team_rows(aws)
    legs=[]
    # Mercados de goles usando el histórico combinado de ambos equipos.
    combined=hr+ar
    h,n=_rate(combined,lambda r:(r["goals_for"]+r["goals_against"])>=2)
    leg=_bet_leg("Más de 1.5 goles",">1.5 goles",h,n,f"{h}/{n} partidos recientes de ambos equipos cumplieron la línea.","goles")
    if leg: legs.append(leg)
    h,n=_rate(combined,lambda r:(r["goals_for"]+r["goals_against"])<=4)
    leg=_bet_leg("Menos de 4.5 goles","<4.5 goles",h,n,f"{h}/{n} partidos recientes de ambos equipos quedaron en 4 goles o menos.","goles")
    if leg: legs.append(leg)
    # Ambos marcan: tasa de partidos del propio equipo en los que marcó y recibió.
    for team,rows,label in ((home_name,hr,"Local"),(away_name,ar,"Visitante")):
        h,n=_rate(rows,lambda r:r["goals_for"]>=1 and r["goals_against"]>=1)
        leg=_bet_leg(f"BTTS · referencia {label}","Ambos marcan",h,n,f"En {team}: {h}/{n} partidos recientes tuvieron gol de ambos lados.","btts")
        if leg: legs.append(leg)
    # Gol del equipo.
    for team,rows,label in ((home_name,hr,"Local"),(away_name,ar,"Visitante")):
        h,n=_rate(rows,lambda r:r["goals_for"]>=1)
        leg=_bet_leg(f"{label}: más de 0.5 gol",f"{team} +0.5 goles",h,n,f"{h}/{n} partidos recientes del equipo terminaron con al menos un gol propio.","equipo_gol")
        if leg: legs.append(leg)
    # Doble oportunidad según rendimiento en la condición de local/visitante.
    for team,summary,label,key,market in ((home_name,hs,"Local","home","1X"),(away_name,aws,"Visitante","away","X2")):
        rec=((summary or {}).get("records") or {}).get(key) or {}
        sample=sum(rec.get(k,0) for k in ("wins","draws","losses"))
        hits=rec.get("wins",0)+rec.get("draws",0)
        leg=_bet_leg(f"{label}: doble oportunidad",market,hits,sample,
                     f"Registro {rec.get('wins',0)}G–{rec.get('draws',0)}E–{rec.get('losses',0)}P en {sample} partidos de esa condición.","doble_oportunidad",min_sample=3)
        if leg: legs.append(leg)
    # Métricas de volumen: solo se incluyen si el dato existe en la mayoría de partidos.
    metric_specs=[
        ("shots","remate","10+ remates"),
        ("sot","tiro a puerta","3+ tiros a puerta"),
        ("corners","córner","4+ córners"),
        ("yellow","amarilla","2+ amarillas"),
    ]
    for team,rows,label in ((home_name,hr,"Local"),(away_name,ar,"Visitante")):
        for key,word,market_suffix in metric_specs:
            vals=[r.get(key) for r in rows if r.get(key) is not None]
            if len(vals)<5: continue
            threshold={"shots":10,"sot":3,"corners":4,"yellow":2}.get(key,1)
            hits=sum(1 for v in vals if v>=threshold)
            leg=_bet_leg(f"{label}: {market_suffix}",f"{team} {market_suffix}",hits,len(vals),
                         f"{hits}/{len(vals)} partidos con dato alcanzaron el umbral.",f"{key}")
            if leg: legs.append(leg)
    # Deduplicar por mercado y quedarnos con la evidencia histórica más alta.
    best={}
    for leg in legs:
        k=leg["market"]
        if k not in best or (leg["rate"],leg["sample"])>(best[k]["rate"],best[k]["sample"]): best[k]=leg
    legs=list(best.values())
    legs.sort(key=lambda x:(x["rate"],x["sample"]),reverse=True)
    for i,leg in enumerate(legs,1):
        leg["rank"]=i
        leg["tier"]="Fuerte" if leg["rate"]>=80 and leg["sample"]>=7 else ("Media" if leg["rate"]>=65 else "Variable")
    # Constructor de patas: no inventa cuotas ni convierte la tasa histórica en probabilidad futura.
    strong=[x for x in legs if x["rate"]>=75 and x["sample"]>=5]
    conservative=strong[:3]
    balanced=strong[:4]
    return {"available":bool(legs),"home":home_name,"away":away_name,"sample_home":len(hr),"sample_away":len(ar),
            "legs":legs[:12],"tickets":{"conservadora":conservative,"equilibrada":balanced},
            "note":"Ordenado por frecuencia histórica observada. No incluye cuotas, valor esperado ni garantía de acierto; sirve como filtro estadístico prematch."}

FAVICON_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 128 128'>
<circle cx='64' cy='64' r='60' fill='#f7f7f7' stroke='#111' stroke-width='5'/>
<polygon points='64,36 78,46 73,63 55,63 50,46' fill='#111'/>
<path d='M64 36l14 10 18-6-8-18-24 4z' fill='#111'/>
<path d='M78 46l18-6 10 20-15 16-18-8z' fill='#111'/>
<path d='M73 63l15 16-6 18-22-6 2-23z' fill='#111'/>
<path d='M55 63l-2 23-22 6-6-18 15-16z' fill='#111'/>
<path d='M50 46L32 40 22 60l15 16 18-8z' fill='#111'/>
<path d='M50 46l14-10-24-4-8 18z' fill='#111'/>
<circle cx='64' cy='64' r='60' fill='none' stroke='#111' stroke-width='5'/>
</svg>"""

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>Prematch Stats Desk</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg"/>
<link rel="apple-touch-icon" href="/favicon.svg"/>

<style>
:root{--bg:#07101d;--panel:#0c1726;--panel2:#101d2e;--line:#1d3858;--ink:#f5f8fc;--muted:#8fa6c0;--blue:#25a8ff;--blue2:#0d5d9b;--pink:#d94882;--green:#27d39a;--yellow:#ffd35a;--red:#ff5c68}
*{box-sizing:border-box}html{min-height:100%}
body{margin:0;min-height:100vh;overflow-x:hidden;color:var(--ink);font:14px Inter,Segoe UI,system-ui,sans-serif;
background:
  radial-gradient(circle at 50% -18%, #163258 0%, #0b1726 34%, #070d16 62%, #000 100%);
}
body::after{content:"";position:fixed;left:0;right:0;bottom:0;height:42vh;pointer-events:none;z-index:8;
background:linear-gradient(to top,#000 0%,rgba(0,0,0,.88) 28%,rgba(0,0,0,.45) 62%,transparent 100%)}
.wrap,.bar,.watchBox,header,.statsOverlay{position:relative;z-index:10}

header,.bar,.watchBox,.sectionTitle,.statsModalHead,.today thead th,.recent thead th,.compare thead th{position:static !important;top:auto !important}
header{text-align:center;padding:24px 30px;border-bottom:1px solid var(--line);background:#07111f;z-index:11}.brand{font-weight:900;letter-spacing:.6px;font-size:24px}.brand span{color:var(--blue)}
.bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:12px 20px;border-bottom:1px solid var(--line);background:#091321;z-index:11}button,input,select{background:#0d1928;border:1px solid var(--line);color:var(--ink);border-radius:9px;padding:9px 11px}button{cursor:pointer}.chip.on{border-color:var(--blue);box-shadow:0 0 0 1px #25a8ff33}.dateLabel{font-size:12px;color:#7fa7cf;font-weight:800;letter-spacing:.06em;margin-right:2px}.tzBadge{font-size:11px;color:#8bdcff;border:1px solid #1b638c;background:#071d30;border-radius:999px;padding:7px 10px;font-weight:800}.dateSelect,.monthSelect{min-width:132px}.sortToggle{min-width:150px;font-weight:800}input{min-width:220px;flex:1}
.wrap{width:min(97vw,1800px);max-width:1800px;margin:0 auto;padding:16px 18px}.panel{background:linear-gradient(145deg,#0d1928,#0a1421);border:1px solid var(--line);border-radius:13px;padding:12px;margin-bottom:12px}.sub{color:var(--muted);font-size:13px}.today table,.recent table,.compare table{width:100%;border-collapse:collapse}.today table{table-layout:fixed}.today th:nth-child(1){width:4%}.today th:nth-child(2){width:10%}.today th:nth-child(3){width:16%}.today th:nth-child(4){width:7%}.today th:nth-child(5){width:18%}.today th:nth-child(6){width:18%}.today th:nth-child(7){width:13%}.today th:nth-child(8){width:14%}.tableScroll{overflow:hidden}.teamCell{display:flex;align-items:center;gap:7px;min-width:0;overflow:hidden;font-size:14px}.teamCell b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.crestFallback{display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;border-radius:50%;background:#273142;color:#fff;border:1px solid #45516a;flex:0 0 auto}.matchCard.womensMatch{position:relative;border:1px solid rgba(224,145,177,.30);box-shadow:0 0 0 1px rgba(224,145,177,.05),0 3px 12px rgba(224,145,177,.04)}
.cupTag{display:inline-flex;align-items:center;justify-content:center;margin-right:5px;width:23px;height:23px;border-radius:50%;color:#8bdcff;background:rgba(139,220,255,.10);border:1px solid rgba(139,220,255,.38);font-size:12px}.cupTag[title]{cursor:help}.topStar{display:inline-flex;align-items:center;justify-content:center;margin-right:5px;width:23px;height:23px;border-radius:50%;color:#ffd35a;background:rgba(255,211,90,.10);border:1px solid rgba(255,211,90,.38);font-size:13px;box-shadow:0 0 10px rgba(255,211,90,.08)}.topStar[title]{cursor:help}.womensTag{display:inline-flex;align-items:center;gap:4px;margin-left:7px;padding:2px 7px;border-radius:999px;background:rgba(224,145,177,.07);color:#d9a5b8;font-size:10px;font-weight:800;letter-spacing:.3px;text-transform:uppercase}
.miniCrest{width:30px;height:30px;object-fit:contain;flex:0 0 30px}.boxTitle{display:flex;align-items:center;gap:9px}.boxCrest{width:30px;height:30px;object-fit:contain}.today th,.today td,.recent th,.recent td,.compare th,.compare td{padding:8px 7px;border-bottom:1px solid #17304c;text-align:left;font-size:12px}.today th,.recent th,.compare th{color:var(--muted);font-weight:700}.today tr:hover{background:#102137}.load{border-color:#31557b}
.matchHero{display:grid;grid-template-columns:1fr 105px 1fr;align-items:center;border-radius:14px;overflow:hidden;border:1px solid var(--line);background:#091728;margin-bottom:15px}.teamHero{padding:12px;text-align:center}.teamHero.home{background:linear-gradient(115deg,#08284a,#0b1726)}.teamHero.away{background:linear-gradient(245deg,#351127,#0b1726)}.teamHero .crest{width:52px;height:52px;object-fit:contain;display:block;margin:0 auto 8px}.teamHero h2{margin:0;font-size:20px}.kick{text-align:center;padding:18px}.kick b{font-size:18px;display:block}.kick span{display:block;color:var(--muted);margin-top:5px}
.dual{display:grid;grid-template-columns:1fr 1fr;gap:14px}.teamBox{position:relative;background:linear-gradient(145deg,#071728 0%,#081522 52%,#06111e 100%);border:1px solid #183b5e;border-radius:15px;padding:16px 16px 13px;overflow:hidden;box-shadow:0 10px 28px rgba(0,0,0,.20)}.teamBox::before{content:"";position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at 10% 0%,rgba(37,168,255,.08),transparent 34%),radial-gradient(circle at 100% 100%,rgba(84,108,255,.05),transparent 38%)}.teamBox.awayBox{background:linear-gradient(145deg,#071728 0%,#081522 52%,#0c1020 100%)}.teamTitle{position:relative;z-index:1;display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:13px}.teamTitle .boxTitle{min-width:0}.teamTitle b{font-size:18px;letter-spacing:.1px}.teamTitle .teamMeta{display:block;color:#79a4c8;font-size:11px;margin-top:2px}.status{display:inline-flex;align-items:center;gap:6px;flex:0 0 auto;padding:6px 9px;border:1px solid #1b5d8d;border-radius:8px;background:#0a2237;color:#9ed8ff;font-size:10px;font-weight:800;white-space:nowrap}.status::before{content:"◷";font-size:12px}.metrics{position:relative;z-index:1;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-bottom:15px}.metric{position:relative;min-height:98px;background:linear-gradient(145deg,#0b1c2e,#0a1625);border:1px solid #1a4568;border-radius:11px;padding:13px 12px 10px;overflow:hidden;box-shadow:inset 0 1px 0 rgba(255,255,255,.025)}.metric::after{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--metric-accent,#25a8ff)}.metric .metricIcon{display:block;color:var(--metric-accent,#25a8ff);font-size:22px;line-height:1;margin-bottom:9px;filter:drop-shadow(0 0 7px color-mix(in srgb,var(--metric-accent,#25a8ff) 35%,transparent))}.metric .label{font-size:10px;color:#b8c8d8;display:block;line-height:1.15}.metric b{font-size:22px;line-height:1;display:block;margin-top:5px;color:#f3f7fb}.metric small{display:block;color:#7e9ab5;margin-top:5px;font-size:9px}.metric.missing b{color:#71859d;font-size:18px}.metric.shots{--metric-accent:#28a9ff;border-color:rgba(40,169,255,.55)}.metric.sot{--metric-accent:#18d2ad;border-color:rgba(24,210,173,.45)}.metric.goals{--metric-accent:#b86cff;border-color:rgba(184,108,255,.55)}.metric.fouls{--metric-accent:#f0aa38;border-color:rgba(240,170,56,.48)}.metric.corners{--metric-accent:#ec5cae;border-color:rgba(236,92,174,.52)}.metric.yellow{--metric-accent:#ffd35a;border-color:rgba(255,211,90,.55)}.metric.tackles{--metric-accent:#52b6ff;border-color:rgba(82,182,255,.45)}.metric.throwins{--metric-accent:#9b8cff;border-color:rgba(155,140,255,.45)}.metric.offsides{--metric-accent:#ff7b7b;border-color:rgba(255,123,123,.45)}.record{display:none}.rec{padding:9px;background:#0c1827;border:1px solid #193452;border-radius:8px;text-align:center}.rec b{display:block;font-size:17px}.rec span{color:var(--muted);font-size:10px}.metricExtra{grid-column:1/-1;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:0}.recent{position:relative;z-index:1;margin-top:2px}.recentHead{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:0 0 8px}.recent h3,.summary h3,.compare h3{margin:0;font-size:14px}.recentBadge{color:#9fc2df;font-size:10px;font-weight:700}.result{font-weight:900}.win{color:var(--green)}.draw{color:var(--yellow)}.loss{color:var(--red)}.summaryGrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.summary{background:#091524;border:1px solid var(--line);border-radius:13px;padding:13px}.summary ul{margin:8px 0 0;padding-left:19px;color:#cbd8e7}.summary li{margin:6px 0}.compare{margin-top:14px}.sourceNote{position:relative;z-index:1;margin-top:12px;padding:10px 11px;border:1px solid #17466d;border-left:3px solid var(--blue);border-radius:9px;background:linear-gradient(90deg,#091b2c,#091624);color:#a9bfd3;font-size:10px}.missingText{color:#71859d}.footer{color:var(--muted);font-size:11px;padding:8px 2px 22px}
.prematchBox{margin:10px 0 12px;padding:11px;border:1px solid #2a4868;border-radius:11px;background:linear-gradient(135deg,#0b1827,#0a1421)}.prematchHead{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}.prematchHead b{font-size:14px}.prematchGrid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:7px}.pmItem{background:#0d1a29;border:1px solid #1c3855;border-radius:8px;padding:8px;min-width:0}.pmItem .pmLabel{font-size:9px;color:var(--muted);display:block;text-transform:uppercase;letter-spacing:.3px}.pmItem strong{display:block;margin-top:3px;font-size:13px}.pmItem small{display:block;margin-top:2px;color:#7994af;font-size:9px;line-height:1.25}.pmItem.tension{border-color:rgba(255,211,90,.35)}.pmItem.tension strong{color:#ffd35a}.pmItem.pressure strong{color:#8fd4ff}.pmItem.offensive strong{color:#73e5ba}.recentCompact{width:100%;table-layout:fixed;border-collapse:collapse!important;border-spacing:0;overflow:hidden;border:1px solid #102d49;border-radius:9px;background:#071523}.recentCompact th,.recentCompact td{padding:4px 3px!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border-bottom:1px solid #102b44!important;text-align:center}.recentCompact th{background:#0a1b2e;color:#86add0;font-size:7.5px!important;font-weight:800;line-height:1.05}.recentCompact td{font-size:8px!important;color:#d5e1ec;line-height:1.1}.recentCompact tbody tr:last-child td{border-bottom:0!important}.recentCompact tbody tr:hover td{background:#0c2135}.recentCompact th:nth-child(1){width:6%}.recentCompact th:nth-child(2){width:14%}.recentCompact th:nth-child(3){width:18%}.recentCompact th:nth-child(4){width:5%}.recentCompact th:nth-child(5){width:8%}.recentCompact th:nth-child(6){width:7%}.recentCompact th:nth-child(7),.recentCompact th:nth-child(8),.recentCompact th:nth-child(9),.recentCompact th:nth-child(10),.recentCompact th:nth-child(11),.recentCompact th:nth-child(12),.recentCompact th:nth-child(13){width:6%}.recentCompact .compCell{display:block;min-width:0}.recentCompact .compCell i{font-style:normal;color:#7bb8e9;margin-right:2px}.recentCompact .rivalCell span{color:#6f8ba5}.recentCompact .result{text-align:center}.recentCompact .resultPill{display:inline-flex;align-items:center;justify-content:center;min-width:20px;height:18px;padding:0 5px;border-radius:999px;font-weight:900;font-size:8px;background:#12334b;color:#a9c6da}.recentCompact .win .resultPill{background:#0c9b72;color:#d9fff4}.recentCompact .draw .resultPill{background:#d89525;color:#fff4d4}.recentCompact .loss .resultPill{background:#d8377b;color:#ffe1ec}.recentCompact .scoreCell{font-weight:800;text-align:center;color:#dbe8f3}.recentCompact .statCell{text-align:center;font-weight:700;color:#cfe0ef}.noScroll{overflow:visible!important;max-height:none}.recentCompact{min-width:0}@media(max-width:1100px){.prematchGrid{grid-template-columns:1fr 1fr}.metrics{grid-template-columns:repeat(3,1fr)}.recentCompact th{font-size:7px!important}.recentCompact td{font-size:7.5px!important}}@media(max-width:950px){.metrics{grid-template-columns:repeat(3,1fr)}.dual,.summaryGrid,.matchHero{grid-template-columns:1fr}.kick{padding:8px}.bar{top:59px}}@media(max-width:600px){.wrap{padding:8px}.metrics{grid-template-columns:repeat(2,1fr)}.prematchGrid{grid-template-columns:1fr 1fr}.today table,.recent table{min-width:0;font-size:9px}.today th,.today td{padding:6px 4px}.teamCell{min-width:0;gap:5px}.miniCrest{width:24px;height:24px;flex-basis:24px}}
/* FIX18 women's match highlight — rosa sutil */
.womensRow td{background:rgba(224,145,177,.055)!important;border-top:1px solid rgba(224,145,177,.28);border-bottom:1px solid rgba(224,145,177,.28)}
.womensRow td:first-child{border-left:3px solid rgba(224,145,177,.58)}
.womensRow td:last-child{border-right:3px solid rgba(224,145,177,.28)}
.womensRow:hover td{background:rgba(224,145,177,.09)!important}
.womensRow .teamCell b{color:#f0d5df}.womensRow td{color:#d9c3cc}
.topStar{display:inline-flex;align-items:center;justify-content:center;margin-right:5px;width:23px;height:23px;border-radius:50%;color:#ffd35a;background:rgba(255,211,90,.10);border:1px solid rgba(255,211,90,.38);font-size:13px;box-shadow:0 0 10px rgba(255,211,90,.08)}.topStar[title]{cursor:help}.womensTag{display:inline-flex;align-items:center;gap:4px;margin-left:7px;padding:2px 7px;border-radius:999px;background:rgba(224,145,177,.08);color:#d9a5b8;border:1px solid rgba(224,145,177,.32);font-size:10px;font-weight:800;letter-spacing:.35px}
.filterChip{font-weight:800}.filterChip.womensFilter{border-color:rgba(224,145,177,.30)}.filterChip.womensFilter.on{border-color:rgba(224,145,177,.62);box-shadow:0 0 0 1px rgba(224,145,177,.12);color:#e0b3c3}.sectionTitle{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:16px 0 8px;padding:11px 13px;border-radius:10px;background:#0b1726;border:1px solid var(--line);font-size:15px;font-weight:900}.sectionTitle.women{border-color:rgba(224,145,177,.28);background:linear-gradient(90deg,rgba(224,145,177,.045),#0b1726)}.sectionTitle .count{font-size:11px;color:var(--muted);font-weight:700}.sectionTitle.women .count{color:#d9a5b8}.h2hStatsGrid{margin-top:10px;display:grid;grid-template-columns:1fr;gap:8px}.h2hStatsGrid>div{background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:10px;font-size:12px;line-height:1.5}.h2hBox table{font-size:11px}.h2hBox th{white-space:nowrap}.h2hBox td{white-space:nowrap}.h2hBox{margin-top:14px;padding:16px;border:1px solid rgba(224,145,177,.25);border-radius:13px;background:linear-gradient(135deg,rgba(224,145,177,.045),#091524)}.h2hBox.noH2H{border:2px solid #ef4444;background:linear-gradient(135deg,rgba(239,68,68,.14),rgba(127,29,29,.08));box-shadow:0 0 18px rgba(239,68,68,.10)}.h2hNoTitle{color:#ff5b5b;font-size:17px;font-weight:950}.h2hNoText{margin-top:7px;color:#ffd0d0;font-size:12px;font-weight:800}.h2hUnavailable{border-color:rgba(255,183,77,.45);background:linear-gradient(135deg,rgba(255,183,77,.08),#091524)}.h2hUnavailable .h2hNoTitle{color:#ffbf69}.universalBox{margin-top:14px;padding:15px;border:2px solid rgba(255,211,90,.55);border-radius:13px;background:linear-gradient(135deg,rgba(255,211,90,.10),#091524);box-shadow:0 0 18px rgba(255,211,90,.08)}.universalTitle{font-weight:900;color:#ffd35a;font-size:14px;letter-spacing:.25px}.universalList{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.universalList span{display:inline-flex;align-items:center;gap:6px;padding:8px 10px;border-radius:999px;background:rgba(39,211,154,.12);border:1px solid rgba(39,211,154,.45);color:#b8ffe8;font-weight:800;font-size:12px}.h2hBox b{font-size:18px}.h2hMeta{color:var(--muted);font-size:12px;margin-top:5px}.emptySection{padding:15px;border:1px dashed #29415d;border-radius:10px;color:var(--muted);font-size:12px}


.bettorBox{margin:14px 0;padding:14px;border:1px solid #2d567a;border-radius:14px;background:linear-gradient(135deg,#0b1b2b,#0a1421);box-shadow:0 8px 24px rgba(0,0,0,.18)}.bettorHead{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px}.bettorTitle{font-size:16px;font-weight:900;letter-spacing:.2px}.bettorBadge{font-size:10px;font-weight:900;color:#8fe1ff;border:1px solid #22658d;background:#08233a;border-radius:999px;padding:6px 9px}.bettorGrid{display:grid;grid-template-columns:1.25fr 1fr;gap:12px}.bettorPanel{background:#0b1726;border:1px solid #1a3957;border-radius:11px;padding:11px}.bettorPanel h4{margin:0 0 8px;font-size:12px}.legRow{display:grid;grid-template-columns:24px 1fr auto;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid #18314a}.legRow:last-child{border-bottom:0}.legRank{font-weight:900;color:#7ecfff}.legMain b{display:block;font-size:12px}.legMain span{display:block;color:#7893ad;font-size:9px;margin-top:2px;line-height:1.25}.legRate{font-weight:900;font-size:13px;color:#9ff5d8;text-align:right}.tierStrong{color:#9ff5d8}.tierMid{color:#ffd976}.tierVar{color:#ff9a9a}.ticketLegs{display:flex;flex-wrap:wrap;gap:7px}.ticketChip{padding:8px 10px;border-radius:999px;border:1px solid #27587a;background:#0c2336;color:#c9e8fb;font-size:10px;font-weight:800}.bettorNote{margin-top:9px;color:#7f9ab2;font-size:10px;line-height:1.35}@media(max-width:900px){.bettorGrid{grid-template-columns:1fr}.prematchGrid{grid-template-columns:1fr 1fr}}

.statsOverlay{position:fixed;inset:0;z-index:1000;display:none;align-items:center;justify-content:center;padding:24px;background:rgba(2,7,14,.78);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}.statsOverlay.open{display:flex}.statsModal{width:min(1500px,96vw);max-height:92vh;display:flex;flex-direction:column;background:linear-gradient(145deg,#0c1726,#07111d);border:1px solid #2a4d70;border-radius:18px;box-shadow:0 28px 90px rgba(0,0,0,.60),0 0 0 1px rgba(37,168,255,.08);overflow:hidden;animation:statsModalIn .18s ease-out}.statsModalHead{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:16px 20px;border-bottom:1px solid #1d3858;background:linear-gradient(180deg,#0f1f32,#0a1625);position:relative;z-index:1}.statsModalKicker{font-size:10px;letter-spacing:.16em;font-weight:900;color:#6fc8ff}.statsModalHead h2{margin:3px 0 0;font-size:20px}.statsClose{width:38px;height:38px;padding:0;border-radius:10px;font-size:18px;font-weight:900;background:#101f31;border-color:#31516f}.statsClose:hover{background:#172c42;border-color:#4b759b}.statsModalBody{overflow:auto;padding:18px 20px 26px}.statsModalBody>.matchHero{margin-bottom:14px}.statsLoading{display:flex;align-items:center;justify-content:center;min-height:180px;color:#9fc2df}.statsLoading .spinner{width:28px;height:28px;border:3px solid #214361;border-top-color:#25a8ff;border-radius:50%;animation:spin .8s linear infinite;margin-right:10px}@keyframes spin{to{transform:rotate(360deg)}}@keyframes statsModalIn{from{opacity:0;transform:translateY(10px) scale(.985)}to{opacity:1;transform:none}}body.modalOpen{overflow:hidden}@media(max-width:700px){.statsOverlay{padding:8px}.statsModal{width:100%;max-height:96vh;border-radius:14px}.statsModalHead{padding:13px 14px}.statsModalBody{padding:12px}.statsModalHead h2{font-size:17px}}

.intensityBox{margin:8px 0 12px;padding:10px 12px;border-radius:11px;border:1px solid #2a4868;background:#0a1a2b}
.intensityBox.hot{border-color:#ff5c68;box-shadow:0 0 16px rgba(255,92,104,.16)}
.intensityBox.warm{border-color:#ffd35a;box-shadow:0 0 16px rgba(255,211,90,.12)}
.intensityBox.normal{border-color:#25a8ff}
.intensityBox.cold{border-color:#3d6a88}
.intensityTop{display:flex;justify-content:space-between;gap:8px;font-size:11px;font-weight:800;letter-spacing:.04em}
.intensityBox.hot .intensityTop b,.intensityBox.warm .intensityTop b{color:#ffd35a}
.intensityBar{height:8px;border-radius:99px;background:#102033;margin:8px 0 6px;overflow:hidden}
.intensityBar i{display:block;height:100%;background:linear-gradient(90deg,#27d39a,#ffd35a,#ff5c68)}.styleBox{margin:8px 0 12px;padding:11px;border:1px solid #2a4868;border-radius:11px;background:#0a1a2b}.styleGrid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}.styleCell{background:#071421;border-radius:9px;padding:8px}.styleCell span{display:block;color:#8fa6c0;font-size:10px;font-weight:800}.styleCell b{display:block;margin-top:3px}.styleCell small{display:block;color:#9db4c9;margin-top:3px}
.builderGrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.alwaysChip{border-color:#27d39a;background:#0c2b22;color:#b8ffe8}
.leagueTableBox{margin:8px 0 12px;padding:10px;border:1px solid #2a4868;border-radius:11px;background:#0a1a2b}
.leagueTable td,.leagueTable th{text-align:center}
.leagueTable tr.in8 td{background:rgba(201,221,3,.06)}

.hotChip{border-color:#ffd35a;color:#ffe7a3}
.htBox{margin:8px 0;padding:10px;border:1px solid #2a4868;border-radius:11px;background:#0a1a2b}.cornerBox{margin:8px 0;padding:10px;border:1px solid #2a5a4a;border-radius:11px;background:#071a16}.cornerBox.alta{border-color:#2d8f6a}.cornerBox.media{border-color:#3a6e8f}.cornerBox.baja{border-color:#3a4a58}.cornerHead{display:flex;justify-content:space-between;gap:8px;align-items:baseline;margin-bottom:6px}.cornerHead b{color:#7dffc4}.cornerGrid{display:grid;grid-template-columns:repeat(6,1fr);gap:7px}.cornerGrid div{background:#061310;border-radius:8px;padding:7px}.cornerGrid strong{display:block;font-size:15px}.cornerGrid span{color:#8fb8aa;font-size:10px}.matchCornerBox{margin:0 0 12px;padding:12px;border:1px solid #2a5a4a;border-radius:12px;background:linear-gradient(180deg,#0a221c,#071611)}
.htGrid{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:8px}
.htGrid div{background:#071421;border-radius:8px;padding:8px}
.htGrid strong{display:block;font-size:18px;color:#ffd35a}
.htGrid span{font-size:11px;color:#9db4c9}
.watchBox{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 16px}
.watchCol{background:#0a1a2b;border:1px solid #2a4868;border-radius:11px;padding:10px}
.watchCol h4{margin:0 0 8px;font-size:13px}
.watchRow{display:flex;gap:6px;margin-bottom:8px}
.watchRow input{flex:1;background:#071421;border:1px solid #2a4868;color:#e8f1f8;border-radius:8px;padding:6px 8px}
.watchRow button{background:#12304a;border:1px solid #2a4868;color:#e8f1f8;border-radius:8px;padding:6px 10px;cursor:pointer}
.tagList{display:flex;flex-wrap:wrap;gap:6px}
.tag{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:4px 8px;font-size:12px}
.tag.fav{background:#1d3a16;border:1px solid #3d7a2a;color:#d4f5c4}
.tag.blk{background:#3a1616;border:1px solid #7a2a2a;color:#f5c4c4}
.tag button{background:none;border:0;color:inherit;cursor:pointer}
tr.favRow td{background:rgba(61,122,42,.12)}
tr.blkRow td{background:rgba(122,42,42,.14)}
@media(max-width:900px){.htGrid,.watchBox{grid-template-columns:1fr}}

@media(max-width:900px){.builderGrid{grid-template-columns:1fr}}

.mList{display:none}
.watchAgenda{margin-top:8px;display:flex;flex-direction:column;gap:6px}
.agendaItem{background:#071421;border:1px solid #1d3a56;border-radius:9px;padding:7px 8px;font-size:12px}
.agendaItem b{display:block;color:#d5e7f6}
.agendaMeta{color:#8fa6c0;font-size:11px}
@media(max-width:760px){
  header{padding:14px 12px}
  .brand{font-size:18px;letter-spacing:0}
  .bar{padding:8px 10px;gap:6px}
  .bar input,.bar select,.bar button{min-width:0;padding:8px 9px;font-size:12px}
  .bar input{flex:1 1 100%}
  .dateSelect,.monthSelect,.sortToggle{min-width:0;flex:1 1 auto}
  .watchBox{margin:8px 10px}
  .wrap{width:100%;padding:10px}
  .today table{display:none}
  .mList{display:flex;flex-direction:column;gap:8px}
  .mCard{background:#0b1a2a;border:1px solid #1d3858;border-radius:12px;padding:10px}
  .mCardTop{display:flex;justify-content:space-between;gap:8px;color:#8fa6c0;font-size:11px;font-weight:700}
  .mCardComp{margin:5px 0 8px;color:#c5d8ea;font-size:12px;line-height:1.3;white-space:normal}
  .mCardTeams{display:flex;flex-direction:column;gap:6px}
  .mCardTeams .teamCell{overflow:visible}
  .mCardTeams .teamCell b{white-space:normal;overflow:visible;text-overflow:unset;font-size:14px}
  .mCardBtn{width:100%;margin-top:8px}
  .dual,.summaryGrid,.matchHero,.metrics,.metricExtra,.cornerGrid,.htGrid{grid-template-columns:1fr 1fr !important}
  .matchHero{grid-template-columns:1fr !important}
  .statsOverlay{padding:0;align-items:stretch}
  .statsModal{width:100%;max-height:100vh;border-radius:0}
  .tableScroll{overflow:visible}
}
@media(min-width:761px){.mList{display:none}}

</style></head>
<body>
<header><div class="brand">⚽ <span>PREMATCH</span> STATS DESK</div><div class="sub">Estadística histórica verificable · filtro PREMATCH APOSTADOR · hora Perú UTC−5</div></header>
<div class="bar">
  <span class="dateLabel">📅 FECHA</span>
  <select id="dateMonth" class="monthSelect"></select>
  <select id="dateDay" class="dateSelect"></select>
  <button type="button" class="chip sortToggle on" id="sortToggle" title="Cambiar orden horario">↑ INICIO → FIN</button>
  <button class="chip filterChip" data-filter="all" id="filterAll">TODOS</button>
  <button class="chip filterChip on" data-filter="men" id="filterMen">⚽ MASCULINO</button>
  <button class="chip filterChip womensFilter" data-filter="women" id="filterWomen">🌸 FEMENINO</button>
  <button class="chip filterChip" data-filter="fav" id="filterFav">⭐ FAVORITOS</button>
  <button class="chip filterChip" data-filter="blk" id="filterBlk">⛔ LISTA NEGRA</button>
  <input id="q" placeholder="Buscar equipo, país o competición…"/>
  <select id="pais"><option value="">Todos los países</option></select>
</div>
<div class="watchBox">
  <div class="watchCol"><h4>⭐ Favoritos · equipos que te hacen ganar</h4>
    <div class="watchRow"><input id="favIn" placeholder="Nombre del equipo…"><button type="button" onclick="addWatch('fav')">Añadir</button></div>
    <div class="tagList" id="favList"></div>
    <div class="watchAgenda" id="favAgenda"></div>
  </div>
  <div class="watchCol"><h4>⛔ Lista negra · equipos que no te hacen ganar</h4>
    <div class="watchRow"><input id="blkIn" placeholder="Nombre del equipo…"><button type="button" onclick="addWatch('blk')">Añadir</button></div>
    <div class="tagList" id="blkList"></div>
    <div class="watchAgenda" id="blkAgenda"></div>
  </div>
</div>
<div class="wrap"><div class="panel"><div class="today" id="todayTable"></div></div><div id="detailHost" class="statsOverlay" aria-hidden="true"><div class="statsModal" role="dialog" aria-modal="true" aria-labelledby="statsModalTitle"><div class="statsModalHead"><div><div class="statsModalKicker">📊 PREMATCH STATS</div><h2 id="statsModalTitle">Estadísticas del partido</h2></div><button type="button" class="statsClose" onclick="closeStatsModal()" aria-label="Cerrar">✕</button></div><div id="statsModalBody" class="statsModalBody"></div></div></div><div class="footer">Fuente histórica: SofaScore cuando responde. Logos: TheSportsDB cuando están disponibles; si no hay escudo se muestran iniciales. Si la fuente devuelve HTTP 403, no entrega una estadística o no existe el histórico, se muestra <b>Dato no disponible</b>. Los promedios y rangos se calculan únicamente sobre valores realmente recibidos.</div></div>
<script>
const TODAY_22_09=__TODAY__;
let selectedDate="__TODAY_DATE__";
let ALL_TODAY=[];
const DATE_LABELS={"2026-09-22":"22/09/2026","2026-09-23":"23/09/2026","2026-09-24":"24/09/2026","2026-09-25":"25/09/2026","2026-09-26":"26/09/2026","2026-09-27":"27/09/2026","2026-09-28":"28/09/2026","2026-09-29":"29/09/2026"};
const FALLBACK_DATES={
 "2026-09-22":[
  {n:2999,pais:"Brasil",liga:"Série B",hora:"17:30",local:"Criciúma",visita:"Operário-PR",estado:"Programado",is_cup:false,top_flight:true}
 ],
 "2026-09-23":[
  {n:1001,pais:"Europa",liga:"UEFA Women's Champions League",hora:"11:45",local:"Leuven Women",visita:"Roma Women",estado:"Programado",is_cup:false,gender:"female"},
  {n:1002,pais:"Europa",liga:"UEFA Women's Champions League",hora:"11:45",local:"Servette Women",visita:"OL Lyonnes",estado:"Programado",is_cup:false,gender:"female"},
  {n:1003,pais:"Europa",liga:"UEFA Women's Champions League",hora:"14:00",local:"Barcelona Women",visita:"Paris FC Women",estado:"Programado",is_cup:false,gender:"female"},
  {n:1004,pais:"Europa",liga:"UEFA Women's Champions League",hora:"14:00",local:"Chelsea Women",visita:"Austria Vienna Women",estado:"Programado",is_cup:false,gender:"female"},
  {n:1010,pais:"Inglaterra",liga:"Subway Women's League Cup",hora:"13:00",local:"Tottenham Hotspur Women",visita:"West Ham United Women",estado:"Programado",is_cup:true,gender:"female"},
  {n:1011,pais:"Inglaterra",liga:"Subway Women's League Cup",hora:"13:00",local:"Crystal Palace Women",visita:"Watford Women",estado:"Programado",is_cup:true,gender:"female"},
  {n:1012,pais:"Inglaterra",liga:"Subway Women's League Cup",hora:"13:00",local:"Nottingham Forest Women",visita:"Aston Villa Women",estado:"Programado",is_cup:true,gender:"female"},
  {n:1013,pais:"Inglaterra",liga:"Subway Women's League Cup",hora:"13:00",local:"Liverpool Women",visita:"Sunderland Women",estado:"Programado",is_cup:true,gender:"female"},
  {n:1014,pais:"Inglaterra",liga:"Subway Women's League Cup",hora:"13:00",local:"Manchester United Women",visita:"Sheffield United Women",estado:"Programado",is_cup:true,gender:"female"},
  {n:1015,pais:"Inglaterra",liga:"Subway Women's League Cup",hora:"13:00",local:"Everton Women",visita:"Birmingham City Women",estado:"Programado",is_cup:true,gender:"female"},
  {n:1016,pais:"Inglaterra",liga:"Subway Women's League Cup",hora:"13:30",local:"Leicester City Women",visita:"London City Lionesses",estado:"Programado",is_cup:true,gender:"female"},
  {n:1017,pais:"Inglaterra",liga:"Subway Women's League Cup",hora:"13:45",local:"Brighton Women",visita:"Charlton Athletic Women",estado:"Programado",is_cup:true,gender:"female"}
 ],
 "2026-09-24":[
  {n:2001,pais:"Europa",liga:"UEFA Nations League",hora:"11:00",local:"Andorra",visita:"Malta",estado:"Programado",is_cup:false},
  {n:2002,pais:"Europa",liga:"UEFA Nations League",hora:"13:45",local:"Austria",visita:"Israel",estado:"Programado",is_cup:false},
  {n:2003,pais:"Europa",liga:"UEFA Nations League",hora:"13:45",local:"Kosovo",visita:"Rep of Ireland",estado:"Programado",is_cup:false},
  {n:2004,pais:"Europa",liga:"UEFA Nations League",hora:"13:45",local:"Liechtenstein",visita:"Lithuania",estado:"Programado",is_cup:false},
  {n:2005,pais:"Europa",liga:"UEFA Nations League",hora:"13:45",local:"Netherlands",visita:"Germany",estado:"Programado",is_cup:false},
  {n:2006,pais:"Europa",liga:"UEFA Nations League",hora:"13:45",local:"Norway",visita:"Denmark",estado:"Programado",is_cup:false},
  {n:2007,pais:"Europa",liga:"UEFA Nations League",hora:"13:45",local:"Portugal",visita:"Wales",estado:"Programado",is_cup:false},
  {n:2008,pais:"Europa",liga:"UEFA Nations League",hora:"13:45",local:"Serbia",visita:"Greece",estado:"Programado",is_cup:false}
 ],
 "2026-09-25":[
  {n:3001,pais:"Brasil",liga:"Série B",hora:"17:30",local:"Novorizontino",visita:"São Bernardo",estado:"Programado",is_cup:false,top_flight:true},
  {n:3002,pais:"Brasil",liga:"Série B",hora:"18:30",local:"Vila Nova",visita:"Londrina",estado:"Programado",is_cup:false,top_flight:true},
 ],
 "2026-09-26":[
  {n:3003,pais:"Brasil",liga:"Série B",hora:"14:00",local:"Operário-PR",visita:"Ceará",estado:"Programado",is_cup:false,top_flight:true},
  {n:3004,pais:"Brasil",liga:"Série B",hora:"16:30",local:"Goiás",visita:"Atlético-GO",estado:"Programado",is_cup:false,top_flight:true},
  {n:3005,pais:"Brasil",liga:"Série B",hora:"18:30",local:"Náutico",visita:"Sport",estado:"Programado",is_cup:false,top_flight:true},
  {n:3006,pais:"Brasil",liga:"Série C",hora:"15:00",local:"Botafogo-PB",visita:"Maringá",estado:"Programado",is_cup:false,top_flight:true},
  {n:3007,pais:"Brasil",liga:"Série C",hora:"15:00",local:"Floresta",visita:"Santa Cruz",estado:"Programado",is_cup:false,top_flight:true},
  {n:3008,pais:"Brasil",liga:"Série C",hora:"17:30",local:"Inter de Limeira",visita:"Paysandu",estado:"Programado",is_cup:false,top_flight:true}
 ],
 "2026-09-27":[
  {n:3009,pais:"Brasil",liga:"Série B",hora:"09:00",local:"Criciúma",visita:"Avaí",estado:"Programado",is_cup:false,top_flight:true},
  {n:3010,pais:"Brasil",liga:"Série B",hora:"14:00",local:"CRB",visita:"Cuiabá",estado:"Programado",is_cup:false,top_flight:true},
  {n:3011,pais:"Brasil",liga:"Série B",hora:"16:30",local:"Fortaleza",visita:"Athletic-MG",estado:"Programado",is_cup:false,top_flight:true},
  {n:3012,pais:"Brasil",liga:"Série C",hora:"16:30",local:"Brusque",visita:"Ferroviária",estado:"Programado",is_cup:false,top_flight:true}
 ],
 "2026-09-28":[
  {n:3013,pais:"Brasil",liga:"Série B",hora:"17:30",local:"América-MG",visita:"Juventude",estado:"Programado",is_cup:false,top_flight:true}
 ],
 "2026-09-29":[
  {n:3014,pais:"Brasil",liga:"Série B",hora:"17:30",local:"Botafogo-SP",visita:"Ponte Preta",estado:"Programado",is_cup:false,top_flight:true}
 ]
};

const q=document.getElementById('q'),pais=document.getElementById('pais');
function esc(v){return String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}
function fmt(v,percent=false){if(v==null)return '<span class="missingText">Dato no disponible</span>';return esc(Number(v).toFixed(2))+(percent?'%':'')}
function range(v){return v||'Dato no disponible'}
function metric(label,m,percent=false){m=m||{};const missing=m.average==null;return `<div class="metric ${missing?'missing':''}"><span class="label">${label}</span><b>${fmt(m.average,percent)}</b><small>Rango: ${esc(range(m.range))} · ${m.available_matches||0} con dato</small></div>`}
function record(t){const r=t.records||{};const a=r.all||{};const h=r.home||{};const v=r.away||{};return `<div class="record"><div class="rec"><b>${a.wins||0}–${a.draws||0}–${a.losses||0}</b><span>G–E–P últimos ${t.matches||0}</span></div><div class="rec"><b>${h.wins||0}–${h.draws||0}–${h.losses||0}</b><span>Local</span></div><div class="rec"><b>${v.wins||0}–${v.draws||0}–${v.losses||0}</b><span>Visitante</span></div></div>`}
function recentRows(t){if(!t.recent||!t.recent.length)return '<tr><td colspan="14" class="missingText">Dato no disponible</td></tr>';return t.recent.map(x=>{const cls=x.result==='G'?'win':x.result==='E'?'draw':'loss';let d='—';if(x.date){const dt=typeof x.date==='number'?new Date(x.date*1000):new Date(x.date);if(!Number.isNaN(dt.getTime()))d=dt.toLocaleDateString('es-PE',{day:'2-digit',month:'2-digit'});}const comp=String(x.competition||'—');const compIcon=/champions/i.test(comp)?'◉':/copa/i.test(comp)?'◈':'◍';return `<tr><td>${d}</td><td><span class="compCell"><i>${compIcon}</i>${esc(comp)}</span></td><td class="rivalCell">${esc(x.opponent)} <span>· ${esc(x.venue)}</span></td><td class="result ${cls}"><span class="resultPill">${esc(x.result)}</span></td><td class="scoreCell">${esc(x.goals_for)}–${esc(x.goals_against)}</td><td class="statCell">${(x.goals_ht_for==null&&x.goals_ht_against==null)?'—':esc(String(x.goals_ht_for??'—'))+'–'+esc(String(x.goals_ht_against??'—'))}</td><td class="statCell">${esc(x.shots??'—')}</td><td class="statCell">${esc(x.sot??'—')}</td><td class="statCell">${esc(x.fouls??'—')}</td><td class="statCell">${esc(x.yellow??'—')}</td><td class="statCell">${esc(x.corners??'—')}</td><td class="statCell">${esc(x.tackles??'—')}</td><td class="statCell">${esc(x.offsides??'—')}</td></tr>`}).join('')}
function universalBlock(t){const a=t.universal_trends||[];if(!a.length)return `<div class="universalBox"><div class="universalTitle">🔥 LO QUE SE CUMPLIÓ EN TODOS LOS ÚLTIMOS PARTIDOS</div><div class="h2hMeta">No hay una tendencia del 100% con los datos verificables disponibles.</div></div>`;return `<div class="universalBox"><div class="universalTitle">🔥 LO QUE SE CUMPLIÓ EN TODOS LOS ÚLTIMOS PARTIDOS</div><div class="universalList">${a.map(x=>`<span>✓ ${esc(x.label)} <b>${x.hits}/${x.sample}</b></span>`).join('')}</div><div class="h2hMeta">Solo se resaltan patrones con 100% de cumplimiento. No es una predicción.</div></div>`}
function htInsight(t){
  const rec=(t.recent||[]).filter(x=>x.goals_ht_total!=null||(x.goals_ht_for!=null&&x.goals_ht_against!=null));
  if(!rec.length) return `<div class="htBox"><b>⏱ GOLES EN EL 1.º TIEMPO</b><div class="h2hMeta">Sin marcador de primer tiempo verificable en la fuente.</div></div>`;
  const tot=rec.map(x=>x.goals_ht_total!=null?Number(x.goals_ht_total):(Number(x.goals_ht_for||0)+Number(x.goals_ht_against||0)));
  const n=tot.length;
  const g05=tot.filter(v=>v>=1).length;
  const g15=tot.filter(v=>v>=2).length;
  const zero=tot.filter(v=>v===0).length;
  const avg=(tot.reduce((a,b)=>a+b,0)/n).toFixed(2);
  const team=(t.recent||[]).filter(x=>x.goals_ht_for!=null);
  const tavg=team.length?(team.reduce((a,b)=>a+Number(b.goals_ht_for),0)/team.length).toFixed(2):'—';
  return `<div class="htBox"><b>⏱ GOLES EN EL 1.º TIEMPO · dato real</b>
    <div class="htGrid">
      <div><strong>${g05}/${n}</strong><span>partidos con gol en 1T (${Math.round(g05*100/n)}%)</span></div>
      <div><strong>${g15}/${n}</strong><span>partidos +1.5 goles 1T (${Math.round(g15*100/n)}%)</span></div>
      <div><strong>${zero}/${n}</strong><span>1T en 0-0 (${Math.round(zero*100/n)}%)</span></div>
      <div><strong>${avg}</strong><span>promedio goles 1T del partido</span></div>
      <div><strong>${tavg}</strong><span>promedio goles 1T de ${esc(t.team)}</span></div>
    </div>
    <div class="h2hMeta">Se cuenta el marcador real al descanso (goles de ambos). No es estimado.</div>
  </div>`;
}

function cornerInsight(t){
  const p=t.corner_profile||{};
  if(!p.available){
    return `<div class="cornerBox"><div class="cornerHead"><b>🚩 CÓRNERS · dato real</b><span>sin dato</span></div><div class="h2hMeta">La fuente no entregó córners en los partidos de ${esc(t.team)}. No se estima.</div></div>`;
  }
  const band=th=>{
    const b=(p.bands||[]).find(x=>x.min===th)||{};
    const hits=b.hits??'—', n=b.sample??p.sample, rate=b.rate!=null?b.rate+'%':'—';
    return `<div><strong>${hits}/${n}</strong><span>${th}+ córners · ${rate}</span></div>`;
  };
  return `<div class="cornerBox ${esc(p.tone||'')}">
    <div class="cornerHead"><b>🚩 CÓRNERS DE ${esc(t.team)}</b><span>${esc(p.label||'')}</span></div>
    <div class="cornerGrid">
      <div><strong>${p.average}</strong><span>promedio por partido</span></div>
      <div><strong>${esc(p.range||'—')}</strong><span>rango real min–máx</span></div>
      ${band(3)}${band(4)}${band(5)}${band(6)}
    </div>
    <div class="h2hMeta">${p.sample} partido(s) con córners reales. 3+ en ${p.hit3}% · 4+ en ${p.hit4}% · 5+ en ${p.hit5}%. No es predicción.</div>
  </div>`;
}
function matchCornerBox(h,a){
  const hp=h&&h.corner_profile||{}, ap=a&&a.corner_profile||{};
  if(!hp.available && !ap.available){
    return `<div class="matchCornerBox"><b>🚩 CÓRNERS DEL PARTIDO</b><div class="h2hMeta">Ningún equipo trajo córners verificables. No se estima el total.</div></div>`;
  }
  const line=(p,name)=>p.available?`<div><b>${esc(name)}</b> · prom ${p.average} · rango ${esc(p.range)} · 3+ ${p.hit3}% · 4+ ${p.hit4}% · 5+ ${p.hit5}% (${p.sample} PJ)</div>`:`<div><b>${esc(name)}</b> · sin córners en la fuente</div>`;
  let extra='';
  if(hp.available && ap.available){
    const tot=(Number(hp.average)+Number(ap.average)).toFixed(1);
    const lo=Number(hp.min)+Number(ap.min), hi=Number(hp.max)+Number(ap.max);
    extra=`<div class="h2hMeta" style="margin-top:8px">Suma de promedios (descriptiva): <b>${tot} córners</b> · suma de rangos ${lo}–${hi}. No trata dos calendarios como un solo duelo.</div>`;
  }
  return `<div class="matchCornerBox"><b>🚩 CÓRNERS · LECTURA DEL CRUCE</b>${line(hp,h.team||'Local')}${line(ap,a.team||'Visitante')}${extra}</div>`;
}
function teamBlock(t,side){const ok=t.source_status!=='UNAVAILABLE';const logo=t.logo||"";const accentSide=side==='away'?'awayBox':'homeBox';const m=t.metrics||{};const teamMeta=[t.competition||t.league||t.recent?.[0]?.competition,t.country].filter(Boolean).join(' · ')||'Histórico verificable';const card=(icon,label,key,cls)=>{const v=m[key]?.average;const missing=v==null;return `<div class="metric ${cls||''} ${missing?'missing':''}"><span class="metricIcon">${icon}</span><span class="label">${label}</span><b>${fmt(v)}</b><small>por partido</small></div>`};return `<section class="teamBox ${accentSide}"><div class="teamTitle"><div class="boxTitle">${logo?`<img class="boxCrest" src="${esc(logo)}">`:``}<div><b>${esc(t.team)}</b><span class="teamMeta">${esc(teamMeta)}</span></div></div><span class="status">Últimos ${Math.min(20,t.recent?.length||20)} partidos</span></div><div class="metrics">${card('◢','Remates','shots','shots')}${card('▥','Tiros a puerta','sot','sot')}${card('⚽','Goles','goals_for','goals')}${card('⏱','Goles 1T (equipo)','goals_ht_for','goals')}${card('⏱','Goles 1T (partido)','goals_ht_total','goals')}${card('⚑','Faltas','fouls','fouls')}${card('🟨','Amarillas','yellow','yellow')}${card('⚑','Córners','corners','corners')}<div class="metricExtra">${card('🛡','Tackles','tackles','tackles')}${card('↔','Saques de banda','throwins','throwins')}${card('🚩','Offsides','offsides','offsides')}${card('↯','Tiros libres','freekicks','freekicks')}${card('🥅','Saques de meta','goalkicks','goalkicks')}${card('🧤','Atajadas','saves','saves')}${card('✚','Centros','crosses','crosses')}${card('▣','Remates bloqueados','blockedshots','blockedshots')}${card('〽','Palo/Travesaño','woodwork','woodwork')}${card('⚡','Ataques peligrosos','dangerousattacks','dangerousattacks')}</div></div>${htInsight(t)}${cornerInsight(t)}<div class="recent noScroll"><div class="recentHead"><h3>📅 Últimos ${Math.min(20,t.recent?.length||0)} partidos</h3><span class="recentBadge">Histórico verificable</span></div><table class="recentCompact"><thead><tr><th>Fecha</th><th>Competición</th><th>Rival</th><th>R</th><th>Marcador</th><th>Goles 1T</th><th>Remates</th><th>Tiros a puerta</th><th>Faltas</th><th>Amarillas</th><th>Córners</th><th>Tackles</th><th>Offsides</th></tr></thead><tbody>${recentRows(t)}</tbody></table></div><div class="sourceNote">ⓘ ${ok?`Fuente: ${esc(t.source)}. Los promedios usan solo partidos donde la fuente entregó ese campo.`:`⚠️ ${esc(t.reason||'Dato no disponible')}. No se muestran valores estimados.`}</div></section>`}
function summary(t){if(t.source_status==='UNAVAILABLE')return `<div class="summary"><h3>📈 Resumen estadístico — ${esc(t.team)}</h3><ul><li class="missingText">Dato no disponible porque la fuente no entregó un histórico verificable.</li></ul></div>`;const m=t.metrics||{};const fmtm=k=>m[k]?.average==null?'Dato no disponible':Number(m[k].average).toFixed(2);return `<div class="summary"><h3>📈 Resumen estadístico — ${esc(t.team)}</h3><ul><li>Promedio de goles: <b>${fmtm('goals_for')}</b>.</li><li>Promedio de goles en 1.º tiempo: <b>${fmtm('goals_ht_for')}</b>.</li><li>Promedio de remates: <b>${fmtm('shots')}</b>.</li><li>Promedio de remates al arco: <b>${fmtm('sot')}</b>.</li><li>Promedio de córners: <b>${fmtm('corners')}</b>.</li><li>Promedio de tarjetas amarillas: <b>${fmtm('yellow')}</b>.</li><li>Posesión media: <b>${m.possession?.average==null?'Dato no disponible':Number(m.possession.average).toFixed(2)+'%'}</b>.</li><li>Promedio de saques de banda: <b>${fmtm('throwins')}</b>.</li><li>Promedio de tackles: <b>${fmtm('tackles')}</b>.</li><li>Promedio de offsides: <b>${fmtm('offsides')}</b>.</li><li>Promedio de tiros libres: <b>${fmtm('freekicks')}</b>.</li><li>Promedio de saques de meta: <b>${fmtm('goalkicks')}</b>.</li><li>Promedio de atajadas: <b>${fmtm('saves')}</b>.</li><li>Promedio de centros: <b>${fmtm('crosses')}</b>.</li><li>Promedio de remates bloqueados: <b>${fmtm('blockedshots')}</b>.</li><li>Promedio de palo/travesaño: <b>${fmtm('woodwork')}</b>.</li><li>Promedio de ataques: <b>${fmtm('attacks')}</b>.</li><li>Promedio de ataques peligrosos: <b>${fmtm('dangerousattacks')}</b>.</li></ul></div>`}
function leagueTableBlock(t){
  if(!t||!t.available||!(t.rows||[]).length) return '';
  const rows=t.rows.map(r=>`<tr class="${(r.position||99)<=8?'in8':''}"><td>${r.position}</td><td class="teamCell">${r.logo?`<img class="miniCrest" src="${esc(r.logo)}">`:''}<b>${esc(r.team)}</b></td><td>${r.played??'—'}</td><td>${r.wins??'—'}</td><td>${r.draws??'—'}</td><td>${r.losses??'—'}</td><td>${r.gf??'—'}:${r.ga??'—'}</td><td>${r.gd??'—'}</td><td><b>${r.points??'—'}</b></td></tr>`).join('');
  return `<div class="leagueTableBox"><div class="prematchHead"><b>📋 ${esc(t.league||'Tabla')}</b><span class="sub">${esc(t.season||'')} · top 8 clasifica a cuadrangulares</span></div><table class="recentCompact leagueTable"><thead><tr><th>#</th><th>Equipo</th><th>PJ</th><th>G</th><th>E</th><th>P</th><th>GF:GC</th><th>DG</th><th>Pts</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function styleReading(p){
  const h=p.home||{}, a=p.away||{}, r=p.reading||{};
  const poss=v=>v==null?'Dato no disponible':Number(v).toFixed(1)+'%';
  const form=f=>f&&f.label?`${f.label}${f.ppg!=null?` · ${f.ppg} pts/pj`:''}${f.win_rate!=null?` · ${f.win_rate}% victorias`:''}`:'Sin racha';
  const cell=(title,team,st,frm,possAvg)=>`<div class="styleCell"><span>${title} · ${esc(team||'')}</span><b>${esc((st&&st.label)||'Sin estilo verificable')}</b><small>Posesión ${poss(possAvg)} · ${esc(form(frm))}</small><small>${esc((st&&st.detail)||'')}</small></div>`;
  return `<div class="styleBox"><div class="prematchHead"><b>🎯 NIVEL · RENDIMIENTO · ESTILO</b><span class="sub">Solo métricas reales de los últimos partidos</span></div>
    <div><b>${esc(r.label||'Comparación no disponible')}</b><div class="h2hMeta">${esc(r.detail||'')}</div></div>
    <div class="styleGrid">
      ${cell('Local',h.name,h.style,h.form,h.possession)}
      ${cell('Visita',a.name,a.style,a.form,a.possession)}
    </div>
  </div>`;
}
function intensityMeter(i){
  i=i||{}; const score=Math.max(0,Math.min(100,Number(i.score||0)));
  const tone=i.tone||'normal';
  return `<div class="intensityBox ${tone}"><div class="intensityTop"><span>INTENSIDAD DEL ENCUENTRO</span><b>${esc(i.label||'NORMAL')} · ${score}/100</b></div><div class="intensityBar"><i style="width:${score}%"></i></div><small>${esc(i.detail||'')}</small></div>`;
}
function pickList(arr, empty){
  if(!arr||!arr.length) return `<div class="bettorNote">${empty}</div>`;
  return `<div class="ticketLegs">${arr.map(x=>`<span class="ticketChip ${x.rate>=100?'alwaysChip':(x.rate>=78?'hotChip':'')}">${esc(x.label||x)}${x.rate!=null?` · ${x.rate}%`:''}${x.hits&&x.sample?` (${x.hits}/${x.sample})`:''}</span>`).join('')}</div>`;
}
function prematchBlock(p){
  if(!p||!p.available) return `<div class="prematchBox"><div class="prematchHead"><b>🧭 PREMATCH BUILDER</b><span class="sub">Dato no disponible</span></div><div class="h2hMeta">No se pudo armar el contexto de tabla, necesidad e intensidad.</div></div>`;
  const h=p.home||{},a=p.away||{},ts=p.tension||{},b=p.builder||{},inten=p.intensity||{};
  const item=(label,strong,small,cls='')=>`<div class="pmItem ${cls}"><span class="pmLabel">${label}</span><strong>${esc(strong||'No disponible')}</strong><small>${esc(small||'')}</small></div>`;
  const combo=(b.combo||[]).map(x=>`<span class="ticketChip alwaysChip">${esc(x)}</span>`).join('');
  return `<div class="prematchBox">
    <div class="prematchHead"><b>🧭 PREMATCH BUILDER</b><span class="sub">${esc(p.competition||'Competición')}${p.round?' · '+esc(p.round):''}</span></div>
    ${intensityMeter(inten)}
    ${styleReading(p)}
    ${leagueTableBlock(p.league_table)}
    <div class="prematchGrid">
      ${item('Posición · local',h.table_context?.label,(h.table_context?.zone||'')+' · '+(h.table_context?.detail||''),'pressure')}
      ${item('Posición · visitante',a.table_context?.label,(a.table_context?.zone||'')+' · '+(a.table_context?.detail||''),'pressure')}
      ${item('Necesidad · local',h.need?.label,h.need?.detail,'pressure')}
      ${item('Necesidad · visitante',a.need?.label,a.need?.detail,'pressure')}
      ${item('Ofensiva · local',h.offensive?.label,h.offensive?.detail,'offensive')}
      ${item('Ofensiva · visitante',a.offensive?.label,a.offensive?.detail,'offensive')}
      ${item('Estilo · local',h.style?.label,(h.possession!=null?('Posesión '+Number(h.possession).toFixed(1)+'% · '):'')+(h.style?.detail||''),'offensive')}
      ${item('Estilo · visitante',a.style?.label,(a.possession!=null?('Posesión '+Number(a.possession).toFixed(1)+'% · '):'')+(a.style?.detail||''),'offensive')}
      ${item('Rendimiento · local',h.form?.label,(h.form?.ppg!=null?h.form.ppg+' pts/pj':'')+' · '+(h.form?.win_rate!=null?h.form.win_rate+'% victorias':''),'pressure')}
      ${item('Rendimiento · visitante',a.form?.label,(a.form?.ppg!=null?a.form.ppg+' pts/pj':'')+' · '+(a.form?.win_rate!=null?a.form.win_rate+'% victorias':''),'pressure')}
      ${item('Tensión / amarillas',ts.label,ts.detail,'tension')}
      ${item('Lectura del cruce',inten.label,inten.detail,'tension')}
    </div>
    <div class="builderGrid">
      <div class="bettorPanel"><h4>🔥 Picks que SIEMPRE se dieron en el H2H</h4>${pickList(b.always,'No hay un patrón al 100% en los duelos directos.')}<div class="bettorNote">Muestra H2H: ${b.h2h_sample||0} enfrentamientos. Solo entra lo que ocurrió en todos.</div></div>
      <div class="bettorPanel"><h4>🎯 Picks posibles (forma reciente)</h4>${pickList(b.possible,'Sin picks con muestra suficiente en los últimos 20.')}<div class="bettorNote">Últimos ${b.form_home||0}/${b.form_away||0} partidos de cada equipo. No es cuota ni garantía.</div></div>
    </div>
    <div class="bettorPanel" style="margin-top:8px"><h4>🧱 Combo builder</h4><div class="ticketLegs">${combo||'<span class="bettorNote">Aún no hay patas sólidas para armar combo.</span>'}</div><div class="bettorNote">Se priorizan los 100% del H2H y después frecuencias altas de la forma. Revisá alineaciones y minuto en vivo antes de usarlas.</div></div>
  </div>`;
}
function bettorPrematchBlock(p){
  if(!p||!p.available) return '';
  const tier=x=>x.tier==='Fuerte'?'tierStrong':x.tier==='Media'?'tierMid':'tierVar';
  const rows=(p.legs||[]).slice(0,8).map(x=>`<div class="legRow"><div class="legRank">${x.rank}</div><div class="legMain"><b>${esc(x.label)}</b><span>${esc(x.detail)} · ${esc(x.tier)}</span></div><div class="legRate ${tier(x)}">${x.rate}%</div></div>`).join('');
  return `<div class="bettorBox"><div class="bettorHead"><div class="bettorTitle">📊 FRECUENCIAS RECIENTES · ${esc(p.home)} vs ${esc(p.away)}</div><span class="bettorBadge">ÚLTIMOS ${p.sample_home||0}/${p.sample_away||0}</span></div><div class="bettorPanel">${rows||'<div class="bettorNote">Sin mercados con muestra suficiente.</div>'}</div><div class="bettorNote">${esc(p.note||'')}</div></div>`;
}
function h2hDate(v){
  if(v==null||v==='') return '—';
  const dt=typeof v==='number'?new Date(v>1e12?v:v*1000):new Date(v);
  if(Number.isNaN(dt.getTime())) return '—';
  return dt.toLocaleDateString('es-PE',{timeZone:'America/Lima',day:'2-digit',month:'2-digit',year:'numeric'});
}
function h2hBlock(h2h){
  if(!h2h || h2h.has_previous===false){
    return `<div class="h2hBox noH2H"><div class="h2hNoTitle">🔴 SIN DUELOS ANTERIORES</div><div class="h2hNoText">No se encontraron enfrentamientos previos verificables entre ${esc(h2h?.home||'estos equipos')} y ${esc(h2h?.away||'su rival')}. Por lo tanto, no existen estadísticas H2H históricas que mostrar.</div></div>`;
  }
  if(!h2h.available){
    return `<div class="h2hBox h2hUnavailable"><div class="h2hNoTitle">⚠️ H2H NO VERIFICABLE</div><div class="h2hMeta">${esc(h2h?.reason||'No se pudo consultar el histórico de enfrentamientos.')}</div></div>`;
  }
  const total=k=>{const p=h2h.totals?.[k];return p?.average!=null?fmt(p.average):'—'};
  const statTotal=(r,k)=>{const p=(r.stats||{})[k];return p&&p.home!=null&&p.away!=null?(p.home+p.away):'—'};
  const always=(h2h.universal||[]).map(x=>typeof x==='string'?{label:x,hits:h2h.sample,sample:h2h.sample}:x);
  const alwaysBox=always.length
    ? `<div class="universalBox"><div class="universalTitle">🔥 EN SUS H2H ESTO SE CUMPLIÓ SIEMPRE</div><div class="universalList">${always.map(x=>`<span>✓ ${esc(x.label)} <b>${x.hits}/${x.sample}</b></span>`).join('')}</div><div class="h2hMeta">Solo patrones con 100% en los duelos verificables. No es un pronóstico.</div></div>`
    : `<div class="universalBox"><div class="universalTitle">🔥 EN SUS H2H ESTO SE CUMPLIÓ SIEMPRE</div><div class="h2hMeta">No hay un patrón al 100% con la muestra disponible.</div></div>`;
  return `<div class="h2hBox"><div>🔁 <b>H2H · ÚLTIMOS DUELOS ENTRE AMBOS</b></div><div class="h2hMeta">${h2h.sample||h2h.matches?.length||0} enfrentamiento(s) directo(s) verificable(s), del más reciente al más antiguo.${h2h.source?` · Fuente: ${esc(h2h.source)}`:''}</div>${alwaysBox}<div class="h2hStatsGrid"><div><b>Promedios por duelo</b><br>⚽ Goles ${total('goals')} · 🟨 Amarillas ${total('yellow')} · 🟥 Rojas ${total('red')} · 🚩 Córners ${total('corners')} · 🛡️ Tackles ${total('tackles')} · 🚫 Faltas ${total('fouls')} · 🎯 Remates ${total('shots')} · 🎯 A puerta ${total('sot')} · 🏳️ Offsides ${total('offsides')} · ↔️ Saques ${total('throwins')}</div></div><table class="recentCompact h2hCompact"><thead><tr><th>Fecha</th><th>Competición</th><th>Duelo</th><th>Marcador</th><th>1T</th><th>Goles</th><th>Cór.</th><th>Faltas</th><th>Amar.</th><th>Rojas</th><th>Tackles</th><th>Rem.</th><th>A puerta</th><th>Offs.</th></tr></thead><tbody>${(h2h.matches||[]).slice(0,20).map(r=>{const d=h2hDate(r.date);let ht=r.home_goals_1t??r.home_ht??'—',at=r.away_goals_1t??r.away_ht??'—';return `<tr><td>${d}</td><td>${esc(r.competition||'—')}</td><td class="rivalCell">${esc(r.home)} <span>vs</span> ${esc(r.away)}</td><td class="scoreCell"><b>${r.home_goals}-${r.away_goals}</b></td><td>${ht==='—'||at==='—'?'—':ht+'-'+at}</td><td>${(Number(r.home_goals)||0)+(Number(r.away_goals)||0)}</td><td>${statTotal(r,'corners')}</td><td>${statTotal(r,'fouls')}</td><td>${statTotal(r,'yellow')}</td><td>${statTotal(r,'red')}</td><td>${statTotal(r,'tackles')}</td><td>${statTotal(r,'shots')}</td><td>${statTotal(r,'sot')}</td><td>${statTotal(r,'offsides')}</td></tr>`}).join('')}</tbody></table><div class="h2hMeta">Las estadísticas de cada choque solo aparecen cuando la fuente las entrega; los valores faltantes se mantienen como “—” y no se estiman.</div></div>`
}
async function loadMatch(m){
 const overlay=document.getElementById('detailHost'),body=document.getElementById('statsModalBody'),title=document.getElementById('statsModalTitle');
 overlay.classList.add('open');overlay.setAttribute('aria-hidden','false');document.body.classList.add('modalOpen');
 title.textContent=`${m.local} vs ${m.visita}`;
 body.innerHTML='<div class="statsLoading"><span class="spinner"></span><span>Consultando estadísticas, H2H y datos prematch…</span></div>';
 const qs=(p)=>encodeURIComponent(p||'');
 const getJson=async(url,timeout=28000)=>{
   const ctl=new AbortController(); const t=setTimeout(()=>ctl.abort(),timeout);
   try{
     const r=await fetch(url,{cache:'no-store',signal:ctl.signal});
     const ct=r.headers.get('content-type')||''; const d=ct.includes('application/json')?await r.json():{error:'El servidor no devolvió JSON'};
     if(!r.ok) throw new Error(d.error||('HTTP '+r.status)); return d;
   } finally { clearTimeout(t); }
 };
 const state={d:null,h2h:{available:false},prematch:{available:false},bettor:{available:false}};
 body.innerHTML=`<div class="statsLoading"><span class="spinner"></span><span>Cargando estadísticas principales…</span></div>`;
 const teamP=getJson('/api/team-stats?home='+qs(m.local)+'&away='+qs(m.visita)+'&limit=20',55000).then(d=>{state.d=d;return d}).catch(e=>({error:e.name==='AbortError'?'Tiempo de espera agotado al consultar estadísticas.':e.message}));
 const h2hP=getJson('/api/h2h?home='+qs(m.local)+'&away='+qs(m.visita),55000).then(d=>{state.h2h=d;return d}).catch(e=>({available:false,has_previous:null,reason:e.name==='AbortError'?'Tiempo de espera agotado al consultar el H2H.':(e.message||'No se pudo completar la consulta H2H.')}));
 const preP=getJson('/api/prematch?home='+qs(m.local)+'&away='+qs(m.visita)+'&date='+qs(m.fecha||selectedDate),55000).then(d=>{state.prematch=d;return d}).catch(()=>({available:false}));
 const betP=getJson('/api/bettor-prematch?home='+qs(m.local)+'&away='+qs(m.visita),20000).then(d=>{state.bettor=d;return d}).catch(()=>({available:false}));
 await Promise.allSettled([teamP,h2hP,preP,betP]);
 const d=state.d;
 if(!d || d.error){
   body.innerHTML=`<div class="panel"><b>⚠️ Las estadísticas principales no pudieron cargarse.</b><div class="sub" style="margin-top:6px">${esc(d?.error||'La fuente no respondió.')}</div><div style="margin-top:14px">${h2hBlock(state.h2h)}</div><div class="sourceNote">El H2H y los datos prematch se consultan de forma independiente; un fallo de estadísticas no bloquea los demás módulos.</div></div>`;
   return;
 }
 const logoHome=d.home?.logo||'';
 body.innerHTML=`<div class="matchHero"><div class="teamHero home">${logoHome?`<img class="crest" src="${esc(logoHome)}"/>`:''}<h2>${esc(d.home.team)}</h2><div class="sub">Local</div></div><div class="kick"><b>${esc(m.hora||'Hora no indicada')} <span style="display:inline;color:#8bdcff;font-size:10px">PE</span></b><span>${esc(m.liga)}</span><span>${esc(m.pais)}</span></div><div class="teamHero away">${d.away?.logo?`<img class="crest" src="${esc(d.away.logo)}"/>`:''}<h2>${esc(d.away.team)}</h2><div class="sub">Visitante</div></div></div>${prematchBlock(state.prematch)}${bettorPrematchBlock(state.bettor)}${matchCornerBox(d.home,d.away)}<div class="dual">${teamBlock(d.home,'home')}${teamBlock(d.away,'away')}</div>${h2hBlock(state.h2h)}<div class="summaryGrid" style="margin-top:14px">${summary(d.home)}${summary(d.away)}</div><div class="panel compare"><h3>⚖️ Comparación estadística</h3><table><thead><tr><th>Estadística</th><th>${esc(d.home.team)}</th><th>${esc(d.away.team)}</th></tr></thead><tbody>${[['Goles','goals_for',false],['Goles 1T','goals_ht_for',false],['Remates','shots',false],['Remates al arco','sot',false],['Córners','corners',false],['Posesión','possession',true],['Faltas','fouls',false],['Amarillas','yellow',false],['Rojas','red',false],['Saques de banda','throwins',false],['Tackles','tackles',false],['Offsides','offsides',false],['Tiros libres','freekicks',false],['Saques de meta','goalkicks',false],['Atajadas','saves',false],['Centros','crosses',false],['Remates bloqueados','blockedshots',false],['Palo/travesaño','woodwork',false],['Ataques','attacks',false],['Ataques peligrosos','dangerousattacks',false]].map(x=>`<tr><td>${x[0]}</td><td>${fmt(d.home.metrics?.[x[1]]?.average,x[2])}</td><td>${fmt(d.away.metrics?.[x[1]]?.average,x[2])}</td></tr>`).join('')}</tbody></table><div class="sourceNote">Fuente principal: ${esc(d.home?.source||'—')}${d.home?.source_status==='FALLBACK'?' (alternativa)':''}. ${esc(d.home?.source_note||d.away?.source_note||'')} No hay pronóstico. Esta pantalla solo describe encuentros históricos entregados por la fuente. Un campo ausente permanece como <b>Dato no disponible</b>.</div></div>`;
}
function closeStatsModal(){const overlay=document.getElementById('detailHost');overlay.classList.remove('open');overlay.setAttribute('aria-hidden','true');document.body.classList.remove('modalOpen')}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeStatsModal()});document.getElementById('detailHost').addEventListener('click',e=>{if(e.target.id==='detailHost')closeStatsModal()});

function loadMatchByN(n){
 const m=ALL_TODAY.find(x=>String(x.n)===String(n)),host=document.getElementById('detailHost');
 if(!m){host.innerHTML='<div class="panel"><b>⚠️ No se encontró el partido seleccionado.</b></div>';return false;}
 loadMatch(m);
 return false;
}
function initials(s){return String(s||"").split(/\\s+/).filter(Boolean).slice(0,2).map(x=>x[0]).join("").toUpperCase()||"?"}
function fallbackCrest(name){const s=document.createElement("span");s.className="miniCrest crestFallback";s.textContent=initials(name);return s}
function crest(url,name){if(url){return `<img class="miniCrest" src="${esc(url)}" alt="" data-team="${esc(name)}" onerror="fixCrest(this)">`}return `<span class="miniCrest crestFallback" data-team="${esc(name)}">${initials(name)}</span>`}
function fixCrest(img){if(!img||img.dataset.failed)return;img.dataset.failed="1";const name=img.dataset.team||"";fetch("/api/team-logo?name="+encodeURIComponent(name)).then(r=>r.json()).then(x=>{if(x.logo&&x.logo!==img.src){img.dataset.failed="";img.src=x.logo}else{img.replaceWith(fallbackCrest(name))}}).catch(()=>img.replaceWith(fallbackCrest(name)))}

function loadMissingLogos(){document.querySelectorAll("span[data-team]").forEach(el=>{if(el.dataset.logoLoaded)return;el.dataset.logoLoaded="1";fetch("/api/team-logo?name="+encodeURIComponent(el.dataset.team)).then(r=>r.json()).then(x=>{if(x.logo){const im=document.createElement("img");im.className="miniCrest";im.alt="";im.src=x.logo;im.onerror=()=>im.replaceWith(fallbackCrest(el.dataset.team));el.replaceWith(im)}}).catch(()=>{})})}
 function isTopFlightJS(m){
  if(m.top_flight===true)return true;
  const x=[m.liga,m.league,m.competition,m.name,m.pais,m.country].filter(Boolean).join(' ').toLowerCase();
  if(/women|femen|female|ladies|u21|u23|reserve|reserves|ii|2|cup|copa|trophy|challenge|beker/.test(x) && !/champions league/.test(x))return false;
  return /premier league|la liga|laliga|primera divisi[oó]n|primera a|liga 1|liga mx|liga bet ?play|liga pro|serie a|s[ée]rie ?b|s[ée]rie ?c|brasileir[aã]o.*s[ée]rie ?[abc]|bundesliga|ligue 1|eredivisie|primeira liga|premiership|superliga|super league|pro league|allsvenskan|eliteserien|super lig|first league|liga profesional|jupiler pro league|champions league|betplay|dimayor|primera a/.test(x);
}
function isCupJS(m){
  if(m && m.is_cup===true)return true;
  const x=[m?.liga,m?.league,m?.competition,m?.name,m?.pais,m?.country].filter(v=>v!==undefined&&v!==null).map(v=>String(v).toLowerCase()).join(" ");
  if(/women|femen|female|ladies|u21|u23|reserve|reserves/.test(x))return false;
  return /\bcup\b|copa|trophy|challenge cup|beker|coupe|pokal|coppa|taça|taca/.test(x);
}
const WATCH_KEY={fav:'prematch_favs',blk:'prematch_black'};
function loadWatch(kind){try{return JSON.parse(localStorage.getItem(WATCH_KEY[kind])||'[]')}catch(e){return []}}
function saveWatch(kind,arr){localStorage.setItem(WATCH_KEY[kind],JSON.stringify(arr));renderWatch();draw();refreshAgenda();}
function normWatch(n){return String(n||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\(f\)|\(w\)/g,'').replace(/\s+/g,' ').trim()}
function addWatch(kind){
  const inp=document.getElementById(kind==='fav'?'favIn':'blkIn');
  const name=(inp.value||'').trim(); if(!name) return;
  const arr=loadWatch(kind);
  if(!arr.some(x=>normWatch(x)===normWatch(name))) arr.push(name);
  const other=kind==='fav'?'blk':'fav';
  saveWatch(other, loadWatch(other).filter(x=>normWatch(x)!==normWatch(name)));
  inp.value=''; saveWatch(kind,arr);
}
function removeWatch(kind,name){saveWatch(kind, loadWatch(kind).filter(x=>normWatch(x)!==normWatch(name)));}
function isWatched(kind,name){return loadWatch(kind).some(x=>normWatch(x)===normWatch(name)||normWatch(name).includes(normWatch(x))||normWatch(x).includes(normWatch(name)));}
function watchFlags(m){
  const hf=isWatched('fav',m.local),af=isWatched('fav',m.visita);
  const hb=isWatched('blk',m.local),ab=isWatched('blk',m.visita);
  let cls='', mark='';
  if(hb||ab){cls='blkRow'; mark=' <span title="Lista negra">⛔</span>';}
  if(hf||af){cls=(cls?cls+' ':'')+'favRow'; mark+=' <span title="Favorito">⭐</span>';}
  return {cls,mark,fav:hf||af,blk:hb||ab};
}

let AGENDA={};
function nextDates(n){
  const out=[];
  const base=selectedDate||new Date().toISOString().slice(0,10);
  const [y,m,d]=base.split('-').map(Number);
  const start=new Date(y,m-1,d);
  for(let i=0;i<n;i++){
    const x=new Date(start); x.setDate(start.getDate()+i);
    out.push(`${x.getFullYear()}-${pad2(x.getMonth()+1)}-${pad2(x.getDate())}`);
  }
  return out;
}
function teamMatchesAgenda(names){
  const want=names.map(normWatch).filter(Boolean);
  if(!want.length) return [];
  const hits=[];
  Object.keys(AGENDA||{}).sort().forEach(date=>{
    (AGENDA[date]||[]).forEach(m=>{
      const a=normWatch(m.local), b=normWatch(m.visita);
      if(want.some(w=>a===w||b===w||a.includes(w)||b.includes(w)||w.includes(a)||w.includes(b))){
        hits.push({...m,fecha:date});
      }
    });
  });
  return hits;
}
function agendaHtml(kind){
  const names=loadWatch(kind);
  if(!names.length) return '<div class="h2hMeta">Añade un equipo para ver su calendario.</div>';
  const rows=teamMatchesAgenda(names);
  if(!rows.length) return '<div class="h2hMeta">Sin partidos en los próximos días (FotMob).</div>';
  return rows.slice(0,12).map(m=>`<div class="agendaItem"><b>${esc(m.local)} vs ${esc(m.visita)}</b><div class="agendaMeta">${esc(m.fecha||'')} · ${esc(m.hora||'')} PE · ${esc(m.liga||'')} · ${esc(m.pais||'')}</div></div>`).join('');
}
async function refreshAgenda(){
  try{
    const dates=nextDates(8);
    const r=await fetch('/api/calendar-range?dates='+encodeURIComponent(dates.join(',')),{cache:'no-store'});
    AGENDA=await r.json();
    if(!AGENDA || AGENDA.error) AGENDA={};
  }catch(e){AGENDA={}}
  const fa=document.getElementById('favAgenda'); if(fa) fa.innerHTML=agendaHtml('fav');
  const ba=document.getElementById('blkAgenda'); if(ba) ba.innerHTML=agendaHtml('blk');
}
function renderWatch(){
  const box=(kind,el)=>{
    const host=document.getElementById(el); if(!host) return;
    host.innerHTML=loadWatch(kind).map(n=>`<span class="tag ${kind}"><b>${esc(n)}</b><button type="button" onclick="removeWatch('${kind}', '${String(n).replace(/'/g,"\\'")}')">✕</button></span>`).join('')||'<span class="h2hMeta">Vacío</span>';
  };
  box('fav','favList'); box('blk','blkList');
  const fa=document.getElementById('favAgenda'); if(fa) fa.innerHTML=agendaHtml('fav');
  const ba=document.getElementById('blkAgenda'); if(ba) ba.innerHTML=agendaHtml('blk');
}
function isWomensMatchJS(m){
  const vals=[m.liga,m.league,m.competition,m.name,m.pais,m.country,m.sexo,m.gender,m.home,m.away,m.local,m.visita]
    .filter(v=>v!==undefined&&v!==null).map(v=>String(v).toLowerCase()).join(" ");
  return /(women|women's|womens|femen|femin|fem\\.|female|nwsl|women super league|champions league women|uefa women's|liga mx femenil|liga femenina|primera femenina|superliga femenina|primera division femenina|division femenina|women cup|women league|ladies|girls)/i.test(vals)
    || /^(f|female|women|w|femenino|femenina)$/i.test(String(m.sexo||m.gender||"").trim());
}
function decorateWomensRows(){
  document.querySelectorAll("#todayTable tr[data-womens='1']").forEach(tr=>{
    tr.classList.add("womensRow");
  });
}

let activeFilter="men";
let sortDirection="asc";
function rowHtml(m){const star=isTopFlightJS(m)?`<span class="topStar" title="Primera división / competición de élite">★</span>`:"";const cup=isCupJS(m)?`<span class="cupTag" title="Copa / torneo eliminatorio">🏆</span>`:"";const shownStatus=(String(m.estado||"").toLowerCase()==="programado"&&m.hora)?m.hora:(m.estado||"—");const watch=watchFlags(m);return `<tr class="${watch.cls}" data-womens="${isWomensMatchJS(m)?'1':'0'}" data-topflight="${isTopFlightJS(m)?'1':'0'}"><td>${m.n}${watch.mark}</td><td>${esc(m.pais)}</td><td>${star}${cup}${esc(m.liga)}</td><td><b>${esc(m.hora||"—")}</b></td><td><div class="teamCell">${crest(m.logo_l,m.local)}<b>${esc(m.local)}</b></div></td><td><div class="teamCell">${crest(m.logo_v,m.visita)}<b>${esc(m.visita)}</b></div></td><td>${esc(shownStatus)}</td><td><button type="button" class="load" data-n="${m.n}" onclick="return loadMatchByN(${m.n})">📊 Ver estadísticas</button></td></tr>`}
function cardHtml(m){
  const watch=watchFlags(m);
  const shownStatus=(String(m.estado||"").toLowerCase()==="programado"&&m.hora)?m.hora:(m.estado||"—");
  const star=isTopFlightJS(m)?"★ ":"";
  const cup=isCupJS(m)?"🏆 ":"";
  return `<article class="mCard ${watch.cls}"><div class="mCardTop"><span>${esc(m.hora||"—")} PE</span><span>${esc(m.pais||"")}${watch.mark}</span></div><div class="mCardComp">${star}${cup}${esc(m.liga||"")}</div><div class="mCardTeams"><div class="teamCell">${crest(m.logo_l,m.local)}<b>${esc(m.local)}</b></div><div class="teamCell">${crest(m.logo_v,m.visita)}<b>${esc(m.visita)}</b></div></div><button type="button" class="load mCardBtn" onclick="return loadMatchByN(${m.n})">📊 Ver estadísticas</button></article>`;
}
function tableHtml(arr){
  if(!arr.length)return '<div class="emptySection">No hay partidos que coincidan con los filtros actuales.</div>';
  return `<div class="tableScroll"><table><thead><tr><th>#</th><th>País</th><th>Competición</th><th>Hora PE</th><th>Local</th><th>Visitante</th><th>Estado</th><th></th></tr></thead><tbody>${arr.map(rowHtml).join("")}</tbody></table></div><div class="mList">${arr.map(cardHtml).join("")}</div>`;
}
function sectionHtml(title,arr,isWomen){
  return `<div class="sectionTitle ${isWomen?'women':''}"><span>${title}</span><span class="count">${arr.length} partido${arr.length===1?'':'s'}</span></div>${tableHtml(arr)}`;
}
function draw(){
  let term=q.value.toLowerCase(),p=pais.value;
  let arr=ALL_TODAY.filter(m=>(!p||m.pais===p)&&(!term||(m.local+" "+m.visita+" "+m.pais+" "+m.liga).toLowerCase().includes(term)));
  const timeKey=m=>{const h=String(m.hora||"99:99"); const mm=h.match(/^(\d{1,2}):(\d{2})$/); return mm?(Number(mm[1])*60+Number(mm[2])):9999;};
  arr.sort((a,b)=>{const d=timeKey(a)-timeKey(b); if(d!==0)return sortDirection==="asc"?d:-d; return String(a.local||"").localeCompare(String(b.local||""));});
  const womenAll=arr.filter(isWomensMatchJS);
  const men=arr.filter(m=>!isWomensMatchJS(m));
  // Vista principal: solo femenino TOP. Con país elegido, todas las ligas de ese país.
  const women=p?womenAll:womenAll.filter(m=>m.women_top===true);
  let content=`<div class="sub" style="margin-bottom:8px">📅 ${DATE_LABELS[selectedDate]||selectedDate} · ${arr.length} partidos · horarios verificados · <span style="color:#ffd35a;font-weight:800">★ Primera división / élite</span></div>`;
  const favs=arr.filter(m=>watchFlags(m).fav);
  const blks=arr.filter(m=>watchFlags(m).blk);
  if(activeFilter==="women") content+=sectionHtml(p?"🌸 FEMENINO · "+p+" (todas las ligas)":"🌸 FEMENINO TOP",women,true);
  else if(activeFilter==="men") content+=sectionHtml("⚽ PARTIDOS MASCULINOS",men,false);
  else if(activeFilter==="fav") content+=sectionHtml("⭐ PARTIDOS CON FAVORITOS",favs,false);
  else if(activeFilter==="blk") content+=sectionHtml("⛔ PARTIDOS CON LISTA NEGRA",blks,false);
  else content+=sectionHtml("⚽ PARTIDOS MASCULINOS",men,false)+sectionHtml(p?"🌸 FEMENINO · "+p+" (todas las ligas)":"🌸 FEMENINO TOP",women,true);
  document.getElementById("todayTable").innerHTML=content;
  decorateWomensRows();
  loadMissingLogos();
}
function unlockHeaders(){
  document.querySelectorAll("header,.bar,.watchBox,.sectionTitle,.statsModalHead").forEach(el=>{
    el.style.position="static"; el.style.top="auto";
  });
}
function setFilter(f){unlockHeaders();

  activeFilter=f;
  document.querySelectorAll(".filterChip").forEach(b=>b.classList.toggle("on",b.dataset.filter===f));
  draw();
}
document.querySelectorAll(".filterChip").forEach(b=>b.onclick=()=>setFilter(b.dataset.filter));
document.getElementById('sortToggle').onclick=toggleSort;
function refillCountries(){
  const current=pais.value;
  pais.innerHTML='<option value="">Todos los países</option>';
  [...new Set(ALL_TODAY.map(x=>x.pais).filter(Boolean))].sort().forEach(x=>pais.insertAdjacentHTML('beforeend',`<option value="${esc(x)}">${esc(x)}</option>`));
  if([...pais.options].some(o=>o.value===current))pais.value=current;
}
function pad2(n){return String(n).padStart(2,'0')}
function daysInMonth(y,m){return new Date(y,m,0).getDate()}
function fillDateControls(dateStr){
  const [y,m,d]=(dateStr||'2026-09-23').split('-').map(Number);
  const monthEl=document.getElementById('dateMonth');
  const dayEl=document.getElementById('dateDay');
  if(!monthEl.dataset.ready){
    const months=[{v:'2026-09',l:'Septiembre 2026'},{v:'2026-10',l:'Octubre 2026'},{v:'2026-11',l:'Noviembre 2026'}];
    monthEl.innerHTML=months.map(x=>`<option value="${x.v}">${x.l}</option>`).join('');
    monthEl.dataset.ready='1';
  }
  const key=`${y}-${pad2(m)}`;
  if([...monthEl.options].some(o=>o.value===key)) monthEl.value=key;
  const n=daysInMonth(y,m);
  const cur=dayEl.value;
  dayEl.innerHTML=Array.from({length:n},(_,i)=>`<option value="${pad2(i+1)}">${pad2(i+1)}</option>`).join('');
  dayEl.value=pad2(d);
}
function selectedFromControls(){
  const ym=document.getElementById('dateMonth').value||'2026-09';
  const dd=document.getElementById('dateDay').value||'23';
  return ym+'-'+dd;
}
function syncSortButton(){
  const b=document.getElementById('sortToggle');
  if(!b) return;
  b.textContent=sortDirection==='asc'?'↑ INICIO → FIN':'↓ FIN → INICIO';
  b.classList.add('on');
}
function toggleSort(){sortDirection=sortDirection==='asc'?'desc':'asc';syncSortButton();draw();}
async function loadDate(date){
  selectedDate=date;
  fillDateControls(date);
  document.getElementById('todayTable').innerHTML='<div class="panel"><div class="sub">⏳ Cargando calendario verificado en hora Perú…</div></div>';
  try{
    const r=await fetch('/api/calendar?date='+encodeURIComponent(date),{cache:'no-store'});
    if(!r.ok)throw new Error('HTTP '+r.status);
    ALL_TODAY=await r.json();
    if(!Array.isArray(ALL_TODAY)) throw new Error('Respuesta de calendario no válida');
    if(ALL_TODAY.length===0 && FALLBACK_DATES[date]) ALL_TODAY=FALLBACK_DATES[date].map(x=>({...x,fecha:date}));
  }catch(e){
    ALL_TODAY=FALLBACK_DATES[date]?FALLBACK_DATES[date].map(x=>({...x,fecha:date})):[];
    if(!ALL_TODAY.length) document.getElementById('todayTable').innerHTML='<div class="emptySection">No se pudo verificar el calendario de '+(DATE_LABELS[date]||date)+'.</div>';
  }
  refillCountries();
  draw();
}
async function loadWomen(date){
  try{
    const r=await fetch('/api/women-matches?date='+encodeURIComponent(date),{cache:'no-store'});
    if(!r.ok)throw new Error('HTTP '+r.status);
    const women=await r.json();
    if(selectedDate!==date)return;
    const existing=new Set(ALL_TODAY.map(m=>String(m.local||'').trim().toLowerCase()+'|'+String(m.visita||'').trim().toLowerCase()+'|'+String(m.hora||'')));
    const fresh=women.filter(m=>{const key=String(m.local||'').trim().toLowerCase()+'|'+String(m.visita||'').trim().toLowerCase()+'|'+String(m.hora||'');if(existing.has(key))return false;existing.add(key);return true;});
    ALL_TODAY=[...ALL_TODAY,...fresh.map((m,i)=>({...m,n:900000+i+1}))];
    refillCountries();draw();
  }catch(e){console.warn('No se pudo cargar calendario femenino:',e)}
}
document.getElementById('dateMonth').onchange=()=>{const ym=document.getElementById('dateMonth').value;const dayEl=document.getElementById('dateDay');const n=daysInMonth(...ym.split('-').map(Number));const keep=Math.min(Number(dayEl.value||1),n);dayEl.innerHTML=Array.from({length:n},(_,i)=>`<option value="${pad2(i+1)}">${pad2(i+1)}</option>`).join('');dayEl.value=pad2(keep);loadDate(selectedFromControls());};
document.getElementById('dateDay').onchange=()=>loadDate(selectedFromControls());
q.oninput=draw;pais.onchange=draw;refillCountries();draw();
unlockHeaders();renderWatch();syncSortButton();fillDateControls('__TODAY_DATE__');loadDate('__TODAY_DATE__');refreshAgenda();

</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_a):
        return

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, ConnectionError):
            return
        except OSError as e:
            if getattr(e, "winerror", None) in (10053, 10054, 10058, 10038):
                return
            if getattr(e, "errno", None) in (32, 104, 54):
                return
            raise

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, ConnectionError):
            return
        except OSError as e:
            if getattr(e, "winerror", None) in (10053, 10054, 10058, 10038):
                return
            if getattr(e, "errno", None) in (32, 104, 54):
                return
            raise

    def _write_body(self, body):
        """Write a response without printing noisy tracebacks when the browser/client closes early."""
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, ConnectionError, TimeoutError):
            return False
        except OSError as e:
            if getattr(e, "winerror", None) in (10053, 10054, 10058, 10038):
                return False
            if getattr(e, "errno", None) in (32, 104, 54):
                return False
            raise
        return True

    def _send(self, body, content_type="application/json; charset=utf-8", status=200, cache="no-store"):
        if not isinstance(body, (bytes, bytearray)):
            body=str(body).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", cache)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, ConnectionError, OSError):
            return False
        return self._write_body(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = (HTML
                    .replace("__TODAY__", json.dumps(TODAY_22_09, ensure_ascii=False)).replace("__TODAY_DATE__", now_pe().strftime("%Y-%m-%d"))
                    ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self._write_body(body)
            return
        if urllib.parse.urlsplit(self.path).path == "/api/league-table":
            qs=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            lid=int((qs.get("id") or ["274"])[0] or 274)
            body=json.dumps(fotmob_league_table(lid),ensure_ascii=False).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store")
            self._send(body); return
        if urllib.parse.urlsplit(self.path).path == "/api/calendar-range":
            qs=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            raw=(qs.get("dates") or [",".join(NEXT_DAYS)])[0]
            dates=[d.strip() for d in raw.split(",") if d.strip()]
            body=json.dumps(calendar_range(dates),ensure_ascii=False).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store")
            self._send(body); return
        if urllib.parse.urlsplit(self.path).path == "/api/calendar":
            try:
                qs=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                date=(qs.get("date") or ["2026-09-22"])[0]
                rows=calendar_for_date(date)
                # Nunca reutilizar horarios manuales antiguos como si fueran actuales.
                # Si las fuentes no entregan un horario verificable, devolvemos vacío.
                body=json.dumps(rows,ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.end_headers(); self._write_body(body)
            except Exception as e:
                body=json.dumps({"error":str(e)},ensure_ascii=False).encode("utf-8")
                self.send_response(502); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.end_headers(); self._write_body(body)
            return
        if urllib.parse.urlsplit(self.path).path == "/api/women-matches":
            try:
                qs=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                date=(qs.get("date") or ["2026-09-22"])[0]
                body=json.dumps(women_matches_for_date(date),ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.end_headers(); self._write_body(body)
            except Exception as e:
                body=json.dumps({"error":str(e)},ensure_ascii=False).encode("utf-8")
                self.send_response(502); self.send_header("Content-Type","application/json; charset=utf-8"); self.end_headers(); self._write_body(body)
            return
        if urllib.parse.urlsplit(self.path).path == "/api/prematch":
            try:
                qs=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                home=(qs.get("home") or [""])[0].strip(); away=(qs.get("away") or [""])[0].strip(); date=(qs.get("date") or ["2026-09-22"])[0]
                if not home or not away: raise ValueError("Faltan equipos")
                body=json.dumps(prematch_context(home,away,date),ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.end_headers(); self._write_body(body)
            except Exception as e:
                body=json.dumps({"available":False,"error":str(e)},ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.end_headers(); self._write_body(body)
            return
        if urllib.parse.urlsplit(self.path).path == "/api/h2h":
            try:
                qs=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                home=(qs.get("home") or [""])[0].strip(); away=(qs.get("away") or [""])[0].strip()
                if not home or not away: raise ValueError("Faltan equipos")
                h2h=h2h_summary(home,away); h2h["home"]=home; h2h["away"]=away
                body=json.dumps(h2h,ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.end_headers(); self._write_body(body)
            except Exception as e:
                body=json.dumps({"available":False,"has_previous":None,"matches":[],"reason":str(e),"home":home,"away":away},ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.end_headers(); self._write_body(body)
            return
        if urllib.parse.urlsplit(self.path).path == "/api/bettor-prematch":
            try:
                qs=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                home=(qs.get("home") or [""])[0].strip(); away=(qs.get("away") or [""])[0].strip()
                if not home or not away: raise ValueError("Faltan equipos")
                body=json.dumps(bettor_prematch(home,away),ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.end_headers(); self._write_body(body)
            except Exception as e:
                body=json.dumps({"available":False,"error":str(e)},ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.end_headers(); self._write_body(body)
            return
        if urllib.parse.urlsplit(self.path).path == "/api/team-stats":
            try:
                qs=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                home=(qs.get("home") or [""])[0].strip(); away=(qs.get("away") or [""])[0].strip(); limit=min(20,max(5,int((qs.get("limit") or [20])[0])))
                if not home or not away: raise ValueError("Faltan equipos")
                # Consultar ambos equipos en paralelo para que la UI responda mucho antes.
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=2) as pool:
                    fh=pool.submit(summarize_team,home,limit,away)
                    fa=pool.submit(summarize_team,away,limit,home)
                    h=fh.result()
                    a=fa.result()
                sources=sorted(set([h.get("source"),a.get("source")]))
                h["logo"]=resolve_team_logo(home) or logo_for(home); a["logo"]=resolve_team_logo(away) or logo_for(away) or espn_team_logo(away)
                payload={"home":h,"away":a,"source":" + ".join(sources)}
                body=json.dumps(payload,ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.end_headers(); self._write_body(body)
            except Exception as e:
                body=json.dumps({"error":str(e)},ensure_ascii=False).encode("utf-8")
                self.send_response(502); self.send_header("Content-Type","application/json; charset=utf-8"); self.end_headers(); self._write_body(body)
            return
        if urllib.parse.urlsplit(self.path).path == "/api/team-logo":
            try:
                qs=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                name=(qs.get("name") or [""])[0].strip()
                logo=resolve_team_logo(name)
                body=json.dumps({"team":name,"logo":logo},ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","public, max-age=86400"); self.end_headers(); self._write_body(body)
            except Exception:
                body=b'{"logo":""}'
                self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.end_headers(); self._write_body(body)
            return
        if urllib.parse.urlsplit(self.path).path in ("/favicon.svg","/favicon.ico"):
            body=FAVICON_SVG.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type","image/svg+xml; charset=utf-8")
            self.send_header("Cache-Control","public, max-age=86400")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers(); self._write_body(body); return
        if self.path == "/api/matches":
            body = json.dumps(ALL_MATCHES, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self._write_body(body)
            return
        self.send_error(404)

def main():
    threading.Thread(target=_warm_upcoming_calendars, daemon=True).start()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"Prematch Stats Desk → {url}", flush=True)
    if os.environ.get("RENDER") or os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("FLY_APP_NAME"):
        print("Modo servidor: no se abre navegador local.", flush=True)
    else:
        print("Abriendo el navegador...", flush=True)
        threading.Timer(0.8, lambda: webbrowser.open(url.replace("0.0.0.0","127.0.0.1"))).start()
    print("Ctrl+C para salir", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrado.")

if __name__ == "__main__":
    main()
