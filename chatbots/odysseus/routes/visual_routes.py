"""Visual result proxy — the browser-side gateway to per-site result services.

The visual stage (static/js/visual/) renders idli-result/1 envelopes. Envelopes
and their immutable data payloads are produced by the benchmark-owned bridge
behind a registered ModelEndpoint. This proxy:

  * confines the browser to endpoints registered in the ModelEndpoint table
    (never arbitrary URLs), and
  * keeps bridge bearer tokens server-side.

Routes (auth enforced by the global AuthMiddleware like every /api route):
  GET  /api/visual/{endpoint_id}/capabilities
  POST /api/visual/{endpoint_id}/query
  GET  /api/visual/{endpoint_id}/results/{result_id}
  GET  /api/visual/{endpoint_id}/results/{result_id}/data/{handle}
"""

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


def setup_visual_routes():
    router = APIRouter(prefix="/api/visual")

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

    @router.get("/{endpoint_id}/capabilities")
    def capabilities(endpoint_id: str):
        return _get(endpoint_id, "/v1/capabilities")

    @router.get("/{endpoint_id}/results/{result_id}")
    def result(endpoint_id: str, result_id: str):
        if not _SAFE_ID.fullmatch(result_id):
            raise HTTPException(status_code=400, detail="bad result id")
        return _get(endpoint_id, f"/v1/results/{result_id}")

    @router.get("/{endpoint_id}/results/{result_id}/data/{handle}")
    def result_data(endpoint_id: str, result_id: str, handle: str):
        if not (_SAFE_ID.fullmatch(result_id) and _SAFE_ID.fullmatch(handle)):
            raise HTTPException(status_code=400, detail="bad reference")
        return _get(endpoint_id, f"/v1/results/{result_id}/data/{handle}")

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
