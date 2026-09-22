### LIBRARY VERSION 2.0 2026/06/23
### Correcciones respecto a v1.0:
###   - Eliminados imports duplicados (random, json, datetime, sleep)
###   - Eliminados imports de Selenium no utilizados
###   - Corregido bug de condición en género (if release_date_gn en lugar de if release_date_dt)
###   - Corregido raise_for_status() — ahora se llama como método
###   - Corregido User-Agent aleatorio real en agentConfirmation()
###   - Eliminado parámetro muerto placetoInsert de rankingGenerator7()
###   - Reemplazado idListMonth.index() por enumerate() para O(n) y correctitud con duplicados
###   - Limpieza de prints de debug comentados y código muerto

import time
import random
import json
import os
import re
import itertools
from datetime import date
from dateutil.relativedelta import relativedelta
from collections import defaultdict, Counter
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from IPython.display import display, HTML


# ─────────────────────────────────────────────
# UTILIDADES DE VISUALIZACIÓN
# ─────────────────────────────────────────────

def displayExtension():
    """Ajusta el ancho del contenedor en Jupyter Notebook al 95%."""
    display(HTML("<style>.container { width:95% !important; }</style>"))
    print("Pantalla completa 2")


# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL AGENTE HTTP
# ─────────────────────────────────────────────

def agentConfirmation():
    """
    Selecciona un User-Agent aleatorio, verifica la conexión al servidor de rankings
    y devuelve los headers listos para usar en requests.
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
    ]

    # FIX v1→v2: el User-Agent aleatorio ahora se aplica también a los headers
    selected_agent = random.choice(user_agents)
    print("User-Agent seleccionado:", selected_agent)

    headers = {"User-Agent": selected_agent}

    response = requests.get("https://www.melon.com/song/detail.htm?songId=2012282", headers=headers)
    print(response)
    return headers


# ─────────────────────────────────────────────
# EXTRACCIÓN DE IDs DESDE HTML LOCAL
# ─────────────────────────────────────────────

def valuesGenerator(fileName):
    """
    Parsea un archivo HTML local del chart de rankings para extraer:
      - Lista de IDs de canciones
      - Fecha del ranking (último día del mes correspondiente)
      - Lista de posiciones de ranking

    Args:
        fileName (str): Nombre del archivo HTML dentro de la carpeta testPages/

    Returns:
        tuple: (values, rankingDate, rankingNumber)
    """
    with open("testPages/" + fileName, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Extraer IDs de canciones
    inputs = soup.find_all("input", class_="input_check")
    values = [tag.get("value") for tag in inputs if tag.get("value")]

    # Extraer año y mes del ranking
    # Algunos HTML tienen el mes en inglés ("June") y en orden distinto al habitual
    MONTH_NAMES = {
        "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
        "july":7,"august":8,"september":9,"october":10,"november":11,"december":12
    }
    rankingYear = rankingMonth = None
    for span in soup.find_all("span", class_="datelk"):
        val = span.text.strip()
        if not val:
            continue
        if val.isdigit() and len(val) == 4:
            rankingYear = int(val)
        elif val.isdigit():
            rankingMonth = int(val)
        elif val.lower() in MONTH_NAMES:
            rankingMonth = MONTH_NAMES[val.lower()]

    if not rankingYear or not rankingMonth:
        raise ValueError(f"No se pudo extraer año/mes de {fileName}. "
                         f"Spans: {[s.text for s in soup.find_all('span', class_='datelk')]}")

    # Calcular el último día del mes de ranking
    rankingDate = date(rankingYear, rankingMonth, 1)
    rankingDate = rankingDate + relativedelta(months=1) - relativedelta(days=1)
    rankingDate = rankingDate.strftime("%Y.%m.%d")

    # Asignar posiciones de ranking (1-based)
    rankingNumber = list(range(1, len(values) + 1))

    return values, rankingDate, rankingNumber


# ─────────────────────────────────────────────
# GENERACIÓN DEL RANKING MENSUAL
# ─────────────────────────────────────────────

def rankingGenerator(idListMonth, datetoInsert, data_historical, headers):
    """
    Combina una lista de IDs mensuales con el historial de canciones ya conocidas.
    Para las canciones no encontradas en el historial, realiza scraping en tiempo real.

    Args:
        idListMonth    (list): IDs de canciones del chart mensual.
        datetoInsert   (str):  Fecha del ranking en formato "YYYY.MM.DD".
        data_historical(list): Lista de dicts con canciones ya conocidas.
        headers        (dict): Headers HTTP para requests.

    Returns:
        list: Lista de dicts con la información completa del ranking.

    Cambios v1→v2:
        - Eliminado parámetro muerto placetoInsert.
        - Reemplazado idListMonth.index() por enumerate() → O(n) y correcto con duplicados.
    """
    monthRankingList = []
    seen_ids = set()
    canciones_nuevas = 0

    # Indexar el historial por ID para búsquedas O(1)
    historical_index = {item["ID"]: item for item in data_historical}

    for ranking_place, monthlyid in enumerate(idListMonth, start=1):
        if monthlyid in seen_ids:
            continue

        if monthlyid in historical_index:
            hist = historical_index[monthlyid]
            monthRankingDict = {
                "ID":           hist["ID"],
                "Artist Title": hist["Artist Title"],
                "Song Title":   hist["Song Title"],
                "Album Title":  hist["Album Title"],
                "Realise Date": hist["Realise Date"],
                "Genre":        hist["Genre"],
                "Lyrics":       hist["Lyrics"],
                "Ranking Date": datetoInsert,
                "Ranking Place": ranking_place
            }
            print(f"ID {ranking_place}, {monthlyid} agregado desde historial.")
            monthRankingList.append(monthRankingDict)
            seen_ids.add(monthlyid)
        else:
            print(f"ID {ranking_place}, {monthlyid} no está en historial. Procediendo a scrap.")
            canciones_nuevas += 1
            indsong = individualSongGenerator(monthlyid, datetoInsert, ranking_place, headers)
            monthRankingList.append(indsong)
            seen_ids.add(monthlyid)

    print(f"Canciones nuevas scrapeadas: {canciones_nuevas}")
    return monthRankingList


# ─────────────────────────────────────────────
# SERIALIZACIÓN Y DIAGNÓSTICO
# ─────────────────────────────────────────────

def listToJson(nombreDelArchivo, nombreDelaLista):
    """
    Guarda una lista de dicts en un archivo JSON con encoding UTF-8.

    Args:
        nombreDelArchivo (str):  Ruta del archivo de salida.
        nombreDelaLista  (list): Lista de dicts a serializar.

    Returns:
        list: La misma lista recibida.
    """
    with open(nombreDelArchivo, "w", encoding="utf-8") as f:
        json.dump(nombreDelaLista, f, ensure_ascii=False, indent=4)
    print("Archivo JSON guardado correctamente.")
    return nombreDelaLista


def scrape_year(meses, master_data, agent, master_json=None):
    """
    Carga o scrappea una lista de meses mensuales del Top-100.

    Para cada mes:
      - Si el JSON ya existe, lo carga directamente (caché).
      - Si no hay HTML disponible en testPages/, avisa y lo omite.
      - Si hay HTML pero no JSON, scrappea y guarda el JSON.

    Args:
        meses       (list): Strings de 6 dígitos, p. ej. ['201301', '201302', ...].
        master_data (list): Acumulado histórico de canciones (se extiende en cada mes).
        agent       (dict): Headers HTTP con User-Agent.
        master_json (str):  Ruta opcional donde guardar el JSON maestro del año.

    Returns:
        list: master_data actualizado con todos los meses procesados.
    """
    SEP = chr(8212) * 50
    for mes in meses:
        year, month = mes[:4], mes[4:]
        json_path = Path(f"jsonfiles/Silver_rankingList_{mes[2:]}.json")
        html_path = Path(f"testPages/{mes}.html")

        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                ranking = json.load(f)
            master_data = master_data + ranking
            print(f'  {year}/{month} ya procesado — cargado desde JSON ({len(ranking)} entradas)')
            continue

        if not html_path.exists():
            print(f'  {year}/{month} sin HTML disponible aún — agrégalo a testPages/ cuando lo tengas')
            continue

        print(SEP)
        print(f'  Procesando: {year} / {month}  |  Historial: {len(master_data)} canciones')
        print(SEP)

        try:
            ids, fecha, _ = valuesGenerator(f'{mes}.html')
            ranking       = rankingGenerator(ids, fecha, master_data, agent)
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            print(f'\n  ⚠ ERROR HTTP {code}: el servidor bloqueó la conexión.')
            print(f'  Scraping detenido en {year}/{month}. Guardando lo acumulado hasta ahora.')
            break
        except requests.exceptions.ConnectionError:
            print(f'\n  ⚠ ERROR de conexión al intentar {year}/{month}.')
            print(f'  Scraping detenido. Guardando lo acumulado hasta ahora.')
            break

        listToJson(f"jsonfiles/Silver_rankingList_{mes[2:]}.json", ranking)

        master_data = master_data + ranking
        print(f'  -> {len(ranking)} entradas agregadas. Total acumulado: {len(master_data)}')

    if master_json:
        listToJson(master_json, master_data)
        print(f'Master data {meses[0][:4]} guardado | {len(master_data)} registros totales')

    return master_data


def checkList(listCheck):
    """
    Imprime los tipos de datos únicos por cada campo en una lista de dicts.
    Útil para detectar inconsistencias de tipos antes de serializar.

    Args:
        listCheck (list): Lista de dicts a inspeccionar.
    """
    types_dict = defaultdict(set)
    for item in listCheck:
        for key, value in item.items():
            types_dict[key].add(type(value))

    for key, types in types_dict.items():
        print(f"{key}: {types}")


# ─────────────────────────────────────────────
# SCRAPING DE CANCIÓN INDIVIDUAL
# ─────────────────────────────────────────────

def individualSongGenerator(song_id, rankingDate, rankingNumber, headers):
    """
    Scrappea el servidor de rankings para obtener la información completa de una canción.

    Args:
        song_id       (str/int): ID de la canción en el ranking.
        rankingDate   (str):     Fecha del ranking en formato "YYYY.MM.DD".
        rankingNumber (int):     Posición en el ranking.
        headers       (dict):    Headers HTTP para requests.

    Returns:
        dict: Información completa de la canción.

    Cambios v1→v2:
        - raise_for_status() ahora se llama correctamente como método.
        - Corregida condición del género: if release_date_gn en lugar de if release_date_dt.
    """
    print(f"Canción {rankingNumber}, id: {song_id}")
    url_cancion = f"https://www.melon.com/song/detail.htm?songId={song_id}"

    wait_time = random.uniform(1, 6)
    print(f"Esperando {wait_time:.2f} segundos...")
    time.sleep(wait_time)

    r = requests.get(url_cancion, headers=headers)
    r.raise_for_status()  # FIX v1→v2: ahora se ejecuta y lanza excepción en errores HTTP

    soup = BeautifulSoup(r.text, "html.parser")

    # PASO 1 — Artista
    artist_name_div = soup.find("div", class_="artist")
    if artist_name_div:
        artist_link = artist_name_div.find("a", class_="artist_name")
        if artist_link:
            artist_title = artist_link.get("title") or artist_link.get_text(strip=True)
        else:
            artist_title = artist_name_div.get_text(strip=True) or "Artista no encontrado"
    else:
        artist_title = "Artista no encontrado"

    # PASO 2 — Título de la canción
    song_name_div = soup.find("div", class_="song_name")
    if song_name_div:
        song_name = song_name_div.get_text(strip=True).replace("곡명", "")
    else:
        song_name = "Título no encontrado"
    print("Song:", song_name)

    # PASO 3 — Álbum
    album_link = soup.select_one("div.meta a")
    album_name = album_link.get_text(strip=True) if album_link else "None"

    # PASO 4 — Fecha de lanzamiento
    release_date_dt = soup.select_one("div.meta dt:-soup-contains('발매일')")
    if release_date_dt:
        release_date_dd = release_date_dt.find_next_sibling("dd")
        release_date = release_date_dd.get_text(strip=True) if release_date_dd else "Fecha no encontrada"
    else:
        release_date = "Fecha no encontrada"
        print("Fecha de lanzamiento no encontrada")

    # PASO 5 — Género
    # FIX v1→v2: condición corregida de `if release_date_dt` a `if release_date_gn`
    release_date_gn = soup.select_one("div.meta dt:-soup-contains('장르')")
    if release_date_gn:
        release_date_gn_dd = release_date_gn.find_next_sibling("dd")
        genero = release_date_gn_dd.get_text(strip=True) if release_date_gn_dd else "Género no encontrado"
    else:
        genero = "Género no encontrado"
        print("Género no encontrado")

    # PASO 6 — Letra
    lyric_div = soup.find("div", {"class": "lyric"})
    if lyric_div:
        for br in lyric_div.find_all("br"):
            br.replace_with("\n")
        lyrics = lyric_div.get_text(strip=True, separator="\n")
    else:
        lyrics = "No lyrics"
        print("No se encontró la letra de la canción")

    return {
        "ID":           song_id,
        "Artist Title": artist_title,
        "Song Title":   song_name,
        "Album Title":  album_name,
        "Realise Date": release_date,
        "Genre":        genero,
        "Lyrics":       lyrics,
        "Ranking Date": rankingDate,
        "Ranking Place": rankingNumber
    }


# ═══════════════════════════════════════════════════════════════════
# ANÁLISIS SEMÁNTICO
# ═══════════════════════════════════════════════════════════════════

def load_months(month_ids, base_path="jsonfiles"):
    """
    Carga múltiples meses de datos desde sus archivos JSON.

    Args:
        month_ids (list): Lista de IDs de mes, ej. ['1001', '1002', ...].
        base_path (str):  Ruta a la carpeta jsonfiles (relativa al CWD).

    Returns:
        list: Lista combinada de todos los registros.
    """
    data = []
    for mes in month_ids:
        path = Path(base_path) / f"Silver_rankingList_{mes}.json"
        if not path.exists():
            print(f"  AVISO: {path} no encontrado, omitiendo")
            continue
        with open(path, "r", encoding="utf-8") as f:
            month_data = json.load(f)
        data += month_data
        print(f"  {mes}: {len(month_data)} entradas cargadas")
    print(f"\nTotal: {len(data)} entradas | {len({s['ID'] for s in data})} canciones únicas")
    return data


def dataset_stats(data):
    """
    Imprime estadísticas básicas de un dataset de canciones.

    Args:
        data (list): Lista de dicts con campos estándar del scraper.
    """
    total        = len(data)
    unique_songs = len({s["ID"] for s in data})
    unique_artists = len({s["Artist Title"] for s in data})
    no_lyrics    = sum(1 for s in data if s.get("Lyrics") in ["No lyrics", "", None])
    genres       = Counter(s.get("Genre", "Desconocido") for s in data)

    dates = sorted({s["Ranking Date"][:7] for s in data if s.get("Ranking Date")})

    print("─" * 40)
    print(f"  Entradas totales  : {total}")
    print(f"  Canciones únicas  : {unique_songs}")
    print(f"  Artistas únicos   : {unique_artists}")
    print(f"  Sin letra         : {no_lyrics} ({no_lyrics/total:.1%})")
    print(f"  Periodo           : {dates[0]} → {dates[-1]}")
    print(f"\n  Top 5 géneros:")
    for genre, count in genres.most_common(5):
        bar = "█" * (count // 10)
        print(f"    {genre:<25} {count:>4}  {bar}")
    print("─" * 40)


def english_ratio_by_month(data):
    """
    Calcula y grafica el porcentaje de caracteres en inglés por mes.
    Sirve para ver si el Konglish (mezcla inglés/coreano) crece con el tiempo.

    Args:
        data (list): Dataset de canciones con campo 'Lyrics' y 'Ranking Date'.

    Returns:
        dict: {mes: ratio_promedio_en_%}
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("Instala matplotlib: pip install matplotlib")
        return {}

    monthly = defaultdict(list)
    for song in data:
        lyrics = song.get("Lyrics", "")
        if lyrics in ["No lyrics", "", None]:
            continue
        korean  = len(re.findall(r"[가-힣]", lyrics))
        english = len(re.findall(r"[a-zA-Z]", lyrics))
        total   = korean + english
        if total == 0:
            continue
        month = song["Ranking Date"][:7]
        monthly[month].append(english / total * 100)

    months = sorted(monthly.keys())
    ratios = [sum(monthly[m]) / len(monthly[m]) for m in months]
    labels = [m[5:] + "/" + m[2:4] for m in months]  # "01/10", "02/10"...

    fig, ax = plt.subplots(figsize=(13, 4))
    ax.plot(labels, ratios, marker="o", linewidth=2, color="#4A90D9", zorder=3)
    ax.fill_between(range(len(labels)), ratios, alpha=0.15, color="#4A90D9")
    ax.set_ylabel("% caracteres en inglés")
    ax.set_title("Ratio inglés/coreano en letras del Top-100")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    plt.tight_layout()
    plt.show()

    print("\nRatio por mes:")
    for m, r in zip(months, ratios):
        bar = "█" * int(r / 1.5)
        print(f"  {m}  {r:5.1f}%  {bar}")

    return dict(zip(months, ratios))


def language_ratio_chart(data):
    """
    Crea dos gráficas de barras apiladas (coreano vs inglés) por mes:
      - Superior: porcentajes (100% apilado), con el % de cada idioma dentro de la barra.
      - Inferior: conteo absoluto de caracteres por idioma.

    Args:
        data (list): Dataset de canciones con 'Lyrics' y 'Ranking Date'.

    Returns:
        dict: {mes: {'korean_pct': float, 'english_pct': float,
                     'korean_chars': int,  'english_chars': int}}
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("Instala matplotlib: pip install matplotlib")
        return {}

    monthly_k = defaultdict(int)
    monthly_e = defaultdict(int)

    for song in data:
        lyrics = song.get("Lyrics", "")
        if lyrics in ["No lyrics", "", None]:
            continue
        month = song["Ranking Date"][:7]
        monthly_k[month] += len(re.findall(r"[가-힣]", lyrics))
        monthly_e[month] += len(re.findall(r"[a-zA-Z]", lyrics))

    months  = sorted(monthly_k.keys())
    labels  = [m[5:] + "/" + m[2:4] for m in months]
    k_chars = [monthly_k[m] for m in months]
    e_chars = [monthly_e[m] for m in months]
    totals  = [k + e for k, e in zip(k_chars, e_chars)]
    k_pct   = [k / t * 100 if t else 100 for k, t in zip(k_chars, totals)]
    e_pct   = [e / t * 100 if t else 0   for e, t in zip(e_chars, totals)]

    COLOR_K = "#4A90D9"
    COLOR_E = "#E8A838"

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    fig.suptitle("Coreano vs Inglés en letras del Top-100", fontsize=13, fontweight="bold")

    # ── Gráfica superior: porcentajes apilados ─────────────────────
    x = range(len(labels))
    b_k = ax1.bar(x, k_pct, color=COLOR_K, label="Coreano 가-힣", zorder=2)
    b_e = ax1.bar(x, e_pct, bottom=k_pct, color=COLOR_E, label="Inglés a-z", zorder=2)

    for bar, pct in zip(b_k, k_pct):
        if pct > 6:
            ax1.text(bar.get_x() + bar.get_width() / 2, pct / 2,
                     f"{pct:.1f}%", ha="center", va="center",
                     fontsize=7.5, color="white", fontweight="bold")

    for bar, kp, ep in zip(b_e, k_pct, e_pct):
        if ep > 3:
            ax1.text(bar.get_x() + bar.get_width() / 2, kp + ep / 2,
                     f"{ep:.1f}%", ha="center", va="center",
                     fontsize=7.5, color="white", fontweight="bold")

    ax1.set_ylabel("% de caracteres")
    ax1.set_ylim(0, 107)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)

    # ── Gráfica inferior: conteo absoluto de caracteres ────────────
    ax2.bar(x, k_chars, color=COLOR_K, label="Coreano 가-힣", zorder=2)
    ax2.bar(x, e_chars, bottom=k_chars, color=COLOR_E, label="Inglés a-z", zorder=2)

    for i, (kc, ec) in enumerate(zip(k_chars, e_chars)):
        ax2.text(i, kc / 2, f"{kc:,}", ha="center", va="center",
                 fontsize=6.5, color="white", fontweight="bold")
        if ec > 500:
            ax2.text(i, kc + ec / 2, f"{ec:,}", ha="center", va="center",
                     fontsize=6.5, color="white", fontweight="bold")

    ax2.set_ylabel("Nº de caracteres")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)

    ax2.set_xticks(list(x))
    ax2.set_xticklabels(labels, rotation=45, ha="right")

    plt.tight_layout()
    plt.show()

    return {
        m: {"korean_pct":   round(kp, 2), "english_pct":   round(ep, 2),
            "korean_chars": kc,           "english_chars": ec}
        for m, kp, ep, kc, ec in zip(months, k_pct, e_pct, k_chars, e_chars)
    }


def compare_years_chart(year_datasets):
    """
    Compara el ratio coreano/inglés entre varios años.

    Subplots:
      1. Barras apiladas por año (resumen global).
      2. Líneas superpuestas Jan–Dic, una por año (comparativa estacional).

    Args:
        year_datasets (dict): {'2009': data_2009, '2010': data_2010, ...}

    Returns:
        dict: {year: {'korean_pct', 'english_pct', 'korean_chars', 'english_chars', 'monthly'}}
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("Instala matplotlib: pip install matplotlib")
        return {}

    COLOR_K   = "#4A90D9"
    COLOR_E   = "#E8A838"
    PALETTE   = ["#4A90D9", "#E8A838", "#5CB85C", "#D9534F", "#9B59B6", "#F0A500"]
    MONTH_LBL = ["Ene","Feb","Mar","Abr","May","Jun",
                 "Jul","Ago","Sep","Oct","Nov","Dic"]

    year_stats = {}
    for year, data in sorted(year_datasets.items()):
        tk = te = 0
        mk, me = defaultdict(int), defaultdict(int)
        for song in data:
            lyrics = song.get("Lyrics", "")
            if lyrics in ["No lyrics", "", None]:
                continue
            rd = song.get("Ranking Date", "")
            if not rd:
                continue
            k = len(re.findall(r"[가-힣]", lyrics))
            e = len(re.findall(r"[a-zA-Z]", lyrics))
            tk += k; te += e
            m_num = int(rd[5:7])
            mk[m_num] += k; me[m_num] += e
        total = tk + te
        year_stats[year] = {
            "korean_pct":    tk / total * 100 if total else 100,
            "english_pct":   te / total * 100 if total else 0,
            "korean_chars":  tk,
            "english_chars": te,
            "monthly": {
                m: me[m] / (mk[m] + me[m]) * 100 if (mk[m] + me[m]) else 0
                for m in range(1, 13)
            }
        }

    years = sorted(year_stats.keys())
    x     = range(len(years))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(max(8, len(years) * 2 + 4), 9))
    fig.suptitle("Comparativa Coreano vs Inglés por Año", fontsize=13, fontweight="bold")

    # ── Subplot 1: barras apiladas por año ───────────────────────────
    k_pcts = [year_stats[y]["korean_pct"]  for y in years]
    e_pcts = [year_stats[y]["english_pct"] for y in years]

    b_k = ax1.bar(x, k_pcts, color=COLOR_K, label="Coreano 가-힣", zorder=2)
    b_e = ax1.bar(x, e_pcts, bottom=k_pcts, color=COLOR_E, label="Inglés a-z", zorder=2)

    for bar, kp in zip(b_k, k_pcts):
        if kp > 5:
            ax1.text(bar.get_x() + bar.get_width() / 2, kp / 2,
                     f"{kp:.1f}%", ha="center", va="center",
                     fontsize=11, color="white", fontweight="bold")
    for bar, kp, ep in zip(b_e, k_pcts, e_pcts):
        if ep > 3:
            ax1.text(bar.get_x() + bar.get_width() / 2, kp + ep / 2,
                     f"{ep:.1f}%", ha="center", va="center",
                     fontsize=11, color="white", fontweight="bold")

    ax1.set_ylabel("% de caracteres")
    ax1.set_ylim(0, 107)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(years, fontsize=11)
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)

    # ── Subplot 2: líneas superpuestas Jan–Dic por año ───────────────
    for i, year in enumerate(years):
        monthly = year_stats[year]["monthly"]
        ys = [monthly[m] for m in range(1, 13)]
        ax2.plot(range(12), ys, marker="o", linewidth=2,
                 color=PALETTE[i % len(PALETTE)], label=year, zorder=3)

    ax2.set_ylabel("% inglés")
    ax2.set_title("Tendencia mensual del ratio inglés por año", fontsize=11)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax2.set_xticks(range(12))
    ax2.set_xticklabels(MONTH_LBL)
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)

    plt.tight_layout()
    plt.show()

    print("\nResumen por año:")
    for year in years:
        s = year_stats[year]
        print(f"  {year}  Coreano: {s['korean_pct']:.1f}%  "
              f"Inglés: {s['english_pct']:.1f}%  "
              f"({s['korean_chars']:,} / {s['english_chars']:,} chars)")

    return year_stats


def top_nouns_by_period(data, period="quarter", top_n=15):
    """
    Extrae los sustantivos más frecuentes por periodo usando kiwipiepy.
    Muestra qué temas y palabras dominaban en cada época.

    Args:
        data    (list): Dataset de canciones.
        period  (str):  'month', 'quarter' o 'year'.
        top_n   (int):  Cuántas palabras mostrar por periodo.

    Returns:
        dict: {periodo: [(palabra, frecuencia), ...]}
    """
    try:
        from kiwipiepy import Kiwi
    except ImportError:
        print("Instala kiwipiepy: pip install kiwipiepy")
        return {}

    kiwi = Kiwi()

    grouped = defaultdict(list)
    for song in data:
        lyrics = song.get("Lyrics", "")
        if lyrics in ["No lyrics", "", None]:
            continue
        rd = song.get("Ranking Date", "")
        if not rd:
            continue
        year  = rd[:4]
        month = int(rd[5:7])
        if period == "quarter":
            key = f"{year} Q{(month - 1) // 3 + 1}"
        elif period == "month":
            key = rd[:7]
        else:
            key = year
        grouped[key].append(lyrics)

    results = {}
    STOP = {"것", "수", "때", "나", "너", "우리", "이", "그", "저", "제"}

    for key in sorted(grouped.keys()):
        all_text = "\n".join(grouped[key])
        nouns = []
        for sent in kiwi.analyze(all_text):
            for token in sent[0]:
                if token.tag.startswith("NN") and token.form not in STOP and len(token.form) > 1:
                    nouns.append(token.form)
        top = Counter(nouns).most_common(top_n)
        results[key] = top
        print(f"\n{key}:")
        for word, freq in top:
            bar = "█" * (freq // 3)
            print(f"  {word:<10} {freq:>4}  {bar}")

    return results


def historical_trend_chart(year_datasets):
    """
    Gráfica continua mes a mes en orden cronológico + resumen por año.

    Subplots:
      1. Barras apiladas 100% coreano/inglés por mes (todos los meses seguidos).
      2. Conteo absoluto de caracteres apilado por mes.
      3. Barras apiladas 100% agregadas por año (una barra por año).

    Líneas divisorias verticales y etiquetas de año separan los bloques en los subplots 1–2.

    Args:
        year_datasets (dict): {'2009': data_2009, '2010': data_2010, ...}

    Returns:
        dict: {'YYYY-MM': {'korean_pct', 'english_pct', 'korean_chars', 'english_chars'}}
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("Instala matplotlib: pip install matplotlib")
        return {}

    MONTH_NAMES = ["Ene","Feb","Mar","Abr","May","Jun",
                   "Jul","Ago","Sep","Oct","Nov","Dic"]
    COLOR_K = "#4A90D9"
    COLOR_E = "#E8A838"

    # ── Agregación mensual ────────────────────────────────────────────
    monthly_k = defaultdict(int)
    monthly_e = defaultdict(int)

    for data in year_datasets.values():
        for song in data:
            lyrics = song.get("Lyrics", "")
            if lyrics in ["No lyrics", "", None]:
                continue
            rd = song.get("Ranking Date", "")
            if not rd:
                continue
            month_key = rd[:4] + "-" + rd[5:7]  # normaliza ambos formatos de fecha
            monthly_k[month_key] += len(re.findall(r"[가-힣]", lyrics))
            monthly_e[month_key] += len(re.findall(r"[a-zA-Z]", lyrics))

    months  = sorted(monthly_k.keys())
    k_chars = [monthly_k[m] for m in months]
    e_chars = [monthly_e[m] for m in months]
    totals  = [k + e for k, e in zip(k_chars, e_chars)]
    k_pct   = [k / t * 100 if t else 100 for k, t in zip(k_chars, totals)]
    e_pct   = [e / t * 100 if t else 0   for e, t in zip(e_chars, totals)]
    labels  = [MONTH_NAMES[int(m[5:7]) - 1] for m in months]

    # Índice donde empieza cada año (para separadores)
    year_starts = {}
    for i, m in enumerate(months):
        yr = m[:4]
        if yr not in year_starts:
            year_starts[yr] = i

    # ── Agregación anual ──────────────────────────────────────────────
    yearly_k = defaultdict(int)
    yearly_e = defaultdict(int)
    for m in months:
        yr = m[:4]
        yearly_k[yr] += monthly_k[m]
        yearly_e[yr] += monthly_e[m]

    yr_keys   = sorted(yearly_k.keys())
    yr_k      = [yearly_k[y] for y in yr_keys]
    yr_e      = [yearly_e[y] for y in yr_keys]
    yr_totals = [k + e for k, e in zip(yr_k, yr_e)]
    yr_kpct   = [k / t * 100 if t else 100 for k, t in zip(yr_k, yr_totals)]
    yr_epct   = [e / t * 100 if t else 0   for e, t in zip(yr_e, yr_totals)]

    # % inglés por mes (para la línea de tendencia)
    e_pct_line = [e / t * 100 if t else 0 for e, t in zip(e_chars, totals)]

    PALETTE = ["#4A90D9", "#E8A838", "#5CB85C", "#D9534F", "#9B59B6", "#F0A500"]

    # ── Figura: 5 subplots ────────────────────────────────────────────
    years_str = "–".join(yr_keys)
    fig = plt.figure(figsize=(max(16, len(months) * 0.65), 21))
    fig.suptitle(
        f"Histórico {years_str}: Coreano vs Inglés en letras del Top-100",
        fontsize=13, fontweight="bold"
    )

    # Subplots 1–3 comparten eje X (meses); subplots 4–5 son independientes (años)
    gs  = fig.add_gridspec(5, 1, height_ratios=[2, 1.3, 2, 1.4, 1.4], hspace=0.55)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax4 = fig.add_subplot(gs[3])
    ax5 = fig.add_subplot(gs[4])

    x = range(len(months))

    def _add_year_separators(ax, top_val, label_offset=0.02):
        for yr, idx in sorted(year_starts.items()):
            if idx > 0:
                ax.axvline(idx - 0.5, color="gray", linestyle="--",
                           linewidth=0.9, alpha=0.5, zorder=1)
            ax.text(idx + 0.15, top_val * (1 + label_offset), yr,
                    fontsize=9, color="#555", fontweight="bold", va="bottom")

    # ── Subplot 1: barras apiladas 100% por mes ───────────────────────
    b_k = ax1.bar(x, k_pct, color=COLOR_K, label="Coreano 가-힣", zorder=2)
    b_e = ax1.bar(x, e_pct, bottom=k_pct, color=COLOR_E, label="Inglés a-z", zorder=2)

    for bar, kp in zip(b_k, k_pct):
        if kp > 8:
            ax1.text(bar.get_x() + bar.get_width() / 2, kp / 2,
                     f"{kp:.0f}%", ha="center", va="center",
                     fontsize=6, color="white", fontweight="bold")
    for bar, kp, ep in zip(b_e, k_pct, e_pct):
        if ep > 4:
            ax1.text(bar.get_x() + bar.get_width() / 2, kp + ep / 2,
                     f"{ep:.0f}%", ha="center", va="center",
                     fontsize=6, color="white", fontweight="bold")

    ax1.set_ylabel("% de caracteres")
    ax1.set_ylim(0, 112)
    ax1.set_title("Proporción coreano/inglés por mes", fontsize=11)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)
    plt.setp(ax1.get_xticklabels(), visible=False)
    _add_year_separators(ax1, top_val=106, label_offset=0)

    # ── Subplot 2: línea continua % inglés por mes ────────────────────
    ax2.plot(list(x), e_pct_line, color=COLOR_E, linewidth=2,
             marker="o", markersize=3.5, zorder=3)
    ax2.fill_between(list(x), e_pct_line, alpha=0.15, color=COLOR_E)

    ax2.set_ylabel("% inglés")
    ax2.set_title("Tendencia continua del ratio inglés (mes a mes)", fontsize=11)
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax2.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)
    plt.setp(ax2.get_xticklabels(), visible=False)
    _add_year_separators(ax2, top_val=max(e_pct_line) if e_pct_line else 1, label_offset=0.05)

    # ── Subplot 3: volumen absoluto por mes ──────────────────────────
    ax3.bar(x, k_chars, color=COLOR_K, label="Coreano 가-힣", zorder=2)
    ax3.bar(x, e_chars, bottom=k_chars, color=COLOR_E, label="Inglés a-z", zorder=2)

    ax3.set_ylabel("Nº de caracteres")
    ax3.set_title("Volumen absoluto por mes", fontsize=11)
    ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
    ax3.legend(loc="upper right", fontsize=9)
    ax3.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)
    ax3.set_xticks(list(x))
    ax3.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    _add_year_separators(ax3, top_val=max(k + e for k, e in zip(k_chars, e_chars)) if k_chars else 1,
                         label_offset=0.03)

    # ── Subplot 4: barras apiladas por año (resumen) ──────────────────
    xyr = range(len(yr_keys))
    bk4 = ax4.bar(xyr, yr_kpct, color=COLOR_K, label="Coreano 가-힣", zorder=2)
    be4 = ax4.bar(xyr, yr_epct, bottom=yr_kpct, color=COLOR_E, label="Inglés a-z", zorder=2)

    for bar, kp in zip(bk4, yr_kpct):
        ax4.text(bar.get_x() + bar.get_width() / 2, kp / 2,
                 f"{kp:.1f}%", ha="center", va="center",
                 fontsize=10, color="white", fontweight="bold")
    for bar, kp, ep in zip(be4, yr_kpct, yr_epct):
        if ep > 2:
            ax4.text(bar.get_x() + bar.get_width() / 2, kp + ep / 2,
                     f"{ep:.1f}%", ha="center", va="center",
                     fontsize=10, color="white", fontweight="bold")

    ax4.set_ylabel("% de caracteres")
    ax4.set_ylim(0, 107)
    ax4.set_title("Resumen por año", fontsize=11)
    ax4.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax4.set_xticks(list(xyr))
    ax4.set_xticklabels(yr_keys, fontsize=11)
    ax4.legend(loc="upper right", fontsize=9)
    ax4.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)

    # ── Subplot 5: línea histórica — un punto por año ────────────────
    yr5      = sorted(yr_keys)
    yr5_epct = [yr_e[i] / yr_totals[i] * 100 if yr_totals[i] else 0
                for i, _ in enumerate(yr5)]

    ax5.plot(range(len(yr5)), yr5_epct, marker="o", linewidth=2.5,
             markersize=8, color=COLOR_E, zorder=3)
    ax5.fill_between(range(len(yr5)), yr5_epct, alpha=0.15, color=COLOR_E)

    for i, (yr, val) in enumerate(zip(yr5, yr5_epct)):
        ax5.text(i, val + max(yr5_epct) * 0.04, f"{val:.1f}%",
                 ha="center", va="bottom", fontsize=10, fontweight="bold", color=COLOR_E)

    ax5.set_ylabel("% inglés")
    ax5.set_title("Tendencia histórica del ratio inglés — por año", fontsize=11)
    ax5.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax5.set_xticks(range(len(yr5)))
    ax5.set_xticklabels(yr5, fontsize=11)
    ax5.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)

    plt.tight_layout()
    plt.show()

    return {
        m: {"korean_pct":   round(kp, 2), "english_pct":   round(ep, 2),
            "korean_chars": kc,           "english_chars": ec}
        for m, kp, ep, kc, ec in zip(months, k_pct, e_pct, k_chars, e_chars)
    }


def wordcloud_by_year(year_datasets, top_n=150):
    """
    Genera un word cloud por año con los sustantivos más frecuentes en las letras.
    Los word clouds se muestran en subplots horizontales, uno por año.

    Requiere:
        pip install kiwipiepy wordcloud

    En Windows la fuente Malgun Gothic (malgun.ttf) se detecta automáticamente.
    En Linux instala: apt install fonts-nanum  y ajusta KOREAN_FONTS.

    Args:
        year_datasets (dict): {'2009': data_2009, '2010': data_2010, ...}
        top_n         (int):  Máximo de palabras por word cloud (default 150).

    Returns:
        dict: {year: {word: freq}}
    """
    try:
        from kiwipiepy import Kiwi
    except ImportError:
        print("Instala kiwipiepy: pip install kiwipiepy")
        return {}
    try:
        from wordcloud import WordCloud
    except ImportError:
        print("Instala wordcloud: pip install wordcloud")
        return {}
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Instala matplotlib: pip install matplotlib")
        return {}

    KOREAN_FONTS = [
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/gulim.ttc",
        "/Library/Fonts/AppleGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    font_path = next((fp for fp in KOREAN_FONTS if Path(fp).exists()), None)
    if font_path is None:
        print("AVISO: no se encontró fuente coreana — los caracteres pueden verse incorrectos.")

    STOP = {"것", "수", "때", "나", "너", "우리", "이", "그", "저", "제", "거", "말"}
    COLORMAPS = ["Blues", "Oranges", "Greens", "Purples", "Reds", "copper"]

    kiwi  = Kiwi()
    years = sorted(year_datasets.keys())
    n     = len(years)

    fig, axes = plt.subplots(1, n, figsize=(7 * n, 6))
    if n == 1:
        axes = [axes]
    fig.suptitle(
        "Word Cloud por Año — Sustantivos en letras del Top-100",
        fontsize=13, fontweight="bold"
    )

    results = {}
    for i, year in enumerate(years):
        print(f"  Analizando {year}...")
        all_lyrics = "\n".join(
            s.get("Lyrics", "") for s in year_datasets[year]
            if s.get("Lyrics") not in ["No lyrics", "", None]
        )
        nouns = []
        for sent in kiwi.analyze(all_lyrics):
            for token in sent[0]:
                if token.tag.startswith("NN") and token.form not in STOP and len(token.form) > 1:
                    nouns.append(token.form)

        freq = dict(Counter(nouns).most_common(top_n))
        results[year] = freq

        wc_kwargs = dict(
            width=900, height=680,
            background_color="white",
            colormap=COLORMAPS[i % len(COLORMAPS)],
            max_words=top_n,
            prefer_horizontal=0.85,
        )
        if font_path:
            wc_kwargs["font_path"] = font_path

        wc = WordCloud(**wc_kwargs).generate_from_frequencies(freq)
        axes[i].imshow(wc, interpolation="bilinear")
        axes[i].axis("off")
        axes[i].set_title(year, fontsize=14, fontweight="bold", pad=12)
        print(f"    Top 5: {list(freq.items())[:5]}")

    plt.tight_layout()
    plt.show()
    return results


def lyric_length_chart(year_datasets):
    """
    Evolución de la longitud promedio de las letras (en caracteres) por mes y por año.
    Panel superior: línea continua mes a mes. Panel inferior: promedio anual por barras.

    Args:
        year_datasets (dict): {"2009": [songs], "2010": [songs], ...}

    Returns:
        dict: {año: promedio_chars_anual}
    """
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    PALETTE = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3",
               "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD"]

    years = sorted(year_datasets.keys())

    # Acumular longitudes por (año, mes)
    bucket = defaultdict(list)   # {(year, month): [len(lyrics), ...]}
    year_all = defaultdict(list) # {year: [len(lyrics), ...]}

    for year in years:
        for song in year_datasets[year]:
            lyrics = song.get("Lyrics", "")
            if lyrics in ["No lyrics", "", None]:
                continue
            rd = song.get("Ranking Date", "")
            if not rd:
                continue
            month = int(rd[5:7])
            bucket[(year, month)].append(len(lyrics))
            year_all[year].append(len(lyrics))

    sorted_keys = sorted(bucket.keys())
    y_avg  = [sum(bucket[k]) / len(bucket[k]) for k in sorted_keys]
    x_idx  = list(range(len(sorted_keys)))
    x_lbls = [f"{k[1]:02d}/{k[0][2:]}" for k in sorted_keys]

    # Posición inicial de cada año en el eje x (para líneas divisorias)
    year_starts = {}
    for i, (yr, _) in enumerate(sorted_keys):
        if yr not in year_starts:
            year_starts[yr] = i

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8),
                                    gridspec_kw={"height_ratios": [2, 1]})
    fig.suptitle("Longitud de letras — evolución temporal",
                 fontsize=14, fontweight="bold")

    # Línea continua por mes
    ax1.plot(x_idx, y_avg, color=PALETTE[0], linewidth=2,
             marker="o", markersize=4, zorder=3)
    ax1.fill_between(x_idx, y_avg, alpha=0.12, color=PALETTE[0])

    ymax = max(y_avg) * 1.12 if y_avg else 1
    ax1.set_ylim(0, ymax)
    for yr, xi in year_starts.items():
        if xi > 0:
            ax1.axvline(xi - 0.5, color="gray", linestyle="--", alpha=0.35, zorder=1)
        end_xi = year_starts.get(
            years[years.index(yr) + 1], len(sorted_keys)
        ) if yr != years[-1] else len(sorted_keys)
        ax1.text((xi + end_xi) / 2, ymax * 0.97,
                 yr, ha="center", fontsize=9, color="gray")

    ax1.set_ylabel("Caracteres promedio / canción")
    ax1.set_xticks(x_idx)
    ax1.set_xticklabels(x_lbls, fontsize=7, rotation=45)
    ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))

    # Barras por año
    year_avgs = [
        (sum(year_all[yr]) / len(year_all[yr])) if year_all[yr] else 0
        for yr in years
    ]
    bars = ax2.bar(years, year_avgs, color=PALETTE[:len(years)], alpha=0.8, zorder=2)
    for bar, val in zip(bars, year_avgs):
        ax2.text(bar.get_x() + bar.get_width() / 2, val * 1.01,
                 f"{val:,.0f}", ha="center", va="bottom", fontsize=10)
    ax2.set_ylabel("Promedio anual (chars)")
    ax2.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))

    plt.tight_layout()
    plt.show()

    print("\nPromedio de caracteres por año:")
    for yr, avg in zip(years, year_avgs):
        print(f"  {yr}: {avg:,.0f} chars")

    return {yr: avg for yr, avg in zip(years, year_avgs)}


def noun_cooccurrence_graph(year_datasets, top_n=25, top_edges=40, min_cooc=3):
    """
    Red de co-ocurrencia de sustantivos: nodos = palabras más frecuentes,
    aristas = co-aparecen en la misma canción.
    Tamaño del nodo ∝ frecuencia; grosor de arista ∝ co-ocurrencia.

    Args:
        year_datasets (dict): {"2009": [songs], ...}
        top_n         (int):  Cuántos sustantivos mostrar por año.
        top_edges     (int):  Máximo de aristas por año.
        min_cooc      (int):  Mínimo de co-ocurrencias para incluir una arista.

    Requiere: pip install networkx kiwipiepy
    """
    try:
        import networkx as nx
    except ImportError:
        print("Instala networkx: pip install networkx")
        return
    try:
        from kiwipiepy import Kiwi
    except ImportError:
        print("Instala kiwipiepy: pip install kiwipiepy")
        return
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import math

    PALETTE = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3",
               "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD"]
    STOP = {"것", "수", "때", "나", "너", "우리", "이", "그", "저", "제", "거", "말"}

    # Fuente coreana: registrar + limpiar caché LRU de findfont + fijar rcParams global
    font_prop = None
    prev_family = plt.rcParams.get("font.family", ["sans-serif"])
    for fp in ("C:/Windows/Fonts/malgun.ttf",
               "/System/Library/Fonts/AppleSDGothicNeo.ttc",
               "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"):
        if os.path.exists(fp):
            fm.fontManager.addfont(fp)
            try:
                fm.fontManager.findfont.cache_clear()
            except AttributeError:
                pass
            # Nombre registrado por matplotlib (puede diferir del nombre del archivo)
            registered = [f for f in fm.fontManager.ttflist
                          if os.path.normcase(f.fname) == os.path.normcase(fp)]
            font_name = registered[0].name if registered else fm.FontProperties(fname=fp).get_name()
            plt.rcParams["font.family"] = font_name
            font_prop = fm.FontProperties(family=font_name, size=9)
            break

    kiwi  = Kiwi()
    years = sorted(year_datasets.keys())
    n     = len(years)
    ncols = min(n, 3)
    nrows = math.ceil(n / ncols)

    fig, axes = plt.subplots(nrows, ncols, figsize=(9 * ncols, 8 * nrows))
    # Normalizar axes a lista plana
    if n == 1:
        axes = [axes]
    elif nrows == 1:
        axes = list(axes)
    else:
        axes = list(axes.flatten())

    fig.suptitle("Red de co-ocurrencia de sustantivos",
                 fontsize=14, fontweight="bold")

    for idx, (year, color) in enumerate(zip(years, itertools.cycle(PALETTE))):
        ax = axes[idx]
        print(f"  Analizando {year}...")
        noun_freq = Counter()
        cooc      = Counter()

        for song in year_datasets[year]:
            lyrics = song.get("Lyrics", "")
            if lyrics in ["No lyrics", "", None]:
                continue
            song_nouns = set()
            for sent in kiwi.analyze(lyrics):
                for token in sent[0]:
                    if (token.tag.startswith("NN")
                            and token.form not in STOP
                            and len(token.form) > 1):
                        song_nouns.add(token.form)
            for w in song_nouns:
                noun_freq[w] += 1
            song_list = sorted(song_nouns)
            for i, a in enumerate(song_list):
                for b in song_list[i + 1:]:
                    cooc[(a, b)] += 1

        top_words = {w for w, _ in noun_freq.most_common(top_n)}

        edges = sorted(
            [(a, b, c) for (a, b), c in cooc.items()
             if a in top_words and b in top_words and c >= min_cooc],
            key=lambda x: -x[2]
        )[:top_edges]

        G = nx.Graph()
        for w in top_words:
            G.add_node(w, freq=noun_freq[w])
        for a, b, w in edges:
            G.add_edge(a, b, weight=w)
        G.remove_nodes_from([v for v in G.nodes() if G.degree(v) == 0])

        pos     = nx.spring_layout(G, k=2.0 / math.sqrt(max(G.number_of_nodes(), 1)),
                                    seed=42)
        node_sz = [G.nodes[v]["freq"] * 25 for v in G.nodes()]
        max_w   = max((d["weight"] for _, _, d in G.edges(data=True)), default=1)
        edge_w  = [d["weight"] / max_w * 4 for _, _, d in G.edges(data=True)]

        nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sz,
                                node_color=color, alpha=0.85)
        nx.draw_networkx_edges(G, pos, ax=ax, width=edge_w,
                                alpha=0.35, edge_color="gray")
        # Etiquetas dibujadas manualmente con FontProperties para soportar coreano en Jupyter
        if font_prop:
            for node, (x, y) in pos.items():
                ax.text(x, y, node, fontproperties=font_prop,
                        ha="center", va="center", zorder=4)
        else:
            nx.draw_networkx_labels(G, pos, ax=ax, font_size=9)
        ax.set_title(year, fontsize=12, fontweight="bold")
        ax.axis("off")

    for ax in axes[n:]:
        ax.axis("off")

    plt.tight_layout()
    plt.show()

    plt.rcParams["font.family"] = prev_family


def topic_model_chart(year_datasets, n_topics=6, top_words=8):
    """
    LDA topic modeling sobre el corpus de letras.
    Panel superior: top palabras por tema.
    Panel inferior: distribución proporcional de temas por año (barras apiladas).

    Args:
        year_datasets (dict): {"2009": [songs], ...}
        n_topics      (int):  Número de temas latentes.
        top_words     (int):  Palabras a mostrar por tema.

    Requiere: pip install scikit-learn kiwipiepy

    Returns:
        dict con lda, vectorizer, doc_topics, doc_year, vocab
    """
    try:
        from kiwipiepy import Kiwi
    except ImportError:
        print("Instala kiwipiepy: pip install kiwipiepy")
        return
    try:
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.decomposition import LatentDirichletAllocation
    except ImportError:
        print("Instala scikit-learn: pip install scikit-learn")
        return
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    PALETTE = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3",
               "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD"]
    STOP = {"것", "수", "때", "나", "너", "우리", "이", "그", "저", "제", "거", "말"}

    # Fuente coreana — addfont + rcParams global para cubrir títulos y etiquetas
    font_prop = None
    prev_family = plt.rcParams.get("font.family", ["sans-serif"])
    for fp in ("C:/Windows/Fonts/malgun.ttf",
               "/System/Library/Fonts/AppleSDGothicNeo.ttc",
               "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"):
        if os.path.exists(fp):
            fm.fontManager.addfont(fp)
            try:
                fm.fontManager.findfont.cache_clear()
            except AttributeError:
                pass
            registered = [f for f in fm.fontManager.ttflist
                          if os.path.normcase(f.fname) == os.path.normcase(fp)]
            font_name = registered[0].name if registered else fm.FontProperties(fname=fp).get_name()
            plt.rcParams["font.family"] = font_name
            font_prop = fm.FontProperties(family=font_name, size=8)
            break

    kiwi  = Kiwi()
    years = sorted(year_datasets.keys())

    # Corpus: un documento por canción, sustantivos únicamente
    corpus   = []
    doc_year = []

    print("Extrayendo sustantivos del corpus...")
    for year in years:
        print(f"  {year}...")
        for song in year_datasets[year]:
            lyrics = song.get("Lyrics", "")
            if lyrics in ["No lyrics", "", None]:
                continue
            nouns = [
                token.form
                for sent in kiwi.analyze(lyrics)
                for token in sent[0]
                if token.tag.startswith("NN")
                and token.form not in STOP
                and len(token.form) > 1
            ]
            if nouns:
                corpus.append(" ".join(nouns))
                doc_year.append(year)

    if not corpus:
        print("Sin datos suficientes para modelado de temas.")
        return

    print(f"Ajustando LDA ({n_topics} temas, {len(corpus)} canciones)...")
    vectorizer = CountVectorizer(max_df=0.95, min_df=3)
    X          = vectorizer.fit_transform(corpus)
    vocab      = vectorizer.get_feature_names_out()

    lda        = LatentDirichletAllocation(
        n_components=n_topics, random_state=42,
        max_iter=20, learning_method="batch"
    )
    doc_topics = lda.fit_transform(X)

    topic_top_word = [vocab[lda.components_[t].argmax()] for t in range(n_topics)]

    # Distribución promedio por año
    year_dist = {
        yr: doc_topics[[i for i, y in enumerate(doc_year) if y == yr]].mean(axis=0)
        if any(y == yr for y in doc_year) else [0.0] * n_topics
        for yr in years
    }

    fig = plt.figure(figsize=(max(16, n_topics * 2.5), 11))
    fig.suptitle(f"Topic Modeling (LDA) — {n_topics} temas latentes",
                 fontsize=14, fontweight="bold")
    gs = fig.add_gridspec(2, n_topics,
                           height_ratios=[2.5, 1], hspace=0.5, wspace=0.5)

    # Panel superior: palabras por tema
    for t in range(n_topics):
        ax   = fig.add_subplot(gs[0, t])
        tidx = lda.components_[t].argsort()[-top_words:]
        w_lbl = [vocab[i] for i in tidx]
        w_val = [lda.components_[t][i] for i in tidx]
        ax.barh(w_lbl, w_val, color=PALETTE[t % len(PALETTE)], alpha=0.85)
        ax.set_title(f"Tema {t + 1}\n({topic_top_word[t]})",
                     fontsize=9, color=PALETTE[t % len(PALETTE)], fontweight="bold")
        ax.tick_params(axis="y", labelsize=8)
        ax.set_xlabel("Peso", fontsize=7)
        if font_prop:
            for lbl in ax.get_yticklabels():
                lbl.set_fontproperties(font_prop)

    # Panel inferior: barras apiladas por año
    ax_stk   = fig.add_subplot(gs[1, :])
    bottoms  = [0.0] * len(years)
    for t in range(n_topics):
        vals = [year_dist[yr][t] for yr in years]
        ax_stk.bar(years, vals, bottom=bottoms,
                   color=PALETTE[t % len(PALETTE)], alpha=0.85,
                   label=f"T{t + 1} {topic_top_word[t]}", zorder=2)
        bottoms = [b + v for b, v in zip(bottoms, vals)]

    ax_stk.set_title("Distribución de temas por año", fontsize=11)
    ax_stk.set_ylabel("Proporción promedio")
    ax_stk.legend(loc="upper right", fontsize=7, ncol=2)
    if font_prop:
        for lbl in ax_stk.get_legend().get_texts():
            lbl.set_fontproperties(font_prop)
    ax_stk.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    plt.rcParams["font.family"] = prev_family
    plt.show()

    return {
        "lda": lda, "vectorizer": vectorizer,
        "doc_topics": doc_topics, "doc_year": doc_year, "vocab": vocab,
    }



# ═══════════════════════════════════════════════════════════════════
# ANÁLISIS GRAMATICAL
# ═══════════════════════════════════════════════════════════════════

_REGEX_SPECIAL = set(r'\.[]()+*?|^${}')


def _is_regex(pattern):
    """True si el patrón contiene caracteres especiales de regex."""
    return any(c in _REGEX_SPECIAL for c in pattern)


def _search_patterns(year_datasets, patterns):
    """
    Busca patrones en el corpus. Función interna compartida por
    grammar_pattern_search y grammar_compare.

    Returns:
        results : {pattern: [(year, title, artist, date, place, line, matches)]}
        freq    : {pattern: Counter({year: n_canciones})}
    """
    compiled = [
        (p, re.compile(p if _is_regex(p) else re.escape(p)))
        for p in patterns
    ]
    results = {p: [] for p in patterns}
    freq    = {p: Counter() for p in patterns}

    for year, data in sorted(year_datasets.items()):
        for song in data:
            lyrics = song.get("Lyrics", "")
            if not lyrics or lyrics in ["No lyrics", ""]:
                continue
            title  = song.get("Song Title",   "?")
            artist = song.get("Artist Title", "?")
            date   = song.get("Ranking Date", "?")
            place  = song.get("Ranking Place", "?")

            for p_str, rgx in compiled:
                first_line = first_matches = None
                for line in lyrics.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    m = rgx.findall(line)
                    if m:
                        first_line, first_matches = line, m
                        break
                if first_line:
                    freq[p_str][year] += 1
                    results[p_str].append(
                        (year, title, artist, date, place, first_line, first_matches)
                    )

    return results, freq


def _korean_font_setup():
    """
    Registra la primera fuente coreana disponible en matplotlib.
    Devuelve (FontProperties | None, familia_previa).
    """
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    prev_family = plt.rcParams.get("font.family", ["sans-serif"])
    for fp in ("C:/Windows/Fonts/malgun.ttf",
               "/System/Library/Fonts/AppleSDGothicNeo.ttc",
               "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"):
        if os.path.exists(fp):
            fm.fontManager.addfont(fp)
            try:
                fm.fontManager.findfont.cache_clear()
            except AttributeError:
                pass
            registered = [f for f in fm.fontManager.ttflist
                          if os.path.normcase(f.fname) == os.path.normcase(fp)]
            font_name = (registered[0].name if registered
                         else fm.FontProperties(fname=fp).get_name())
            plt.rcParams["font.family"] = font_name
            return fm.FontProperties(family=font_name, size=9), prev_family
    return None, prev_family


def grammar_pattern_search(year_datasets, patterns, top_n=10, show_chart=True):
    """
    Busca uno o varios patrones gramaticales en el corpus de letras.

    Cada patrón puede ser:
      - Texto plano  (ej. '아서', '기 때문에') -> busqueda de substring exacto.
      - Regex        (ej. r'[가-힣]+(?:아서|어서)') -> se usa directamente.

    Args:
        year_datasets (dict): {'2009': data_2009, '2010': data_2010, ...}
        patterns      (list): Lista de strings — texto plano o regex.
        top_n         (int):  Maximo de canciones unicas a mostrar por patron.
        show_chart    (bool): Si True, muestra grafica de frecuencia por anno.

    Returns:
        tuple: (results, freq)
            results : {patron: [(year, title, artist, date, place, linea, matches)]}
            freq    : {patron: Counter({year: n_canciones})}
    """
    import matplotlib.pyplot as plt

    results, freq = _search_patterns(year_datasets, patterns)
    years = sorted(year_datasets.keys())

    # ── Tabla de frecuencias ──────────────────────────────────────────
    col_w = max((len(p) for p in patterns), default=8) + 2
    header = f"{'Anno':>6}" + "".join(f"  {p:>{col_w}}" for p in patterns)
    print(header)
    print("─" * len(header))
    totals = {p: 0 for p in patterns}
    for yr in years:
        row = f"{yr:>6}"
        for p in patterns:
            n = freq[p].get(yr, 0)
            totals[p] += n
            row += f"  {n:>{col_w}}"
        print(row)
    print("─" * len(header))
    print(f"{'Total':>6}" + "".join(f"  {totals[p]:>{col_w}}" for p in patterns))

    # ── Grafica de barras agrupadas ───────────────────────────────────
    if show_chart and years:
        PALETTE = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"]
        font_prop, prev_family = _korean_font_setup()

        n_pat = len(patterns)
        width = 0.7 / max(n_pat, 1)
        x = range(len(years))
        fig, ax = plt.subplots(figsize=(max(10, len(years) * 1.8), 5))

        for i, p_str in enumerate(patterns):
            vals = [freq[p_str].get(yr, 0) for yr in years]
            offset = (i - n_pat / 2 + 0.5) * width
            bars = ax.bar([xi + offset for xi in x], vals, width=width,
                          label=p_str, color=PALETTE[i % len(PALETTE)],
                          alpha=0.85, zorder=2)
            for bar, v in zip(bars, vals):
                if v:
                    ax.text(bar.get_x() + bar.get_width() / 2, v + 0.3,
                            str(v), ha="center", va="bottom", fontsize=8,
                            color=PALETTE[i % len(PALETTE)])

        ax.set_xticks(list(x))
        ax.set_xticklabels(years, fontsize=10)
        ax.set_ylabel("Canciones con el patron")
        ax.set_title("Frecuencia de patrones gramaticales por anno")
        legend = ax.legend(fontsize=9)
        if font_prop:
            for t in legend.get_texts():
                t.set_fontproperties(font_prop)
        ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)
        plt.tight_layout()
        plt.show()
        plt.rcParams["font.family"] = prev_family

    # ── Ejemplos por patron ───────────────────────────────────────────
    SEP = "=" * 64
    for p_str in patterns:
        total = sum(freq[p_str].values())
        by_yr = "  ".join(f"{yr}:{freq[p_str].get(yr, 0)}" for yr in years)
        print(f"\n{SEP}")
        print(f"  Patron : {p_str}  ({'regex' if _is_regex(p_str) else 'texto plano'})")
        print(f"  Total  : {total} canciones")
        print(f"  Por anno: {by_yr}")
        print(SEP)
        seen, count = set(), 0
        for year, title, artist, date, place, line, matches in results[p_str]:
            key = (title, artist)
            if key in seen:
                continue
            seen.add(key)
            print(f"\n{count + 1:2}. [{year}]  {title}")
            print(f"     Artista : {artist}")
            print(f"     Ranking : #{place}  ({date})")
            print(f"     Linea   : {line[:90]}")
            print(f"     Forma   : {matches}")
            count += 1
            if count >= top_n:
                break

    return results, freq


def grammar_compare(year_datasets, pattern_a, pattern_b, top_stems=15, top_examples=5):
    """
    Compara dos patrones gramaticales en el corpus.

    Salida en tres bloques:
      1. Grafica dual: dos lineas superpuestas, una por patron, eje X = anno.
      2. Tabla de stems: formas mas frecuentes antes de cada patron, lado a lado.
      3. Ejemplos pareados: top_examples canciones por patron.

    Cada patron puede ser texto plano o regex (misma logica que grammar_pattern_search).

    Args:
        year_datasets (dict): {'2009': data_2009, ...}
        pattern_a     (str):  Primer patron.
        pattern_b     (str):  Segundo patron.
        top_stems     (int):  Cuantos stems mostrar por patron (default 15).
        top_examples  (int):  Cuantos ejemplos pareados mostrar (default 5).

    Returns:
        tuple: (results, freq, stems_a, stems_b)
    """
    import matplotlib.pyplot as plt

    patterns = [pattern_a, pattern_b]
    results, freq = _search_patterns(year_datasets, patterns)
    years = sorted(year_datasets.keys())
    PALETTE = ["#4C72B0", "#DD8452"]

    # ── 1. Grafica de frecuencia dual ─────────────────────────────────
    font_prop, prev_family = _korean_font_setup()

    fig, ax = plt.subplots(figsize=(max(10, len(years) * 1.8), 5))
    for i, p_str in enumerate(patterns):
        vals = [freq[p_str].get(yr, 0) for yr in years]
        ymax = max(vals) if vals else 1
        ax.plot(range(len(years)), vals, marker="o", linewidth=2.5,
                markersize=8, color=PALETTE[i], label=p_str, zorder=3)
        ax.fill_between(range(len(years)), vals, alpha=0.10, color=PALETTE[i])
        for xi, v in enumerate(vals):
            ax.text(xi, v + ymax * 0.03, str(v),
                    ha="center", fontsize=9, color=PALETTE[i], fontweight="bold")

    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years, fontsize=10)
    ax.set_ylabel("Canciones con el patron")
    ax.set_title(f"Comparativa: {pattern_a}  vs  {pattern_b}")
    legend = ax.legend(fontsize=10)
    if font_prop:
        for t in legend.get_texts():
            t.set_fontproperties(font_prop)
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)
    plt.tight_layout()
    plt.show()
    plt.rcParams["font.family"] = prev_family

    # ── 2. Extraccion de stems ────────────────────────────────────────
    def extract_stems(result_list, p_str):
        is_rgx = _is_regex(p_str)
        stems = Counter()
        for _, _, _, _, _, _, matches in result_list:
            for m in matches:
                stem = m[: -len(p_str)] if (not is_rgx and m.endswith(p_str)) else m
                if stem:
                    stems[stem] += 1
        return stems

    stems_a = extract_stems(results[pattern_a], pattern_a)
    stems_b = extract_stems(results[pattern_b], pattern_b)
    top_a   = stems_a.most_common(top_stems)
    top_b   = stems_b.most_common(top_stems)

    col = 30
    SEP = "─" * (col * 2 + 6)
    print(f"\n{SEP}")
    print(f"  {'Stems — ' + pattern_a:<{col}}  {'Stems — ' + pattern_b:<{col}}")
    print(f"  {'─'*col}  {'─'*col}")
    for i in range(max(len(top_a), len(top_b))):
        a_str = f"{top_a[i][0]}: {top_a[i][1]}" if i < len(top_a) else ""
        b_str = f"{top_b[i][0]}: {top_b[i][1]}" if i < len(top_b) else ""
        print(f"  {a_str:<{col}}  {b_str:<{col}}")

    # ── 3. Ejemplos por año (uno por patrón por año) ─────────────────
    def best_per_year(result_list, yr_list):
        """Primer match por año, en orden cronológico."""
        by_year = {}
        for item in result_list:
            yr = item[0]
            if yr not in by_year:
                by_year[yr] = item
        return {yr: by_year[yr] for yr in yr_list if yr in by_year}

    ex_a = best_per_year(results[pattern_a], years)
    ex_b = best_per_year(results[pattern_b], years)
    active_years = [yr for yr in years if yr in ex_a or yr in ex_b]

    print(f"\n{SEP}")
    print(f"  Ejemplos por año  (un ejemplo por patrón por año)")
    print(SEP)
    for yr in active_years:
        row_a = ex_a.get(yr)
        row_b = ex_b.get(yr)
        print(f"\n  ── {yr} ──")
        if row_a:
            _, _, _, _, place, line, _ = row_a
            print(f"  [A] #{place:<3}  {line[:85]}")
        else:
            print(f"  [A]  —  (sin ocurrencias en {yr})")
        if row_b:
            _, _, _, _, place, line, _ = row_b
            print(f"  [B] #{place:<3}  {line[:85]}")
        else:
            print(f"  [B]  —  (sin ocurrencias en {yr})")

    return results, freq, stems_a, stems_b


def song_search(year_datasets, query, field="auto", year=None, top_n=20):
    """
    Buscador de canciones en el corpus.

    Modos de búsqueda (field):
      "auto"   — si query es numérico busca por ID; si es texto busca en letras.
      "id"     — ID exacto de la canción (int o str).
      "lyrics" — patrón en letras (texto plano o regex, igual que grammar_pattern_search).

    Args:
        year_datasets (dict): {"2004": [songs], ...}
        query    (str/int):   ID o patrón a buscar.
        field          (str): "auto" | "id" | "lyrics"
        year   (str/list/None): filtrar por año(s); None = todos.
        top_n          (int): máximo de resultados a mostrar.

    Returns:
        list[dict]: registros de canciones que coinciden.
    """
    query = str(query).strip()

    # ── Detectar modo ─────────────────────────────────────────────────
    if field == "auto":
        field = "id" if query.isdigit() else "lyrics"

    # ── Filtrar años ──────────────────────────────────────────────────
    if year is None:
        datasets = year_datasets
    else:
        keys = [year] if isinstance(year, str) else list(year)
        datasets = {k: year_datasets[k] for k in keys if k in year_datasets}

    SEP = "─" * 70
    matches = []

    # ── Búsqueda por ID ───────────────────────────────────────────────
    if field == "id":
        print(f"Buscando ID = {query} …\n{SEP}")
        for yr, songs in sorted(datasets.items()):
            for song in songs:
                if str(song.get("ID", "")).strip() == query:
                    matches.append((yr, song))
                    if len(matches) >= top_n:
                        break
            if len(matches) >= top_n:
                break

        if not matches:
            print(f"No se encontró ninguna canción con ID {query}.")
            return []

        for yr, song in matches:
            print(f"Año          : {yr}")
            print(f"ID           : {song.get('ID')}")
            print(f"Ranking Date : {song.get('Ranking Date')}")
            print(f"Ranking Place: {song.get('Ranking Place')}")
            print(f"Género       : {song.get('Genre', '—')}")
            print(f"Álbum        : {song.get('Album Title', '—')}")
            lyrics = song.get("Lyrics") or "No lyrics"
            preview = lyrics[:300].replace("\n", " / ")
            print(f"Letra (inicio): {preview} …")
            print(SEP)
        return [s for _, s in matches]

    # ── Búsqueda por artista o título ─────────────────────────────────
    if field in ("artist", "title"):
        json_key   = "Artist Title" if field == "artist" else "Song Title"
        label      = "artista" if field == "artist" else "título"
        compiled   = re.compile(query if _is_regex(query) else re.escape(query),
                                re.IGNORECASE)
        print(f"Buscando {label} «{query}» …\n{SEP}")

        for yr, songs in sorted(datasets.items()):
            for song in songs:
                value = str(song.get(json_key, "") or "")
                if compiled.search(value):
                    matches.append((yr, song))
                    if len(matches) >= top_n:
                        break
            if len(matches) >= top_n:
                break

        if not matches:
            print(f"No se encontró ningún {label} que coincida con «{query}».")
            return []

        print(f"{len(matches)} resultado(s)\n")
        for yr, song in matches:
            lyrics = song.get("Lyrics") or "No lyrics"
            preview = lyrics[:200].replace("\n", " / ")
            print(f"[{yr}] #{song.get('Ranking Place'):<3}  "
                  f"ID: {song.get('ID')}  "
                  f"Fecha: {song.get('Ranking Date')}")
            print(f"  Artista : {song.get('Artist Title', '—')}")
            print(f"  Canción : {song.get('Song Title',   '—')}")
            print(f"  Letra   : {preview} …")
            print()
        return [s for _, s in matches]

    # ── Búsqueda en letras ────────────────────────────────────────────
    compiled = re.compile(query if _is_regex(query) else re.escape(query))
    print(f"Buscando «{query}» en letras …\n{SEP}")

    for yr, songs in sorted(datasets.items()):
        for song in songs:
            lyrics = song.get("Lyrics", "") or ""
            if not lyrics or lyrics == "No lyrics":
                continue
            hit_lines = []
            for line in lyrics.splitlines():
                if compiled.search(line):
                    hit_lines.append(line.strip())
            if hit_lines:
                matches.append((yr, song, hit_lines))
                if len(matches) >= top_n:
                    break
        if len(matches) >= top_n:
            break

    if not matches:
        print(f"No se encontraron coincidencias para «{query}».")
        return []

    print(f"{len(matches)} resultado(s) — mostrando hasta {top_n}\n")
    for yr, song, hit_lines in matches:
        print(f"[{yr}] #{song.get('Ranking Place'):<3}  "
              f"Fecha: {song.get('Ranking Date')}  "
              f"ID: {song.get('ID')}")
        print(f"  Artista : {song.get('Artist Title', '—')}")
        print(f"  Canción : {song.get('Song Title',   '—')}")
        for ln in hit_lines[:3]:
            print(f"  ▶ {ln[:90]}")
        if len(hit_lines) > 3:
            print(f"    … +{len(hit_lines)-3} línea(s) más")
        print()

    return [s for _, s, _ in matches]


def grammar_year_search(year_datasets, pattern, top_stems=15, max_per_year=1):
    """
    Analiza un único patrón gramatical año por año.

    Salida en tres bloques:
      1. Gráfica de frecuencia (canciones con el patrón por año).
      2. Tabla de stems más frecuentes (contexto antes del patrón).
      3. Hasta max_per_year ejemplos por año con artista, canción y línea.

    Args:
        year_datasets (dict): {"2004": [songs], ...}
        pattern       (str):  Patrón a buscar (texto plano o regex).
        top_stems     (int):  Cuántos stems mostrar (default 15).
        max_per_year  (int):  Máximo de ejemplos por año (default 1).

    Returns:
        tuple: (results, freq, stems)
    """
    import matplotlib.pyplot as plt

    results, freq = _search_patterns(year_datasets, [pattern])
    years = sorted(year_datasets.keys())
    font_prop, prev_family = _korean_font_setup()

    # ── 1. Gráfica de frecuencia ──────────────────────────────────────
    vals = [freq[pattern].get(yr, 0) for yr in years]
    total = sum(vals)

    fig, ax = plt.subplots(figsize=(max(10, len(years) * 1.8), 4))
    ax.plot(range(len(years)), vals, marker="o", linewidth=2.5,
            markersize=8, color="#4C72B0", zorder=3)
    ax.fill_between(range(len(years)), vals, alpha=0.12, color="#4C72B0")
    ymax = max(vals) if vals else 1
    for xi, v in enumerate(vals):
        ax.text(xi, v + ymax * 0.04, str(v),
                ha="center", fontsize=9, color="#4C72B0", fontweight="bold")
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years, fontsize=10)
    ax.set_ylabel("Canciones con el patrón")
    ax.set_title(f"Frecuencia de «{pattern}» por año  (total: {total:,} canciones)")
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)
    plt.tight_layout()
    plt.show()
    plt.rcParams["font.family"] = prev_family

    # ── 2. Tabla de stems ─────────────────────────────────────────────
    is_rgx = _is_regex(pattern)
    stems  = Counter()
    for _, _, _, _, _, _, matches in results[pattern]:
        for m in matches:
            stem = m[: -len(pattern)] if (not is_rgx and m.endswith(pattern)) else m
            if stem:
                stems[stem] += 1

    SEP = "─" * 50
    print(f"\n{SEP}")
    print(f"  Stems más frecuentes con «{pattern}»")
    print(SEP)
    for word, cnt in stems.most_common(top_stems):
        bar = "█" * min(int(cnt / max(1, stems.most_common(1)[0][1]) * 20), 20)
        print(f"  {word:<18} {cnt:>5}  {bar}")

    # ── 3. Ejemplos por año (hasta max_per_year) ─────────────────────
    by_year = {}
    for item in results[pattern]:
        yr = item[0]
        if yr not in by_year:
            by_year[yr] = []
        if len(by_year[yr]) < max_per_year:
            by_year[yr].append(item)

    active = [yr for yr in years if yr in by_year]
    lbl = "ejemplo" if max_per_year == 1 else f"máx. {max_per_year} ejemplos"
    print(f"\n{SEP}")
    print(f"  Ejemplos por año  ({lbl})")
    print(SEP)
    for yr in active:
        print(f"\n  ── {yr} ──")
        for _, title, artist, _, place, line, _ in by_year[yr]:
            print(f"  #{place:<3}  {artist}  —  {title}")
            print(f"        {line[:85]}")

    return results, freq, stems


def _get_direct_yt_url(query):
    """Devuelve la URL directa del primer resultado de YouTube usando yt-dlp."""
    import yt_dlp
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)
        if info and info.get("entries"):
            vid_id = info["entries"][0].get("id")
            if vid_id:
                return f"https://www.youtube.com/watch?v={vid_id}"


def _get_yt_video_id(query):
    """Devuelve solo el video_id del primer resultado de YouTube."""
    import yt_dlp
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)
        if info and info.get("entries"):
            return info["entries"][0].get("id")
    return None


def grammar_to_yt_playlist(results, freq, pattern=None, max_per_year=1,
                           token=None, chat_id=None):
    """
    Busca los videos en YouTube para cada canción del resultado de
    grammar_year_search y construye UNA sola URL de playlist temporal.

    La URL tiene el formato:
        https://www.youtube.com/watch_videos?video_ids=ID1,ID2,...

    Imprime la lista de canciones y la URL en el notebook.
    Si token y chat_id están presentes, envía el mensaje a Telegram.

    Args:
        results     (dict):  results devuelto por grammar_year_search.
        freq        (dict):  freq devuelto por grammar_year_search.
        pattern      (str):  patrón (opcional, se auto-detecta si hay uno solo).
        max_per_year (int):  canciones por año incluidas en la playlist.
        token        (str):  token del bot de Telegram (opcional).
        chat_id (str/int):   chat_id de Telegram (opcional).

    Returns:
        str: URL de la playlist generada (o None si no se encontró ningún video).
    """
    if pattern is None:
        keys = list(results.keys())
        if len(keys) != 1:
            raise ValueError(f"Hay {len(keys)} patrones; especifica pattern=")
        pattern = keys[0]

    years = sorted(freq[pattern].keys())

    # Reconstruir ejemplos por año
    by_year = {}
    for item in results[pattern]:
        yr = item[0]
        if yr not in by_year:
            by_year[yr] = []
        if len(by_year[yr]) < max_per_year:
            by_year[yr].append(item)

    active = [yr for yr in years if yr in by_year]
    total_songs = sum(len(v) for v in by_year.values())

    print(f"Buscando {total_songs} videos en YouTube (~{total_songs*2}s)...")

    video_ids = []
    # entries: (display_line, lyric_line)
    entries = []
    n = 1
    for yr in active:
        for _, title, artist, _, place, lyric, _ in by_year[yr]:
            query = f"{artist} {title}"
            vid_id = None
            try:
                vid_id = _get_yt_video_id(query)
            except Exception as e:
                print(f"  ⚠ yt-dlp error ({query[:30]}): {e}")
            if vid_id:
                video_ids.append(vid_id)
                entries.append((f"{n}. [{yr}] {artist} — {title}", lyric[:80]))
                n += 1
            else:
                entries.append((f"?. [{yr}] {artist} — {title}  (no encontrado)", lyric[:80]))

    if not video_ids:
        print("No se encontró ningún video.")
        return None

    playlist_url = f"https://www.youtube.com/watch_videos?video_ids={','.join(video_ids)}"

    # Mostrar en notebook
    print(f"\n🎵 Playlist — patrón: {pattern}\n")
    for track, lyric in entries:
        print(f"  {track}")
        print(f"      \"{lyric}\"")
    print(f"\n▶ {playlist_url}")

    # Enviar a Telegram
    if token and chat_id:
        track_list = "\n".join(
            f"{track}\n  <i>\"{lyric}\"</i>" for track, lyric in entries
        )
        msg = (f"🎵 Playlist — patrón: <b>{pattern}</b>\n\n"
               f"{track_list}\n\n"
               f"▶ {playlist_url}")

        MAX_CHARS = 4000
        chunks, current = [], ""
        for line in msg.splitlines(keepends=True):
            if len(current) + len(line) > MAX_CHARS:
                chunks.append(current)
                current = line
            else:
                current += line
        if current:
            chunks.append(current)

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        for i, chunk in enumerate(chunks):
            resp = requests.post(
                url,
                json={"chat_id": chat_id, "text": chunk,
                      "parse_mode": "HTML",
                      "disable_web_page_preview": i < len(chunks) - 1},
                timeout=15,
            )
            if resp.ok:
                print(f"✓ Chunk {i+1}/{len(chunks)} enviado a Telegram")
            else:
                print(f"✗ Error Telegram: {resp.status_code} — {resp.text[:120]}")

    return playlist_url


def grammar_to_telegram(results, freq, pattern=None,
                        max_per_year=1, token=None, chat_id=None,
                        direct_url=True):
    """
    Formatea la salida de grammar_year_search como mensaje de Telegram y
    la muestra en el notebook. Si token y chat_id están presentes, la envía.

    Args:
        results     (dict):  results devuelto por grammar_year_search.
        freq        (dict):  freq devuelto por grammar_year_search.
        pattern      (str):  patrón buscado (opcional, se auto-detecta si hay uno solo).
        max_per_year (int):  máximo de canciones por año (default 1).
        token        (str):  token del bot de Telegram (opcional).
        chat_id (str/int):   chat_id de Telegram (opcional).
        direct_url  (bool):  True = link directo watch?v= (via yt-dlp, más lento);
                             False = link de búsqueda (instantáneo).

    Returns:
        str: texto completo del mensaje generado.
    """
    from urllib.parse import quote_plus

    # Auto-detectar patrón si no se pasa
    if pattern is None:
        keys = list(results.keys())
        if len(keys) != 1:
            raise ValueError(f"Hay {len(keys)} patrones en results; especifica pattern=")
        pattern = keys[0]

    years = sorted(freq[pattern].keys())
    total = sum(freq[pattern].values())

    # ── Reconstruir ejemplos por año ──────────────────────────────────
    by_year = {}
    for item in results[pattern]:
        yr = item[0]
        if yr not in by_year:
            by_year[yr] = []
        if len(by_year[yr]) < max_per_year:
            by_year[yr].append(item)

    active = [yr for yr in years if yr in by_year]

    # ── Construir bloques de texto ────────────────────────────────────
    header = f"🎵 Patrón: <b>{pattern}</b>  ({total:,} canciones en total)\n"
    blocks = []

    if direct_url:
        total_songs = sum(len(v) for v in by_year.values())
        print(f"Buscando URLs directas en YouTube ({total_songs} canciones, ~{total_songs*2}s)...")

    for yr in active:
        n = freq[pattern].get(yr, 0)
        blk = [f"\n── {yr}  ({n} canciones) ──"]
        for _, title, artist, _, place, line, _ in by_year[yr]:
            query = f"{artist} {title}"
            if direct_url:
                try:
                    yt_url = _get_direct_yt_url(query)
                    if not yt_url:
                        yt_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
                except Exception as e:
                    print(f"  ⚠ yt-dlp error ({query[:30]}): {e}")
                    yt_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            else:
                yt_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            blk.append(f"#{place}  {artist} — {title}")
            blk.append(f'"{line[:80]}"')
            blk.append(f"▶ {yt_url}")
        blocks.append("\n".join(blk))

    full_text = header + "\n".join(blocks)

    # ── Mostrar en notebook ───────────────────────────────────────────
    # Versión limpia sin etiquetas HTML para el print local
    print(full_text.replace("<b>", "").replace("</b>", ""))

    # ── Enviar a Telegram (opcional) ──────────────────────────────────
    if token and chat_id:
        MAX_CHARS = 4000
        chunks = []
        current = ""
        for blk in [header] + blocks:
            if len(current) + len(blk) + 1 > MAX_CHARS:
                chunks.append(current)
                current = blk
            else:
                current += ("\n" if current else "") + blk
        if current:
            chunks.append(current)

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        for i, chunk in enumerate(chunks):
            payload = {
                "chat_id":    chat_id,
                "text":       chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": (i < len(chunks) - 1),
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.ok:
                print(f"  ✓ Chunk {i+1}/{len(chunks)} enviado a Telegram")
            else:
                print(f"  ✗ Error chunk {i+1}: {resp.status_code} — {resp.text[:120]}")

    return full_text


# ── Drift léxico + correlación ranking ────────────────────────────────────

def word_trend_ranking(year_datasets, top_n=15, min_years=3):
    """
    Palabras cuyos sustantivos subieron o bajaron más de frecuencia a lo largo de los años.
    Usa regresión lineal sobre el % de canciones que contienen cada palabra por año.

    Args:
        year_datasets (dict): {"2005": [songs], ...}
        top_n     (int): palabras a mostrar en cada dirección
        min_years (int): mínimo de años en que debe aparecer la palabra
    Returns:
        dict con claves "rising", "falling", "slopes"
    """
    try:
        from kiwipiepy import Kiwi
    except ImportError:
        print("Instala kiwipiepy: pip install kiwipiepy")
        return
    import numpy as np
    import matplotlib.pyplot as plt

    STOP = {"것", "수", "때", "나", "너", "우리", "이", "그", "저", "제", "거", "말"}
    font_prop, prev_family = _korean_font_setup()
    kiwi  = Kiwi()
    years = sorted(year_datasets.keys())

    freq_by_year = {}   # {word: {year: pct_songs}}
    for year, songs in sorted(year_datasets.items()):
        total = len(songs)
        if total == 0:
            continue
        print(f"  {year} …")
        word_count = Counter()
        for song in songs:
            lyrics = song.get("Lyrics", "") or ""
            if not lyrics or lyrics == "No lyrics":
                continue
            seen = set()
            for sent in kiwi.analyze(lyrics):
                for tok in sent[0]:
                    if (tok.tag.startswith("NN")
                            and tok.form not in STOP
                            and len(tok.form) > 1
                            and tok.form not in seen):
                        word_count[tok.form] += 1
                        seen.add(tok.form)
        for word, cnt in word_count.items():
            freq_by_year.setdefault(word, {})[year] = cnt / total * 100

    year_idx = {y: i for i, y in enumerate(years)}
    slopes = {}
    for word, ydata in freq_by_year.items():
        present = [y for y in years if y in ydata]
        if len(present) < min_years:
            continue
        xs = np.array([year_idx[y] for y in present], dtype=float)
        ys = np.array([ydata[y]    for y in present], dtype=float)
        slopes[word] = float(np.polyfit(xs, ys, 1)[0])

    rising  = sorted(slopes, key=lambda w: -slopes[w])[:top_n]
    falling = sorted(slopes, key=lambda w:  slopes[w])[:top_n]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, max(6, top_n * 0.45 + 2)))
    fig.suptitle("Tendencias léxicas — cambio de presencia por año",
                 fontsize=13, fontweight="bold")

    for ax, words, color, title in [
        (ax1, rising,  "#55A868", f"↑ Top {top_n} en ascenso"),
        (ax2, falling, "#C44E52", f"↓ Top {top_n} en descenso"),
    ]:
        vals = [slopes[w] for w in words]
        ax.barh(range(len(words)), vals, color=color, alpha=0.85)
        ax.set_yticks(range(len(words)))
        if font_prop:
            ax.set_yticklabels([""] * len(words))
            for i, w in enumerate(words):
                ax.text(0, i, f" {w}", fontproperties=font_prop,
                        ha="left" if vals[i] >= 0 else "right", va="center", fontsize=9)
        else:
            ax.set_yticklabels(words)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Δ % canciones con la palabra / año")
        ax.axvline(0, color="black", linewidth=0.8)
        ax.invert_yaxis()

    plt.tight_layout()
    plt.show()
    plt.rcParams["font.family"] = prev_family
    return {"rising": rising, "falling": falling, "slopes": slopes}


def rank_word_correlation(year_datasets, words, min_songs=30):
    """
    Correlación de Spearman entre presencia de cada palabra y posición en ranking.
    Negativo = la palabra aparece más en canciones de alto ranking (rank bajo = mejor).

    Args:
        year_datasets (dict): {"2005": [songs], ...}
        words    (list[str]): palabras o morfemas a evaluar
        min_songs      (int): mínimo de apariciones para calcular correlación
    Returns:
        dict {word: {"corr", "p", "n", "hits"}}
    """
    try:
        from scipy import stats
    except ImportError:
        print("Instala scipy: pip install scipy")
        return
    import matplotlib.pyplot as plt

    font_prop, prev_family = _korean_font_setup()

    results = {}
    for word in words:
        presences, ranks = [], []
        for songs in year_datasets.values():
            for song in songs:
                lyrics = song.get("Lyrics", "") or ""
                rank   = song.get("Ranking Place")
                if not rank or not lyrics:
                    continue
                try:
                    rank = int(rank)
                except (ValueError, TypeError):
                    continue
                presences.append(1 if word in lyrics else 0)
                ranks.append(rank)

        hits = sum(presences)
        if len(presences) < min_songs or hits < 5:
            results[word] = {"corr": 0.0, "p": 1.0, "n": len(presences), "hits": hits}
            continue
        corr, p = stats.spearmanr(presences, ranks)
        results[word] = {"corr": float(corr), "p": float(p),
                         "n": len(presences), "hits": hits}

    sorted_words = sorted(results, key=lambda w: results[w]["corr"])
    corrs  = [results[w]["corr"] for w in sorted_words]
    colors = ["#55A868" if c < 0 else "#C44E52" for c in corrs]

    fig, ax = plt.subplots(figsize=(10, max(4, len(words) * 0.6 + 2)))
    ax.barh(range(len(sorted_words)), corrs, color=colors, alpha=0.85)
    ax.set_yticks(range(len(sorted_words)))
    if font_prop:
        ax.set_yticklabels([""] * len(sorted_words))
        span = max(abs(c) for c in corrs) if corrs else 0.01
        for i, w in enumerate(sorted_words):
            ax.text(0, i, f" {w}", fontproperties=font_prop,
                    ha="left" if corrs[i] >= 0 else "right", va="center", fontsize=10)
    else:
        ax.set_yticklabels(sorted_words)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Correlación Spearman  (− = más en top,  + = más en cola)")
    ax.set_title("Correlación presencia de palabra ↔ posición en ranking", fontsize=12)

    span = max(abs(c) for c in corrs) if corrs else 0.01
    for i, w in enumerate(sorted_words):
        r   = results[w]
        sig = ("***" if r["p"] < 0.001 else
               "**"  if r["p"] < 0.01  else
               "*"   if r["p"] < 0.05  else "ns")
        ax.text(span * 1.08, i, f"n={r['hits']:,} {sig}",
                va="center", fontsize=8)

    ax.set_xlim(-span * 1.3, span * 1.5)
    plt.tight_layout()
    plt.show()
    plt.rcParams["font.family"] = prev_family

    print(f"\n{'Palabra':<14} {'Corr':>8} {'p-value':>10} {'Total':>8} {'Con pal.':>10}  Sig")
    print("─" * 58)
    for w in sorted_words:
        r   = results[w]
        sig = ("***" if r["p"] < 0.001 else
               "**"  if r["p"] < 0.01  else
               "*"   if r["p"] < 0.05  else "ns")
        print(f"{w:<14} {r['corr']:>8.4f} {r['p']:>10.4f} {r['n']:>8,} {r['hits']:>10,}  {sig}")
    return results


def repetition_vs_rank(year_datasets):
    """
    Densidad de repetición de letras (líneas únicas / total líneas) vs. posición en ranking.
    Muestra scatter por año y box-plot por decil de ranking.
    Correlación Spearman global: ¿los hooks más repetitivos rankean mejor?

    Args:
        year_datasets (dict): {"2005": [songs], ...}
    Returns:
        dict {"correlation", "p_value", "n_songs"}
    """
    try:
        from scipy import stats
    except ImportError:
        print("Instala scipy: pip install scipy")
        return
    import numpy as np
    import matplotlib.pyplot as plt

    PALETTE = ["#4C72B0","#DD8452","#55A868","#C44E52","#8172B3",
               "#937860","#DA8BC3","#8C8C8C","#CCB974","#64B5CD"]
    _korean_font_setup()   # solo para consistencia visual; no hay texto coreano aquí

    all_ratios, all_ranks, all_years = [], [], []

    for year, songs in sorted(year_datasets.items()):
        for song in songs:
            lyrics = song.get("Lyrics", "") or ""
            rank   = song.get("Ranking Place")
            if not lyrics or lyrics == "No lyrics" or not rank:
                continue
            try:
                rank = int(rank)
            except (ValueError, TypeError):
                continue
            lines = [l.strip() for l in lyrics.split("\n") if l.strip()]
            if len(lines) < 3:
                continue
            all_ratios.append(len(set(lines)) / len(lines))
            all_ranks.append(rank)
            all_years.append(year)

    if not all_ratios:
        print("Sin datos suficientes.")
        return

    corr, p = stats.spearmanr(all_ratios, all_ranks)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Repetición de letras vs. posición en ranking",
                 fontsize=13, fontweight="bold")

    # Scatter
    years_u   = sorted(set(all_years))
    color_map = {y: PALETTE[i % len(PALETTE)] for i, y in enumerate(years_u)}
    for year in years_u:
        xs = [r for r, y in zip(all_ratios, all_years) if y == year]
        ys = [rk for rk, y in zip(all_ranks,  all_years) if y == year]
        ax1.scatter(xs, ys, alpha=0.10, s=7, color=color_map[year], label=year)
    m, b = np.polyfit(all_ratios, all_ranks, 1)
    xline = np.linspace(min(all_ratios), max(all_ratios), 100)
    ax1.plot(xline, m * xline + b, color="black", linewidth=2, zorder=5)
    ax1.set_xlabel("Ratio de unicidad  (1 = sin repetición,  0 = todo repetido)")
    ax1.set_ylabel("Posición en ranking  (1 = mejor)")
    ax1.set_title(f"Spearman r = {corr:.3f}   p = {p:.2e}", fontsize=10)
    ax1.invert_yaxis()

    # Box-plot por decil
    order   = np.argsort(all_ranks)
    deciles = np.array_split(order, 10)
    box_data = [[all_ratios[i] for i in d] for d in deciles]
    dec_labels = [f"{j*10+1}–{(j+1)*10}" for j in range(10)]
    bp = ax2.boxplot(box_data, patch_artist=True,
                     medianprops={"color": "black", "linewidth": 1.5})
    pal_box = ["#55A868"] * 3 + ["#CCB974"] * 4 + ["#C44E52"] * 3
    for patch, col in zip(bp["boxes"], pal_box):
        patch.set_facecolor(col); patch.set_alpha(0.7)
    ax2.set_xticklabels(dec_labels, rotation=45, ha="right")
    ax2.set_xlabel("Decil de ranking  (1–10 = top,  91–100 = cola)")
    ax2.set_ylabel("Ratio de unicidad")
    ax2.set_title("Repetitividad por decil de ranking", fontsize=10)

    plt.tight_layout()
    plt.show()

    # Resumen texto
    n = len(all_ratios)
    top_idx  = order[:max(1, n//10)]
    bot_idx  = order[-max(1, n//10):]
    avg_top  = sum(all_ratios[i] for i in top_idx)  / len(top_idx)
    avg_bot  = sum(all_ratios[i] for i in bot_idx)  / len(bot_idx)
    direction = "más repetitivas" if corr < 0 else "menos repetitivas"
    sig_txt   = "significativa" if p < 0.05 else "NO significativa"

    print(f"\nCanciones analizadas : {n:,}")
    print(f"Ratio promedio top10%: {avg_top:.3f}")
    print(f"Ratio promedio cola10%: {avg_bot:.3f}")
    print(f"Correlación Spearman : r={corr:.4f}  p={p:.2e}  ({sig_txt})")
    print(f"→ Las canciones de alto ranking tienden a ser {direction}.")
    return {"correlation": corr, "p_value": p, "n_songs": n}


def sentiment_by_month(data, model_name="snunlp/KR-FinBert-SC"):
    """
    Clasifica el sentimiento de las letras por mes usando un modelo de HuggingFace.

    Args:
        data       (list): Dataset de canciones.
        model_name (str):  Modelo de HuggingFace para sentimiento coreano.
                           Alternativas: 'monologg/koelectra-base-finetuned-sentiment'

    Returns:
        dict: {mes: {'positive': %, 'negative': %}}
    """
    try:
        from transformers import pipeline
    except ImportError:
        print("Instala transformers: pip install transformers torch")
        return {}

    print(f"Cargando modelo {model_name}...")
    classifier = pipeline("text-classification", model=model_name, truncation=True, max_length=512)

    monthly = defaultdict(list)
    for song in data:
        lyrics = song.get("Lyrics", "")
        if lyrics in ["No lyrics", "", None]:
            continue
        month = song["Ranking Date"][:7]
        # Usamos solo las primeras 200 palabras para no saturar el modelo
        short_lyrics = " ".join(lyrics.split()[:200])
        monthly[month].append(short_lyrics)

    results = {}
    for month in sorted(monthly.keys()):
        print(f"  Analizando {month} ({len(monthly[month])} canciones)...")
        preds = classifier(monthly[month])
        pos = sum(1 for p in preds if p["label"].lower() in ["positive", "pos"]) / len(preds) * 100
        neg = 100 - pos
        results[month] = {"positive": pos, "negative": neg}
        print(f"  {month}  positivo: {pos:.0f}%  negativo: {neg:.0f}%")

    return results
