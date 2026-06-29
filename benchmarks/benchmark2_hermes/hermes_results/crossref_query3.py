import sys, json, urllib.request, urllib.parse, re

# Search for papers with downloadable PDF links
queries = [
    "forest fire risk assessment himalayas pdf",
    "wildfire management western himalayas pdf",
    "forest fire nilgiris pdf",
    "india wildfire intervention pdf",
    "forest fire community management india pdf",
]

for q in queries:
    url = f"https://api.crossref.org/works?query={urllib.parse.quote(q)}&rows=10&select=DOI,title,URL,ISSN,container-title,type,publisher"
    try:
        resp = urllib.request.urlopen(url, timeout=20)
        data = json.load(resp)
        items = data.get("message", {}).get("items", [])
        print(f"\n=== Query: {q} ===")
        for m in items:
            doi = m.get("DOI", "")
            title = m.get("title", [""])[0] if m.get("title") else ""
            pub = m.get("publisher", "")
            container = m.get("container-title", [""])[0] if m.get("container-title") else ""
            typ = m.get("type", "")
            if title and ("journal" in typ or "book" in typ):
                print(f"  {title}")
                print(f"    DOI: {doi} | Publisher: {pub} | Journal: {container}")
    except Exception as e:
        print(f"  Error: {e}")
