import os, re, json, time, asyncio, io
import httpx
from bs4 import BeautifulSoup
from pathlib import Path
import pdfplumber
import pandas as pd
from tqdm import tqdm

BASE_DIR = Path(__file__).parent
DATA = BASE_DIR / "data"
PLANS = BASE_DIR / "plans"
DATA.mkdir(exist_ok=True, parents=True)
PLANS.mkdir(exist_ok=True, parents=True)

PROGRAM_URLS = {
    "ai": "https://abit.itmo.ru/program/master/ai",
    "ai_product": "https://abit.itmo.ru/program/master/ai_product",
}

HEADERS = {"User-Agent":"Mozilla/5.0"}

def extract_visible_text(html:str)->str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script","style","noscript"]): tag.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    return text

def find_plan_links(html:str)->list[str]:
    # Грубый поиск pdf/plan ссылок
    hrefs = re.findall(r'href="([^"]+)"', html, re.I)
    pdfs = [h for h in hrefs if h.lower().endswith(".pdf")]
    # иногда кнопка генерит ссылку с query
    pdfs += [h for h in hrefs if "plan" in h.lower() or "учеб" in h.lower()]
    # уникальные, абсолютные
    out = []
    for h in pdfs:
        if h.startswith("//"): h = "https:" + h
        if h.startswith("/"): h = "https://abit.itmo.ru" + h
        out.append(h)
    return list(dict.fromkeys(out))

async def fetch(client, url):
    r = await client.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r

async def scrape_program(slug, url):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await fetch(client, url)
        html = r.text
        text = extract_visible_text(html)
        plan_links = find_plan_links(html)
        res = {"slug":slug,"url":url,"text":text,"plan_candidates":plan_links}
        # Сохраняем сырые данные
        (DATA / f"{slug}.raw.txt").write_text(text, encoding="utf-8")
        json.dump(res, open(DATA / f"{slug}.raw.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
        return res

def parse_pdf_tables_to_json(pdf_path:Path)->dict:
    out = {"file": pdf_path.name, "tables": [], "fulltext": ""}
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            out["fulltext"] += page.extract_text() or "" + "\n"
            tbl = page.extract_table()
            if tbl:
                out["tables"].append(tbl)
    return out

def save_tables_as_csv(tables, basepath:Path):
    for i, tbl in enumerate(tables):
        # normalize jagged rows
        maxlen = max(len(r) for r in tbl)
        rows = [ (r + [""]*(maxlen-len(r))) for r in tbl ]
        df = pd.DataFrame(rows)
        df.to_csv(basepath.with_suffix(f".table{i+1}.csv"), index=False)

async def main():
    results = []
    for slug, url in PROGRAM_URLS.items():
        results.append(await scrape_program(slug, url))

    # Пытаемся скачать PDF учебных планов из найденных кандидатов
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for r in results:
            for link in r["plan_candidates"]:
                if not link.lower().endswith(".pdf"):
                    continue
                fname = PLANS / f"{r['slug']}_{os.path.basename(link).split('?')[0]}"
                if fname.exists(): 
                    continue
                try:
                    pdf = await fetch(client, link)
                    fname.write_bytes(pdf.content)
                    print("Saved plan PDF:", fname.name)
                    parsed = parse_pdf_tables_to_json(fname)
                    json.dump(parsed, open(PLANS / f"{fname.stem}.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
                    save_tables_as_csv(parsed["tables"], PLANS / fname.stem)
                except Exception as e:
                    print("Failed to fetch plan:", link, e)

    # Если прямых PDF не нашли, подсказываем про Playwright
    hint = (BASE_DIR/"docs"/"plan_parsing_hint.md")
    hint.write_text("""
Если PDF «Учебный план» не находится прямой ссылкой, запустите headless‑браузер:
  playwright install chromium
  python playwright_click.py

Скрипт кликнет по кнопке «Скачать учебный план» и сохранит PDF в папку plans.
""", encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())