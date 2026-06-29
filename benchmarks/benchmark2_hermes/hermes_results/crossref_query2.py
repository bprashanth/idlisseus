import sys, json, urllib.request, urllib.parse

# More targeted queries for interventions
queries = [
    "prescribed burning himalayan forest fire",
    "community based forest fire management india",
    "fuel management forest fire india",
    "forest fire risk mitigation himalayas",
    "wildfire intervention effectiveness india",
    "forest fire regime western himalayas",
    "nilgiris fire ecology management",
]

for q in queries:
    url = f"https://api.crossref.org/works?query={urllib.parse.quote(q)}&rows=10&select=DOI,title,URL,abstract"
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
                # Try to get abstract
                abs = m.get("abstract", "")
                if abs:
                    print(f"    Abstract: {abs[:200]}...")
    except Exception as e:
        print(f"  Error: {e}")
