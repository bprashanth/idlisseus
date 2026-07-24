"""skyfi connector — SkyFi Platform API: search / price / order / download archive satellite imagery.

The paid rung of the invasive-map funnel: once the free S2-phenology funnel narrows WHERE to look,
buy ONE recent high-res archive scene over the site to confirm. Everything is budget-guarded: `order`
REFUSES above a cap unless --yes, and always prices via /order-archive/validate first.

  search  : POST /archives           -> recent archives over an AOI (+ price/resolution/cloud/date)
  best    : search + rank (recent, low-cloud, cheapest-within-budget) + price the top candidate
  price   : POST /order-archive/validate  -> exact order cost in USD (no charge)
  order   : POST /order-archive      -> PLACE the order (budget-guarded; needs --yes)
  status  : GET  /orders/{id}        -> delivery status + download URLs
  download: GET  /orders/{id}/{type} -> fetch a deliverable (view_ready_cog | cog | image | payload)

Key (OUTSIDE repo): ~/.config/idlisseus/skyfi.json (host) or ~/.hermes/secrets/skyfi.json (sandbox)
or env SKYFI_API_KEY. Header: X-Skyfi-Api-Key. Docs: https://app.skyfi.com/platform-api/redoc
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

BASE = "https://app.skyfi.com/platform-api"
DEFAULT_CAP_USD = 50.0
DELIVERABLES = {"view_ready_cog": "downloadViewReadyCogUrl", "cog": "downloadCogUrl",
                "image": "downloadImageUrl", "payload": "downloadPayloadUrl"}


def _key():
    for p in ("~/.config/idlisseus/skyfi.json", "~/.hermes/secrets/skyfi.json"):
        p = os.path.expanduser(p)
        if os.path.exists(p):
            return json.load(open(p))["api_key"].strip()
    if os.environ.get("SKYFI_API_KEY"):
        return os.environ["SKYFI_API_KEY"].strip()
    raise SystemExit("No SkyFi key (~/.config/idlisseus/skyfi.json or SKYFI_API_KEY).")


# SkyFi sits behind Cloudflare, which blocks the default Python-urllib User-Agent (403 error 1010).
# A browser-like UA passes it.
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"X-Skyfi-Api-Key": _key(), "Content-Type": "application/json",
                                        "User-Agent": _UA, "Accept": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=60).read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        raise SystemExit(f"SkyFi {method} {path} -> HTTP {e.code}: {detail}\n"
                         f"(401=invalid/not-activated key; 403=accept Vantor EULA at "
                         f"app.skyfi.com/accept-vantor-eula)")


def _wkt(bbox):
    w, s, e, n = [float(x) for x in bbox]
    return f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"


def _slim(a, aoi_sqkm=None):
    """Keep the fields that matter for choosing an archive + estimate the real order cost."""
    per = a.get("priceForOneSquareKm", 0)
    minsq = a.get("minSqKm", 0)
    est = a.get("priceFullScene") if a.get("fullSceneOnly") else round(per * max(aoi_sqkm or 0, minsq or 0), 2)
    return {"archiveId": a["archiveId"], "provider": a.get("provider"), "constellation": a.get("constellation"),
            "resolution": a.get("resolution"), "gsd_m": a.get("gsd"), "capture": a.get("captureTimestamp"),
            "cloud_pct": a.get("cloudCoveragePercent"), "off_nadir": a.get("offNadirAngle"),
            "price_per_sqkm_usd": per, "min_sqkm": minsq, "full_scene_only": a.get("fullSceneOnly"),
            "price_full_scene_usd": a.get("priceFullScene"), "open_data": a.get("openData"),
            "overlap_ratio": round(a.get("overlapRatio", 0), 3), "est_order_usd": est,
            "thumb": (a.get("thumbnailUrls") or {})}


def search(bbox, from_date=None, to_date=None, max_cloud=20, resolutions=None, providers=None,
           open_data=None, page_size=30):
    body = {"aoi": _wkt(bbox), "pageSize": page_size, "maxCloudCoveragePercent": max_cloud}
    if from_date: body["fromDate"] = from_date
    if to_date: body["toDate"] = to_date
    if resolutions: body["resolutions"] = resolutions
    if providers: body["providers"] = providers
    if open_data is not None: body["openData"] = open_data
    res = _req("POST", "/archives", body)
    aoi_sqkm = _bbox_sqkm(bbox)
    return [_slim(a, aoi_sqkm) for a in res.get("archives", [])]


def _bbox_sqkm(bbox):
    import math
    w, s, e, n = [float(x) for x in bbox]
    return round(abs(e - w) * abs(n - s) * 111 * 111 * math.cos(math.radians((s + n) / 2)), 3)


def best(bbox, cap_usd=DEFAULT_CAP_USD, max_cloud=15, from_date=None, since_days=365, **kw):
    """Rank archives for an invasive map: within budget, low cloud, recent, finest GSD. Prices the top."""
    if not from_date and since_days:
        import datetime
        from_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=since_days)).strftime("%Y-%m-%dT00:00:00+00:00")
    arch = search(bbox, from_date=from_date, max_cloud=max_cloud, **kw)
    aff = [a for a in arch if (a["est_order_usd"] or 1e9) <= cap_usd]
    # rank: finest GSD first, then most recent, then lowest cloud
    aff.sort(key=lambda a: (a["gsd_m"] or 99, -_ts(a["capture"]), a["cloud_pct"] or 100))
    out = {"aoi_sqkm": _bbox_sqkm(bbox), "cap_usd": cap_usd, "n_total": len(arch),
           "n_within_budget": len(aff), "candidates": aff[:8]}
    if aff:
        top = aff[0]
        out["recommended"] = top
        out["recommended_price"] = price(top["archiveId"], bbox)   # exact validate cost (no charge)
    return out


def _ts(s):
    try:
        import datetime
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0


def price(archive_id, bbox):
    r = _req("POST", "/order-archive/validate", {"archiveId": archive_id, "aoi": _wkt(bbox)})
    cents = r.get("estimatedCostCents", r.get("orderCost"))   # validate uses estimatedCostCents
    return {"archiveId": archive_id, "order_cost_usd": round(cents / 100, 2) if cents is not None else None,
            "aoi_sqkm": r.get("aoiSqkm"), "provider": r.get("provider")}


def order(archive_id, bbox, cap_usd=DEFAULT_CAP_USD, yes=False, label="ebtl-invasive"):
    """PLACE an order — guarded: prices first, REFUSES above cap or without yes=True."""
    p = price(archive_id, bbox)
    cost = p.get("order_cost_usd")
    if cost is None:
        raise SystemExit(f"could not price {archive_id}")
    if cost > cap_usd:
        raise SystemExit(f"REFUSING: ${cost} exceeds cap ${cap_usd}. Raise --cap-usd to override.")
    if not yes:
        return {"would_order": archive_id, "cost_usd": cost, "cap_usd": cap_usd,
                "note": "dry-run. Re-run with --yes to actually place this order and be charged."}
    r = _req("POST", "/order-archive", {"archiveId": archive_id, "aoi": _wkt(bbox), "orderLabel": label})
    return {"ordered": archive_id, "cost_usd": cost, "orderId": r.get("orderId"),
            "status": r.get("status"), "downloadViewReadyCogUrl": r.get("downloadViewReadyCogUrl")}


def status(order_id):
    return _req("GET", f"/orders/{order_id}")


class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """The SkyFi download URL 302s to a presigned CDN/S3 URL; re-sending the SkyFi key there 403s.
    Drop our auth headers on redirect (same fix as the Dryad connector)."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        r = super().redirect_request(req, fp, code, msg, headers, newurl)
        if r is not None:
            for h in ("X-Skyfi-Api-Key", "Authorization"):
                try:
                    r.remove_header(h)
                except Exception:
                    pass
        return r


def download(order_id, deliverable="view_ready_cog", out=None):
    """Resolve the deliverable URL and STREAM it to disk (browser UA + key; auth stripped on redirect)."""
    import shutil
    r = _req("GET", f"/orders/{order_id}")
    url = r.get(DELIVERABLES.get(deliverable, "downloadViewReadyCogUrl")) or f"{BASE}/orders/{order_id}/{deliverable}"
    out = out or os.path.expanduser(f"~/.hermes/work/skyfi_{order_id}_{deliverable}.tif")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    opener = urllib.request.build_opener(_StripAuthOnRedirect())
    req = urllib.request.Request(url, headers={"X-Skyfi-Api-Key": _key(), "User-Agent": _UA})
    with opener.open(req, timeout=600) as resp, open(out, "wb") as f:
        shutil.copyfileobj(resp, f, length=1 << 20)
    return {"order_id": order_id, "deliverable": deliverable, "saved": out,
            "bytes": os.path.getsize(out) if os.path.exists(out) else 0}


def describe():
    return {
        "connector": "skyfi",
        "purpose": "SkyFi Platform API — search/price/order/download high-res ARCHIVE satellite imagery.",
        "produces": "archive metadata + prices; ordered GeoTIFF/COG deliverables.",
        "functions": [
            "search(bbox, from_date, to_date, max_cloud, resolutions, providers, open_data) -> archives",
            "best(bbox, cap_usd, max_cloud, since_days) -> ranked affordable candidates + priced top",
            "price(archive_id, bbox) -> exact order cost USD (validate, no charge)",
            "order(archive_id, bbox, cap_usd, yes) -> PLACE order (guarded; dry-run unless --yes)",
            "status(order_id) / download(order_id, deliverable) -> fetch view_ready_cog|cog|image|payload",
        ],
        "use": "The PAID confirm step of the invasive-map funnel. Run `best` first (it prices within a "
               "cap). openData=true archives are FREE. Cropping honours minSqKm — tiny AOIs pay the min.",
        "gotcha": "order() is budget-guarded (refuses > cap, dry-run unless yes=True). 401=key invalid/"
                  "not activated; 403=accept Vantor EULA. Archive delivery ~24h. Key OUTSIDE repo.",
        "example": "python /opt/data/connectors/skyfi.py best --bbox 78.170,12.721,78.197,12.747 --cap-usd 50",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="skyfi")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    def bb(p): p.add_argument("--bbox", required=True)
    s = sub.add_parser("search"); bb(s); s.add_argument("--from-date"); s.add_argument("--to-date")
    s.add_argument("--max-cloud", type=float, default=20); s.add_argument("--open-data", action="store_true")
    s.add_argument("--resolutions", nargs="*"); s.add_argument("--providers", nargs="*")
    b = sub.add_parser("best"); bb(b); b.add_argument("--cap-usd", type=float, default=DEFAULT_CAP_USD)
    b.add_argument("--max-cloud", type=float, default=15); b.add_argument("--since-days", type=int, default=365)
    pr = sub.add_parser("price"); bb(pr); pr.add_argument("--archive-id", required=True)
    o = sub.add_parser("order"); bb(o); o.add_argument("--archive-id", required=True)
    o.add_argument("--cap-usd", type=float, default=DEFAULT_CAP_USD); o.add_argument("--yes", action="store_true")
    st = sub.add_parser("status"); st.add_argument("--order-id", required=True)
    dl = sub.add_parser("download"); dl.add_argument("--order-id", required=True)
    dl.add_argument("--deliverable", default="view_ready_cog"); dl.add_argument("--out")
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    bbox = args.bbox.split(",") if getattr(args, "bbox", None) else None
    if args.cmd == "search":
        r = search(bbox, args.from_date, args.to_date, args.max_cloud,
                   args.resolutions, args.providers, args.open_data or None)
    elif args.cmd == "best":
        r = best(bbox, args.cap_usd, args.max_cloud, since_days=args.since_days)
    elif args.cmd == "price":
        r = price(args.archive_id, bbox)
    elif args.cmd == "order":
        r = order(args.archive_id, bbox, args.cap_usd, args.yes)
    elif args.cmd == "status":
        r = status(args.order_id)
    elif args.cmd == "download":
        r = download(args.order_id, args.deliverable, args.out)
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    _main()
