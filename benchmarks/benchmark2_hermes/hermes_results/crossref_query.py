import sys, json, urllib.request

queries = [
    "wildfire nilgiris india",
    "himalayan forest fire management",
    "india forest fire prevention intervention",
]

for q in queries:
    url = f"https://api.crossref.org/works?query={urllib.request.quote(q)}&rows=15&select=DOI,title,URL"
    try:
        resp = urllib.request.urlopen(url, timeout=20)
        data = json.load(resp)
        items = data.get("message", {}).get("items", [])
        print(f"\n=== Query: {q} ===")
        for m in items:
            doi = m.get("DOI", "")
            title = m.get("title", [""])[0] if m.get("title") else ""
            if title:
                print(f"  {title}")
                print(f"    DOI: {doi}")
    except Exception as e:
        print(f"  Error: {e}")
