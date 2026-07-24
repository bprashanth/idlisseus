"""predict connector — supervised prediction from satellite features (the ML tool).

Trains a Random Forest on ground-truth points (from research/surveys/occurrence)
using AlphaEarth Satellite Embeddings (64-d) as features, then predicts the pattern
elsewhere. This is how we corroborate hypotheses with modelled evidence: train
where there IS ground data (e.g. Bandipur/Nagarahole clusters of native/invasive)
and predict where there ISN'T (EBTL). Outputs are MODELLED, not observed — every
result carries an accuracy and a "modelled" caveat.

Uses Earth Engine ee.Classifier.smileRandomForest (server-side; no sklearn needed).

  transfer(train_points[with label], target_points)  -> target + predicted_label, confidence
  presence(species_points, bbox)                      -> modelled presence hotspot fraction + accuracy

CLI:
  python -m connectors.predict --describe
  python -m connectors.predict transfer --train labeled.csv --targets sites.csv --year 2023
  python -m connectors.predict presence --points lantana.csv --bbox 77.4,11.9,78.5,12.9 --year 2023
"""
import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _base import init_ee, read_points, write_points

EMB = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
BANDS = [f"A{i:02d}" for i in range(64)]
WORLDCLIM = "WORLDCLIM/V1/BIO"
BIO = [f"bio{i:02d}" for i in range(1, 20)]  # 19 bioclim variables

# every transfer model uses random background as pseudo-absence — surface the ask to improve it.
ABSENCE_ASK = ("DATA REQUEST: this model used random background as pseudo-absence. If you can provide "
               "confirmed ABSENCE points (sites surveyed where the species was NOT found — e.g. plot "
               "censuses), the estimate improves markedly.")


EMB_MAX_YEAR = 2024  # AlphaEarth V1 annual is published through 2024; later years are empty


def _emb(ee, year):
    year = min(int(year), EMB_MAX_YEAR)  # clamp: a future year -> empty mosaic -> crash
    return ee.ImageCollection(EMB).filterDate(f"{year}-01-01", f"{year + 1}-01-01").mosaic().select(BANDS)


def _worldclim(ee):
    return ee.Image(WORLDCLIM).select(BIO)


_COV_DIR = os.path.expanduser("~/.cache/idlisseus/cov")  # sampled fingerprints cache


def _aoi_points(bbox, n, seed=11):
    """Deterministic AOI sample points (so they cache + repeat)."""
    w, s, e, nn = [float(x) for x in bbox]
    rnd = random.Random(seed)
    return [{"lat": rnd.uniform(s, nn), "lon": rnd.uniform(w, e)} for _ in range(n)]


def _sample_cached(ee, img, rows, bands, layer, ykey, scale):
    """Sample `img` (AE/WorldClim/…) at rows, caching each point's vector to disk keyed by
    (lat,lon,layer,ykey). Only cache-MISSES hit Earth Engine — so repeated gate/route calls
    are instant. Pure-python (works in the Hermes venv, which has no numpy/sklearn).
    Returns a list of vectors aligned to rows (None where a point couldn't be sampled)."""
    os.makedirs(_COV_DIR, exist_ok=True)

    def keyf(r):
        h = hashlib.md5(f"{round(r['lat'], 5)},{round(r['lon'], 5)},{layer},{ykey}".encode()).hexdigest()
        return os.path.join(_COV_DIR, h)
    out, misses = [None] * len(rows), []
    for i, r in enumerate(rows):
        p = keyf(r)
        if os.path.exists(p):
            try:
                out[i] = json.load(open(p)); continue
            except Exception:
                pass
        misses.append(i)
    if misses:
        fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([rows[i]["lon"], rows[i]["lat"]]),
                                              {"_i": i}) for i in misses])
        feats = img.sampleRegions(collection=fc, scale=scale, geometries=False).getInfo()["features"]
        for f in feats:
            pr = f["properties"]; i = int(pr["_i"])
            if all(b in pr for b in bands):
                out[i] = [pr[b] for b in bands]
                try:
                    json.dump(out[i], open(keyf(rows[i]), "w"))
                except Exception:
                    pass
    return out


def _read_labeled(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            low = {k.strip().lower(): v for k, v in r.items() if k}
            lat = low.get("lat") or low.get("latitude") or low.get("decimallatitude")
            lon = low.get("lon") or low.get("lng") or low.get("longitude") or low.get("decimallongitude")
            lab = low.get("label") or low.get("class") or low.get("type")
            if lat and lon and lab:
                rows.append({"lat": float(lat), "lon": float(lon), "label": str(lab)})
    return rows


def _fc(ee, rows, extra=None):
    return ee.FeatureCollection([
        ee.Feature(ee.Geometry.Point([r["lon"], r["lat"]]),
                   {**(extra or {}), **({"label": r["label"]} if "label" in r else {}),
                    "_i": i}) for i, r in enumerate(rows)])


def transfer(train_rows, target_rows, year=2023, trees=100, project="plantwars"):
    """Train RF on labelled points, predict the class at target points."""
    ee = init_ee(project)
    img = _emb(ee, year)
    labels = sorted({r["label"] for r in train_rows})
    code = {l: i for i, l in enumerate(labels)}
    tr = _fc(ee, [{**r, "label": r["label"]} for r in train_rows])
    tr = tr.map(lambda f: f.set("y", ee.Dictionary(code).get(f.get("label"))))
    trained = img.sampleRegions(collection=tr, properties=["y"], scale=10, geometries=False)
    # 70/30 split for an honest accuracy
    trained = trained.randomColumn("r", 42)
    tr_set = trained.filter(ee.Filter.lt("r", 0.7))
    te_set = trained.filter(ee.Filter.gte("r", 0.7))
    clf = ee.Classifier.smileRandomForest(trees).train(tr_set, "y", BANDS)
    acc = te_set.classify(clf).errorMatrix("y", "classification").accuracy().getInfo() \
        if te_set.size().getInfo() else None
    # predict at targets
    tg = _fc(ee, target_rows)
    pred = img.sampleRegions(collection=tg, properties=["_i"], scale=10, geometries=False).classify(clf)
    inv = {i: l for l, i in code.items()}
    by_i = {int(f["properties"]["_i"]): int(f["properties"]["classification"])
            for f in pred.getInfo()["features"]}
    out = [{**t, "predicted_label": inv.get(by_i.get(i)), "modelled": True}
           for i, t in enumerate(target_rows)]
    return {"classes": labels, "test_accuracy": round(acc, 3) if acc else None,
            "n_train": len(train_rows), "predictions": out,
            "caveat": "MODELLED via RF on AlphaEarth embeddings — corroborative, not observed."}


def presence(species_rows, bbox, year=2023, n_bg=300, trees=120, project="plantwars"):
    """Model where a species is likely present (presence vs random background) and
    report the modelled hotspot fraction over the bbox + accuracy."""
    ee = init_ee(project)
    img = _emb(ee, year)
    geom = ee.Geometry.Rectangle(list(bbox))
    pres = _fc(ee, species_rows).map(lambda f: f.set("y", 1))
    bg = ee.FeatureCollection.randomPoints(geom, n_bg, 7).map(lambda f: f.set("y", 0))
    samp = img.sampleRegions(collection=pres.merge(bg), properties=["y"], scale=10, geometries=False)
    samp = samp.randomColumn("r", 42)
    clf = ee.Classifier.smileRandomForest(trees).train(samp.filter(ee.Filter.lt("r", 0.7)), "y", BANDS)
    te = samp.filter(ee.Filter.gte("r", 0.7))
    acc = te.classify(clf).errorMatrix("y", "classification").accuracy().getInfo() \
        if te.size().getInfo() else None
    frac = img.classify(clf).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=geom, scale=200, maxPixels=1e10
    ).get("classification").getInfo()
    imp = ee.Dictionary(clf.explain()).get("importance").getInfo()
    top = sorted(imp.items(), key=lambda kv: -kv[1])[:5] if isinstance(imp, dict) else []
    return {"n_presence": len(species_rows), "n_background": n_bg,
            "test_accuracy": round(acc, 3) if acc else None,
            "modelled_present_fraction": round(frac, 3) if frac is not None else None,
            "top_feature_bands": [k for k, _ in top],
            "caveat": "MODELLED presence (RF on embeddings) — corroborative, not observed. Occurrence "
                      "sampling is biased; treat as a hypothesis-strength signal. " + ABSENCE_ASK}


def gate(train_rows, bbox, year=2023, n_aoi=100, project="plantwars",
         cos_thresh=0.85, emb_frac_min=0.5, climate_frac_min=0.8):
    """The routing SENSOR: is it valid to transfer these training points into the AOI?
    Reports TWO independent gates because the two model families fail differently:
      - AlphaEarth EMBEDDING cosine (train centroid vs AOI): RF/embedding transfer is
        local — invalid across ecoregions. High cosine => transfer_rf ok.
      - WorldClim MESS (is the AOI inside the training CLIMATE envelope?): climate SDM
        CAN cross ecoregions, but only within the trained climate range. In-envelope
        => sdm_climate ok. Out => extrapolation, refuse.
    Verdict: overlap (train already in AOI) > transfer_rf > sdm_climate > refuse."""
    ee = init_ee(project)
    emb, wc = _emb(ee, year), _worldclim(ee)
    yk = min(int(year), EMB_MAX_YEAR)  # AE cache key (clamped); WorldClim is climatology -> "wc"
    w, s, e, n = [float(x) for x in bbox]
    frac_train_in_aoi = sum(1 for r in train_rows if w <= r["lon"] <= e and s <= r["lat"] <= n) \
        / max(1, len(train_rows))
    # subsample training points (bound the NN payload); embedding NEAREST-NEIGHBOUR analog
    # (max cosine of each AOI pixel to ANY training pixel) — a centroid washes out when the
    # species spans heterogeneous habitats, so NN is the right "is this pixel like one we trained on".
    tr_rows = train_rows if len(train_rows) <= 500 else train_rows[::max(1, len(train_rows) // 500)]
    tr_vecs = [v for v in _sample_cached(ee, emb, tr_rows, BANDS, "ae", yk, 10) if v]
    tr_norm = [math.sqrt(sum(x * x for x in v)) or 1e-9 for v in tr_vecs]
    tr_bio = [v for v in _sample_cached(ee, wc, tr_rows, BIO, "bio", "wc", 1000) if v]
    mins = [min(c) for c in zip(*tr_bio)]
    maxs = [max(c) for c in zip(*tr_bio)]
    # sample the AOI (deterministic python points -> cacheable)
    aoi_rows = _aoi_points(bbox, n_aoi, 11)
    aoi_emb = _sample_cached(ee, emb, aoi_rows, BANDS, "ae", yk, 10)
    aoi_wc = _sample_cached(ee, wc, aoi_rows, BIO, "bio", "wc", 1000)

    def nn_cos(v, skip=-1):
        nv = math.sqrt(sum(x * x for x in v)) or 1e-9
        return max(sum(a * b for a, b in zip(v, tv)) / (nv * tn)
                   for j, (tv, tn) in enumerate(zip(tr_vecs, tr_norm)) if j != skip)
    # calibrate "analog" against the training set's OWN internal tightness: each train
    # pixel's nearest OTHER train pixel. The AOI must be as close as training pixels are to
    # each other. floor = 10th pct of that (clamped) — novelty detection, not a magic 0.85.
    self_nn = sorted(nn_cos(tr_vecs[i], skip=i) for i in range(len(tr_vecs)))
    floor = min(0.92, max(cos_thresh, self_nn[max(0, len(self_nn) // 10)]))
    cs = [nn_cos(v) for v in aoi_emb if v]

    def mess(vec):
        outs = []
        for v, lo, hi in zip(vec, mins, maxs):
            rng = (hi - lo) or 1
            outs.append(min((v - lo) / rng, (hi - v) / rng))  # <0 => outside train range
        return min(outs) if outs else None
    ms = [m for m in (mess(v) for v in aoi_wc if v) if m is not None]
    emb_mean = sum(cs) / len(cs) if cs else None
    frac_emb = sum(1 for c in cs if c >= floor) / len(cs) if cs else 0
    frac_clim = sum(1 for m in ms if m >= 0) / len(ms) if ms else 0
    if frac_train_in_aoi >= 0.3:
        verdict, why = "overlap", "training points already fall in the AOI — use observed (geo.nearest), no model."
    elif frac_emb >= emb_frac_min:
        verdict, why = "transfer_rf", "AOI is an AlphaEarth analog of the training area — RF/embedding transfer valid."
    elif frac_clim >= climate_frac_min:
        verdict, why = "sdm_climate", "AOI outside embedding analog space but INSIDE the training climate envelope — climate SDM valid, RF is not."
    else:
        verdict, why = "refuse", "AOI is outside both the embedding analog space AND the climate envelope — extrapolation; collect local data."
    return {"n_train": len(train_rows), "frac_train_in_aoi": round(frac_train_in_aoi, 3),
            "emb_nn_cosine_mean": round(emb_mean, 3) if emb_mean is not None else None,
            "emb_analog_floor": round(floor, 3), "frac_aoi_analog": round(frac_emb, 3),
            "climate_mess_frac_in_envelope": round(frac_clim, 3),
            "verdict": verdict, "why": why}


def sdm_climate(presence_rows, bbox, year=2023, n_bg=500, trees=150, project="plantwars"):
    """CLIMATE SDM (WorldClim bioclim + RF). Trains presence-vs-background on the 19
    bioclim vars over the TRAINING extent, projects a suitability fraction into the AOI,
    and reports MESS coverage (what fraction of the AOI is inside the trained climate
    envelope — the honesty gate on cross-ecoregion extrapolation). This is the branch
    that can legitimately go dry-Deccan -> EBTL, unlike RF-on-embeddings."""
    ee = init_ee(project)
    wc = _worldclim(ee)
    pres_fc = _fc(ee, presence_rows).map(lambda f: f.set("y", 1))
    train_extent = pres_fc.geometry().bounds()  # background drawn from where we have data
    bg = ee.FeatureCollection.randomPoints(train_extent, n_bg, 7).map(lambda f: f.set("y", 0))
    samp = wc.sampleRegions(collection=pres_fc.merge(bg), properties=["y"], scale=1000, geometries=False)
    samp = samp.randomColumn("r", 42)
    clf = ee.Classifier.smileRandomForest(trees).train(samp.filter(ee.Filter.lt("r", 0.7)), "y", BIO)
    te = samp.filter(ee.Filter.gte("r", 0.7))
    acc = te.classify(clf).errorMatrix("y", "classification").accuracy().getInfo() \
        if te.size().getInfo() else None
    geom = ee.Geometry.Rectangle([float(x) for x in bbox])
    frac = wc.classify(clf).reduceRegion(reducer=ee.Reducer.mean(), geometry=geom,
                                         scale=1000, maxPixels=1e10).get("classification").getInfo()
    # MESS coverage of the AOI against the training climate envelope
    mm = wc.sampleRegions(collection=pres_fc, scale=1000, geometries=False) \
        .reduceColumns(ee.Reducer.minMax().repeat(19), BIO).getInfo()
    mins, maxs = mm["min"], mm["max"]
    aoi = ee.FeatureCollection.randomPoints(geom, 100, 11)
    aoi_wc = wc.sampleRegions(collection=aoi, scale=1000, geometries=False).getInfo()["features"]

    def mess(props):
        outs = [min((props[b] - lo) / ((hi - lo) or 1), (hi - props[b]) / ((hi - lo) or 1))
                for b, lo, hi in zip(BIO, mins, maxs) if props.get(b) is not None]
        return min(outs) if outs else None
    ms = [m for m in (mess(f["properties"]) for f in aoi_wc) if m is not None]
    frac_in = sum(1 for m in ms if m >= 0) / len(ms) if ms else 0
    return {"method": "SDM (WorldClim bioclim + RF, presence/background)",
            "n_presence": len(presence_rows), "n_background": n_bg,
            "test_accuracy": round(acc, 3) if acc else None,
            "modelled_suitable_fraction": round(frac, 3) if frac is not None else None,
            "aoi_in_climate_envelope_frac": round(frac_in, 3),
            "data_request": ABSENCE_ASK,
            "caveat": "MODELLED climate suitability, not observed. Cross-ecoregion projection is "
                      "valid ONLY where aoi_in_climate_envelope_frac ~1; lower => extrapolation. "
                      "Climate niche only — ignores land-use, biotic interactions, dispersal."}


def route(train_rows, bbox, question="presence", year=2023, project="plantwars", agree_tol=0.2):
    """The situation classifier. Runs the gate, then EVERY valid method, compares them,
    and returns which of three situations we're in:
      - answerable        : a method (often several, agreeing) applies -> suggestion + caveat
      - need_more_data    : no gate is green -> honest data gap, recommend local collection
      - need_better_models: methods apply but DISAGREE -> model gap, surface the conflict
    'question' picks which methods are eligible:
      - 'presence'/'suitability' (where does a species belong): appearance RF AND climate SDM
      - 'value' (a continuous measurement here, e.g. canopy/pH): appearance RF ONLY
        (a climate niche can't hand you a soil pH)."""
    g = gate(train_rows, bbox, year, project=project)
    out = {"question": question, "gate": g, "methods": {}, "situation": None, "recommendation": None}
    v = g["verdict"]
    if v == "overlap":
        out["situation"] = "answerable"
        out["recommendation"] = "Points already fall in the AOI — report observed (geo.nearest), no model."
        return out
    if v == "refuse":
        out["situation"] = "need_more_data"
        out["recommendation"] = ("AOI is unlike the donor points in appearance AND climate — no valid "
                                 "transfer. Collect local ground data at the AOI (this is the honest gap).")
        return out
    # eligible methods by gate + question type
    ran = {}
    if g["frac_aoi_analog"] >= 0.5:
        ran["transfer_rf"] = presence(train_rows, bbox, year, project=project)
    if question in ("presence", "suitability") and g["climate_mess_frac_in_envelope"] >= 0.8:
        ran["sdm_climate"] = sdm_climate(train_rows, bbox, year, project=project)
    out["methods"] = ran
    sig = {}
    if "transfer_rf" in ran:
        sig["transfer_rf"] = ran["transfer_rf"].get("modelled_present_fraction")
    if "sdm_climate" in ran:
        sig["sdm_climate"] = ran["sdm_climate"].get("modelled_suitable_fraction")
    sig = {k: x for k, x in sig.items() if x is not None}
    if not sig:
        out["situation"] = "need_more_data"
        out["recommendation"] = "Gate opened but no method produced a signal — treat as a data gap."
    elif len(sig) == 2:
        a, b = sig["transfer_rf"], sig["sdm_climate"]
        if abs(a - b) <= agree_tol:
            out["situation"] = "answerable"
            out["recommendation"] = (f"Appearance and climate methods AGREE (~{(a + b) / 2:.2f}) — strong, "
                                     f"corroborated suggestion; high-value spot for a small ground-truth check.")
        else:
            out["situation"] = "need_better_models"
            out["recommendation"] = (f"Methods DISAGREE (appearance={a}, climate={b}) — surface the conflict; "
                                     f"understand which assumption breaks before trusting either.")
    else:
        k, x = next(iter(sig.items()))
        out["situation"] = "answerable"
        out["recommendation"] = (f"One method valid ({k}={x}) — single-method modelled suggestion, "
                                 f"weaker evidence; note the other gate was not green.")
    return out


def describe():
    return {
        "connector": "predict",
        "purpose": "Random-Forest prediction from AlphaEarth embeddings — corroborate "
                   "hypotheses by training on ground truth and predicting elsewhere.",
        "produces": "gate->routing verdict; transfer/presence->RF on embeddings; sdm->climate suitability.",
        "functions": [
            "route(train_rows, bbox, question) -> {situation: answerable|need_more_data|need_better_models} "
            "+ recommendation + the methods it ran. THE ENTRY POINT: gate -> run every valid method -> "
            "compare. question='presence'/'suitability' (both RF+SDM) or 'value' (RF only).",
            "gate(train_rows, bbox, year) -> {verdict: overlap|transfer_rf|sdm_climate|refuse} + why. "
            "Two gates — AlphaEarth NN-analog (RF valid?) + WorldClim MESS (climate envelope covers AOI? "
            "SDM valid?). Refuses when the AOI is out of both.",
            "transfer(train_rows[label], target_rows, year) -> predictions + test_accuracy (RF+AlphaEarth, LOCAL)",
            "presence(species_rows, bbox, year) -> modelled_present_fraction (RF+AlphaEarth, LOCAL)",
            "sdm(presence_rows, bbox, year) -> climate suitability + aoi_in_climate_envelope_frac "
            "(WorldClim bioclim + RF; CAN cross ecoregions within the trained climate envelope)",
        ],
        "use": "gate(train, aoi) FIRST to pick the method. RF/AlphaEarth (transfer/presence) is local — "
               "use when verdict=transfer_rf. Climate SDM (sdm) crosses ecoregions within the climate "
               "envelope — use when verdict=sdm_climate. verdict=refuse => collect local data, don't model. "
               "Feed sdm from OCCURRENCE (GBIF + camera-trap), e.g. dry-Deccan -> EBTL. Always MODELLED.",
        "gotcha": "SDM caveats: occurrence sampling bias, spatial autocorrelation, embedding opacity. "
                  "RF+AlphaEarth CANNOT cross ecoregions (gate refuses); climate SDM only within MESS "
                  "envelope. Report as corroborative + accuracy + gate verdict, never as observation.",
        "example": "python /opt/data/connectors/predict.py presence --points lantana.csv --bbox 77.4,11.9,78.5,12.9",
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(prog="predict")
    ap.add_argument("--describe", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    t = sub.add_parser("transfer"); t.add_argument("--train", required=True)
    t.add_argument("--targets", required=True); t.add_argument("--year", type=int, default=2023)
    p = sub.add_parser("presence"); p.add_argument("--points", required=True)
    p.add_argument("--bbox", required=True); p.add_argument("--year", type=int, default=2023)
    # note: all four take --points (alias --train) for a consistent flag across predict
    g = sub.add_parser("gate"); g.add_argument("--points", "--train", dest="points", required=True)
    g.add_argument("--bbox", required=True); g.add_argument("--year", type=int, default=2023)
    sd = sub.add_parser("sdm"); sd.add_argument("--points", "--train", dest="points", required=True)
    sd.add_argument("--bbox", required=True); sd.add_argument("--year", type=int, default=2023)
    rt = sub.add_parser("route"); rt.add_argument("--points", "--train", dest="points", required=True)
    rt.add_argument("--bbox", required=True); rt.add_argument("--question", default="presence")
    rt.add_argument("--year", type=int, default=2023)
    args = ap.parse_args(argv)
    if args.describe or not args.cmd:
        print(json.dumps(describe(), indent=2)); return
    if args.cmd == "transfer":
        print(json.dumps(transfer(_read_labeled(args.train), read_points(args.targets), args.year), indent=2))
    elif args.cmd == "presence":
        bbox = [float(x) for x in args.bbox.split(",")]
        print(json.dumps(presence(read_points(args.points), bbox, args.year), indent=2))
    elif args.cmd == "gate":
        bbox = [float(x) for x in args.bbox.split(",")]
        print(json.dumps(gate(read_points(args.points), bbox, args.year), indent=2))
    elif args.cmd == "sdm":
        bbox = [float(x) for x in args.bbox.split(",")]
        print(json.dumps(sdm_climate(read_points(args.points), bbox, args.year), indent=2))
    elif args.cmd == "route":
        bbox = [float(x) for x in args.bbox.split(",")]
        print(json.dumps(route(read_points(args.points), bbox, args.question, args.year), indent=2))


if __name__ == "__main__":
    _main()
