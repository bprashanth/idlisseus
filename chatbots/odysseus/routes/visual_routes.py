"""Visual result proxy — the browser-side gateway to per-site result services.

The visual stage (static/js/visual/) renders idli-result/1 envelopes. Envelopes
and their immutable data payloads are produced by the benchmark-owned bridge
behind a registered ModelEndpoint. This proxy:

  * confines the browser to endpoints registered in the ModelEndpoint table
    (never arbitrary URLs), and
  * keeps bridge bearer tokens server-side.

Routes (auth enforced by the global AuthMiddleware like every /api route):
  GET  /api/visual/{endpoint_id}/capabilities
  GET  /api/visual/{endpoint_id}/decision-maps
  POST /api/visual/{endpoint_id}/query
  GET  /api/visual/{endpoint_id}/results/{result_id}
  GET  /api/visual/{endpoint_id}/results/{result_id}/data/{handle}
"""

import json
import pathlib
import re

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from core.database import SessionLocal, ModelEndpoint

_SAFE_ID = re.compile(r"^[A-Za-z0-9_.\-]{1,200}$")
_TIMEOUT = httpx.Timeout(20.0, connect=5.0)


def _bridge_target(endpoint_id: str) -> tuple[str, dict]:
    """Resolve a registered endpoint id to its bridge origin and auth headers."""
    db = SessionLocal()
    try:
        ep = db.query(ModelEndpoint).filter(ModelEndpoint.id == endpoint_id).first()
    finally:
        db.close()
    if not ep or not ep.is_enabled:
        raise HTTPException(status_code=404, detail="unknown endpoint")
    base = (ep.base_url or "").rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    if not base.startswith(("http://", "https://")):
        raise HTTPException(status_code=502, detail="endpoint has no usable base URL")
    headers = {}
    if ep.api_key:
        headers["Authorization"] = f"Bearer {ep.api_key}"
    return base, headers


def _forward(resp: httpx.Response) -> Response:
    media = resp.headers.get("content-type", "application/json")
    out = Response(content=resp.content, status_code=resp.status_code, media_type=media)
    cache = resp.headers.get("cache-control")
    if cache:
        out.headers["Cache-Control"] = cache
    return out


TILE_SOURCES = {
    # Basemaps. Tiles are proxied same-origin (CSP: img-src 'self') and
    # disk-cached; attribution is rendered by the map UI whenever a basemap is on.
    "terrain": "https://tile.opentopomap.org/{z}/{x}/{y}.png",
    "osm": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    # Esri World Imagery (satellite; vegetation visible). Note the y/x order.
    "imagery": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
}
TILE_CACHE = pathlib.Path("data/tile-cache")
TILE_MAX_ZOOM = 15

# Public DOI metadata registries, for turning a source's DOI into the people
# credited with it (IDL-REQ-0004 asks the producer to publish these directly;
# until it does, they are resolvable from the DOIs the producer already ships).
# No API key is involved and no other host may be reached from here.
DOI_REGISTRIES = (
    ("datacite", "https://api.datacite.org/dois/{doi}"),
    ("crossref", "https://api.crossref.org/works/{doi}"),
)
DOI_CACHE = pathlib.Path("data/doi-authors")
_SAFE_DOI = re.compile(r"^10\.[0-9]{4,9}/[A-Za-z0-9._;()/:+-]{1,180}$")
_DOI_UA = "idli-insights/1.0 (+https://chat.idli.cc)"


def setup_visual_routes():
    router = APIRouter(prefix="/api/visual")

    @router.get("/tiles/{source}/{z}/{x}/{y}.png")
    def tile(source: str, z: int, x: int, y: int):
        template = TILE_SOURCES.get(source)
        if not template:
            raise HTTPException(status_code=404, detail="unknown tile source")
        if not (0 <= z <= TILE_MAX_ZOOM and 0 <= x < 2 ** z and 0 <= y < 2 ** z):
            raise HTTPException(status_code=400, detail="bad tile address")
        cached = TILE_CACHE / source / str(z) / str(x) / f"{y}.png"
        if cached.is_file():
            return Response(cached.read_bytes(), media_type="image/png",
                            headers={"Cache-Control": "public, max-age=604800"})
        url = template.format(z=z, x=x, y=y)
        try:
            r = httpx.get(url, timeout=_TIMEOUT,
                          headers={"User-Agent": "Idlisseus/1.0 (self-hosted visual stage)"})
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"tile fetch failed: {type(exc).__name__}")
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"tile upstream {r.status_code}")
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(r.content)
        return Response(r.content, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=604800"})

    def _get(endpoint_id: str, path: str) -> Response:
        if not _SAFE_ID.fullmatch(endpoint_id):
            raise HTTPException(status_code=400, detail="bad endpoint id")
        base, headers = _bridge_target(endpoint_id)
        try:
            r = httpx.get(f"{base}{path}", headers=headers, timeout=_TIMEOUT)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"bridge unreachable: {type(exc).__name__}")
        return _forward(r)

    def _norm(url: str) -> str:
        u = (url or "").rstrip("/")
        for suffix in ("/chat/completions", "/completions"):
            if u.endswith(suffix):
                u = u[: -len(suffix)]
        return u.rstrip("/")

    @router.get("/resolve")
    def resolve(endpoint_url: str = ""):
        """Map a session's endpoint_url (chat URL or base) to its registered endpoint id."""
        target = _norm(endpoint_url)
        if not target:
            raise HTTPException(status_code=400, detail="endpoint_url required")
        db = SessionLocal()
        try:
            rows = db.query(ModelEndpoint).filter(ModelEndpoint.is_enabled == True).all()  # noqa: E712
            for ep in rows:
                if _norm(ep.base_url) == target:
                    return {"endpoint_id": ep.id, "name": ep.name}
        finally:
            db.close()
        raise HTTPException(status_code=404, detail="no registered endpoint for that URL")

    @router.get("/doi-authors")
    def doi_authors(doi: str):
        """People credited with a DOI, for the site-selection view.

        The producer publishes each source's DOI but not its authors, and a
        contributor view that invented names would be worse than no view at
        all — so the names come from the public registries that mint those
        DOIs, cached on disk. Names, affiliations and ORCIDs only; an
        unresolvable DOI answers with an empty list, never a guess.
        """
        doi = (doi or "").strip().lower().removeprefix("https://doi.org/").removeprefix("doi:")
        if not _SAFE_DOI.fullmatch(doi):
            raise HTTPException(status_code=400, detail="bad doi")
        cached = DOI_CACHE / f"{doi.replace('/', '_')}.json"
        if cached.is_file():
            return Response(cached.read_text(), media_type="application/json",
                            headers={"Cache-Control": "public, max-age=604800"})
        people: list[dict] = []
        for kind, template in DOI_REGISTRIES:
            try:
                r = httpx.get(template.format(doi=doi), timeout=_TIMEOUT,
                              headers={"User-Agent": _DOI_UA, "Accept": "application/json"})
                if r.status_code != 200:
                    continue
                body = r.json()
            except Exception:
                continue
            if kind == "datacite":
                raw = ((body.get("data") or {}).get("attributes") or {}).get("creators") or []
            else:
                raw = (body.get("message") or {}).get("author") or []
            for c in raw:
                name = (c.get("name")
                        or " ".join(x for x in (c.get("given"), c.get("family")) if x)).strip()
                if not name:
                    continue
                # Registries store "Family, Given"; people read "Given Family".
                if "," in name and c.get("nameType", "Personal") == "Personal":
                    family, _, given = name.partition(",")
                    name = f"{given.strip()} {family.strip()}".strip()
                affiliation = c.get("affiliation")
                if isinstance(affiliation, list):
                    affiliation = next(
                        (a.get("name") if isinstance(a, dict) else str(a)) for a in affiliation
                    ) if affiliation else None
                orcid = None
                for ident in c.get("nameIdentifiers") or []:
                    if "orcid" in str(ident.get("nameIdentifierScheme", "")).lower():
                        orcid = ident.get("nameIdentifier")
                people.append({k: v for k, v in
                               {"name": name, "affiliation": affiliation, "orcid": orcid}.items()
                               if v})
            if people:
                break
        payload = json.dumps({"doi": doi, "people": people})
        try:
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(payload)
        except OSError:
            pass  # a read-only cache is a slow path, not a failure
        return Response(payload, media_type="application/json",
                        headers={"Cache-Control": "public, max-age=604800"})

    @router.get("/{endpoint_id}/capabilities")
    def capabilities(endpoint_id: str):
        return _get(endpoint_id, "/v1/capabilities")

    @router.get("/{endpoint_id}/decision-maps")
    def decision_maps(endpoint_id: str):
        """TR-VIS-0008: the producer's catalogue of validated decision maps.

        A catalogue of current products, not a history of maps mentioned in
        chats. Packs without the endpoint answer 404, which the Maps centre
        renders as "this pack publishes no decision maps".
        """
        return _get(endpoint_id, "/v1/decision-maps")

    @router.get("/{endpoint_id}/results/{result_id}")
    def result(endpoint_id: str, result_id: str):
        if not _SAFE_ID.fullmatch(result_id):
            raise HTTPException(status_code=400, detail="bad result id")
        return _get(endpoint_id, f"/v1/results/{result_id}")

    @router.get("/{endpoint_id}/targets")
    def targets(endpoint_id: str):
        if not _SAFE_ID.fullmatch(endpoint_id):
            raise HTTPException(status_code=400, detail="bad endpoint id")
        base, headers = _bridge_target(endpoint_id)
        try:
            r = httpx.post(f"{base}/v1/estimate/targets", json={}, headers=headers, timeout=_TIMEOUT)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"bridge unreachable: {type(exc).__name__}")
        return _forward(r)

    @router.get("/{endpoint_id}/headline-stats")
    def headline_stats(endpoint_id: str):
        return _get(endpoint_id, "/v1/site/headline-stats")

    @router.get("/{endpoint_id}/results/{result_id}/explain")
    def result_explain(endpoint_id: str, result_id: str, layer: str = "", mark: str = ""):
        if not _SAFE_ID.fullmatch(result_id):
            raise HTTPException(status_code=400, detail="bad result id")
        from urllib.parse import urlencode

        params = {k: v for k, v in (("layer", layer), ("mark", mark)) if v}
        suffix = ("?" + urlencode(params)) if params else ""
        return _get(endpoint_id, f"/v1/results/{result_id}/explain{suffix}")

    @router.get("/{endpoint_id}/results/{result_id}/data/{handle}")
    def result_data(endpoint_id: str, result_id: str, handle: str):
        if not (_SAFE_ID.fullmatch(result_id) and _SAFE_ID.fullmatch(handle)):
            raise HTTPException(status_code=400, detail="bad reference")
        return _get(endpoint_id, f"/v1/results/{result_id}/data/{handle}")

    # IDL-REQ-0003: bounded pack graph (overview / node focus / entity search).
    # Node ids are producer-namespaced ("ent:…", "src:…"), hence the wider regex.
    _SAFE_NODE = re.compile(r"^[A-Za-z0-9_.:\-]{1,220}$")

    @router.get("/{endpoint_id}/graph")
    def graph_overview(endpoint_id: str, q: str = ""):
        from urllib.parse import urlencode

        suffix = ("?" + urlencode({"q": q[:120]})) if q else ""
        return _get(endpoint_id, f"/v1/graph{suffix}")

    @router.get("/{endpoint_id}/graph/node/{node_id}")
    def graph_node(endpoint_id: str, node_id: str):
        if not _SAFE_NODE.fullmatch(node_id):
            raise HTTPException(status_code=400, detail="bad node id")
        from urllib.parse import quote

        return _get(endpoint_id, f"/v1/graph/node/{quote(node_id, safe='')}")

    @router.post("/{endpoint_id}/feedback/draft")
    async def feedback_draft(endpoint_id: str, request: Request):
        """TR-VIS-0005: create an immutable, redacted problem-report draft.

        The browser supplies the visible user/assistant transcript explicitly;
        the bridge filters roles and content again on its side. Publication
        never happens here — drafting is side-effect-free beyond the draft file.
        """
        if not _SAFE_ID.fullmatch(endpoint_id):
            raise HTTPException(status_code=400, detail="bad endpoint id")
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON object required")
        transcript = []
        for item in (body.get("transcript") or [])[:120]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "")
            if role not in ("user", "assistant"):
                continue
            transcript.append({"role": role, "content": str(item.get("content") or "")[:6000]})
        allowed = {
            "session_id": str(body.get("session_id") or "")[:120],
            "description": str(body.get("description") or "")[:4000],
            "include_conversation": bool(body.get("include_conversation", True)),
            "transcript": transcript,
        }
        base, headers = _bridge_target(endpoint_id)
        try:
            r = httpx.post(f"{base}/v1/feedback/draft", json=allowed, headers=headers, timeout=_TIMEOUT)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"bridge unreachable: {type(exc).__name__}")
        return _forward(r)

    @router.post("/{endpoint_id}/feedback/submit")
    async def feedback_submit(endpoint_id: str, request: Request):
        """TR-VIS-0005: publish a previously drafted report — explicit confirm only."""
        if not _SAFE_ID.fullmatch(endpoint_id):
            raise HTTPException(status_code=400, detail="bad endpoint id")
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON object required")
        allowed = {
            "report_id": str(body.get("report_id") or "")[:200],
            "confirmed": body.get("confirmed") is True,
        }
        base, headers = _bridge_target(endpoint_id)
        try:
            r = httpx.post(f"{base}/v1/feedback/submit", json=allowed, headers=headers,
                           timeout=httpx.Timeout(45.0, connect=5.0))
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"bridge unreachable: {type(exc).__name__}")
        return _forward(r)

    @router.post("/{endpoint_id}/query")
    async def query(endpoint_id: str, request: Request):
        if not _SAFE_ID.fullmatch(endpoint_id):
            raise HTTPException(status_code=400, detail="bad endpoint id")
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON object required")
        allowed = {
            "request_id": body.get("request_id"),
            "capability_id": body.get("capability_id"),
            "arguments": body.get("arguments") or {},
            "question": body.get("question") or "",
        }
        base, headers = _bridge_target(endpoint_id)
        try:
            r = httpx.post(
                f"{base}/v1/results/query", json=allowed, headers=headers, timeout=_TIMEOUT
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"bridge unreachable: {type(exc).__name__}")
        return _forward(r)

    return router
