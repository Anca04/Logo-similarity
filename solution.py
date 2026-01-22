import pandas as pd
import cloudscraper
import socket
import warnings
import os
import threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

from playwright.sync_api import sync_playwright

warnings.filterwarnings("ignore")

PARQUET_FILE = "logos.snappy.parquet"
NUM_DOMAINS_TO_TEST = 4384
TIMEOUT = 12
LOGO_DIR = "logos_downloaded"
MAX_THREADS = 4
PRINT_EVERY = 100

os.makedirs(LOGO_DIR, exist_ok=True)

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "desktop": True}
)

playwright_lock = threading.Lock()

def domain_resolves(domain):
    try:
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False

def get_accessible_url(domain):
    protocols = ["https://", "http://"]
    subdomains = ["", "www.", "www2.", "web.", "app.", "portal."]

    for proto in protocols:
        for sub in subdomains:
            url = f"{proto}{sub}{domain}"
            try:
                r = scraper.get(url, timeout=TIMEOUT, allow_redirects=True)
                if r.status_code == 200:
                    return r.url
            except Exception:
                continue
    return None

def download_logo_html(page_url, domain):
    file_base = os.path.join(LOGO_DIR, domain.replace(".", "_"))

    for ext in [".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"]:
        p = file_base + ext
        if os.path.isfile(p) and os.path.getsize(p) > 200:
            return p

    try:
        r = scraper.get(page_url, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")

        candidates = []

        for img in soup.find_all("img"):
            src = img.get("src") or ""
            alt = img.get("alt") or ""
            cls = " ".join(img.get("class") or [])
            score = 0
            if "logo" in src.lower(): score += 4
            if "logo" in alt.lower(): score += 3
            if "logo" in cls.lower(): score += 2
            if img.get("width") or img.get("height"): score += 1
            if score > 0:
                candidates.append((score, urljoin(page_url, src)))

        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            candidates.append((2, urljoin(page_url, og["content"])))

        icon = soup.find("link", rel=lambda x: x and "icon" in x.lower())
        if icon and icon.get("href"):
            candidates.append((1, urljoin(page_url, icon.get("href"))))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        logo_url = candidates[0][1]

        ext = os.path.splitext(logo_url)[-1].split("?")[0]
        if ext.lower() not in [".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"]:
            ext = ".png"

        path = file_base + ext
        img = scraper.get(logo_url, timeout=TIMEOUT)

        if img.content and len(img.content) > 200:
            with open(path, "wb") as f:
                f.write(img.content)
            return path
    except Exception:
        pass

    return None

def download_logo_js(page_url, domain):
    file_base = os.path.join(LOGO_DIR, domain.replace(".", "_"))

    with playwright_lock:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(page_url, timeout=30000)
                page.wait_for_timeout(3000)

                elements = page.query_selector_all("img, svg")
                best = None
                best_score = -1

                for el in elements:
                    src = (el.get_attribute("src") or "").lower()
                    alt = (el.get_attribute("alt") or "").lower()
                    cls = (el.get_attribute("class") or "").lower()
                    score = 0
                    if "logo" in src: score += 4
                    if "logo" in alt: score += 3
                    if "logo" in cls: score += 2
                    if score > best_score:
                        best_score = score
                        best = el

                if best:
                    src = best.get_attribute("src")
                    if src:
                        logo_url = urljoin(page_url, src)
                        ext = os.path.splitext(logo_url)[-1].split("?")[0]
                        if ext.lower() not in [".png", ".jpg", ".jpeg", ".svg", ".webp"]:
                            ext = ".png"

                        path = file_base + ext
                        img = scraper.get(logo_url, timeout=TIMEOUT)
                        if img.content and len(img.content) > 200:
                            with open(path, "wb") as f:
                                f.write(img.content)
                            browser.close()
                            return path
                browser.close()
        except Exception:
            pass

    return None

def process_domain(domain):
    if not domain_resolves(domain):
        return "NXDOMAIN", False

    url = get_accessible_url(domain)
    if not url:
        return "NO_HTTP", False

    logo = download_logo_html(url, domain)
    if logo:
        return "HTTP_OK", True

    logo = download_logo_js(url, domain)
    if logo:
        return "HTTP_OK", True

    return "HTTP_OK", False

df = pd.read_parquet(PARQUET_FILE)
domains = df["domain"].head(NUM_DOMAINS_TO_TEST).tolist()

processed = 0
http_ok = 0
not_accessible = 0
logos = 0

print(f"Starting processing {len(domains)} domains using {MAX_THREADS} threads...\n")

with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    futures = [executor.submit(process_domain, d) for d in domains]

    for future in as_completed(futures):
        processed += 1
        status, has_logo = future.result()

        if status == "HTTP_OK":
            http_ok += 1
        else:
            not_accessible += 1

        if has_logo:
            logos += 1

        if processed % PRINT_EVERY == 0 or processed == len(domains):
            print(
                f"[{processed}/{len(domains)} | "
                f"{processed/len(domains)*100:.1f}%] "
                f"HTTP_OK={http_ok} | "
                f"Not accessible={not_accessible} | "
                f"Logos={logos}"
            )

print(f"Processed domains: {processed}")
print(f"Websites with HTTP 200: {http_ok}")
print(f"Not accessible: {not_accessible}")
print(f"Logos downloaded: {logos}")