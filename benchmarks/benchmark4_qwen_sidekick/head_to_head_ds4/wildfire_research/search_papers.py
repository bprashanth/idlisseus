import requests, json, sys, os, time, urllib.parse, re
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTDIR = os.path.expanduser("~/wildfire-research/papers")
os.makedirs(OUTDIR, exist_ok=True)

def fetch(url, label=""):
    try:
        r = requests.get(url, headers={"User-Agent": "HermesAgent/1.0"}, timeout=30)
        if r.status_code == 200:
            print(f"  OK  {label or url}")
            return r.json() if 'json' in r.headers.get('content-type','').lower() else r.text
        else:
            print(f"  ERR {label or url} (status {r.status_code})")
            return None
    except Exception as e:
        print(f"  ERR {label or url}: {e}")
        return None

def save_pdf(url, filename):
    """Attempt to save PDF from URL"""
    try:
        r = requests.get(url, headers={"User-Agent": "HermesAgent/1.0"}, timeout=60)
        if r.status_code == 200 and 'application/pdf' in r.headers.get('content-type','').lower():
            path = os.path.join(OUTDIR, filename)
            with open(path, 'wb') as f:
                f.write(r.content)
            print(f"  SAVED {filename} ({len(r.content)} bytes)")
            return path
        return None
    except Exception as e:
        print(f"  ERR saving {filename}: {e}")
        return None

def save_text(content, filename):
    path = os.path.join(OUTDIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  SAVED {filename} ({len(content)} bytes)")
    return path

# ─── QUERY 1: Zenodo API ───
def query_zenodo(query, size=25):
    url = f"https://zenodo.org/api/records?q={urllib.parse.quote(query)}&size={size}&sort=most_relevant"
    data = fetch(url, "Zenodo API")
    if not data:
        return []
    results = []
    for rec in data.get('hits',{}).get('hits',[]):
        title = rec.get('metadata',{}).get('title','')
        doi = rec.get('doi','')
        pub_date = rec.get('metadata',{}).get('publication_date','')
        # Look for PDF files
        files = rec.get('files',[])
        pdf_url = None
        for f in files:
            if f.get('type','') == 'pdf' or f['key'].endswith('.pdf'):
                pdf_url = f['links'].get('self','')
                break
        # Fallback: full text download
        if not pdf_url:
            pdf_url = rec.get('links',{}).get('self','')
        results.append({
            'title': title,
            'doi': doi,
            'date': pub_date,
            'pdf_url': pdf_url,
            'source': 'zenodo',
            'id': rec.get('record_id',''),
        })
    return results

# ─── QUERY 2: CrossRef API ───
def query_crossref(query, rows=25):
    url = f"https://api.crossref.org/works?query={urllib.parse.quote(query)}&rows={rows}&select=title,DOI,author,date,abstract,link"
    data = fetch(url, "CrossRef API")
    if not data:
        return []
    results = []
    for item in data.get('message',{}).get('items',[]):
        title = item.get('title',[''])[0] if item.get('title') else ''
        doi = item.get('DOI','')
        date = item.get('date',{}).get('date-parts',[[0]])[0]
        date_str = '-'.join(str(x) for x in date) if isinstance(date, list) else str(date)
        # Look for PDF links
        pdf_url = None
        for link in item.get('link',[]):
            if link.get('content-type','').startswith('application/pdf'):
                pdf_url = link.get('URL','')
                break
        results.append({
            'title': title,
            'doi': doi,
            'date': date_str,
            'pdf_url': pdf_url,
            'source': 'crossref',
        })
    return results

# ─── QUERY 3: EuropePMC API ───
def query_europepmc(query, size=25):
    url = f"https://www.ebi.ac.uk/europepmc/api/search?query={urllib.parse.quote(query)}&pageSize={size}&resultType=relevance"
    data = fetch(url, "EuropePMC API")
    if not data:
        return []
    results = []
    for item in data.get('resultList',{}).get('result',[]):
        title = item.get('title','')
        doi = item.get('doi','')
        pub_date = item.get('firstPublicationDate','')
        pdf_url = item.get('fullTextUrl','') or ''
        results.append({
            'title': title,
            'doi': doi,
            'date': pub_date,
            'pdf_url': pdf_url,
            'source': 'europepmc',
        })
    return results

# ─── QUERIES ───
queries = [
    "wildfire risk Nilgiris forest fire management",
    "Himalayan forest fire intervention prescribed burning",
    "India wildfire mitigation fuel management",
    "Western Ghats forest fire ecology prevention",
    "Uttarakhand forest fire controlled burning",
    "community-based wildfire management South Asia",
    "fire line construction India forest fire prevention",
    "forest fire early warning system India satellite",
    "biomass fuel load management India forests",
    "Indigenous fire knowledge Nilgiris Himalaya",
    "forest fire policy India review",
]

all_results = []
for q in queries:
    print(f"\nQuery: {q}")
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(query_zenodo, q): 'zenodo',
            ex.submit(query_crossref, q): 'crossref',
            ex.submit(query_europepmc, q): 'europepmc',
        }
        for f in as_completed(futures):
            src = futures[f]
            try:
                res = f.result()
                print(f"  {src}: {len(res)} results")
                all_results.extend(res)
            except Exception as e:
                print(f"  {src} ERROR: {e}")

# Deduplicate by DOI
seen_dois = set()
unique = []
for r in all_results:
    key = r.get('doi','') or r.get('title','')
    if key and key not in seen_dois:
        seen_dois.add(key)
        unique.append(r)

print(f"\nTotal unique results: {len(unique)}")
print("\n=== RESULTS ===")
for i, r in enumerate(unique[:30]):
    print(f"{i+1}. {r['title'][:80]} | DOI: {r.get('doi','-')[:50]} | {r['source']} | PDF: {r.get('pdf_url','-')[:60]}")

# Save results as JSON
save_text(json.dumps(unique, indent=2, ensure_ascii=False), "search_results.json")
print("\nSaved search_results.json")
