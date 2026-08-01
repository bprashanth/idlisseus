from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_boot_lands_on_sites_but_honours_an_open_conversation():
    """A plain visit opens site selection; a refresh mid-chat (a #<session-id>
    URL) returns to that chat instead of dropping the reader on the landing page."""
    shell = (ROOT / "static/js/visual/visualShell.js").read_text(encoding="utf-8")
    boot = shell.split("async function boot()", 1)[1].split("setTimeout(boot", 1)[0]
    assert "deepLink" in boot
    assert "'reload'" in boot  # hash counts only on an actual reload
    assert "hideLanding();" in boot
    assert "showLanding(true);" in boot
    assert "setActiveNav('research');" in boot
    assert "setActiveNav('chat');" in boot


def test_brand_mark_is_the_raven_and_opens_sites():
    """The mark is deliberately cryptic. It ships as alpha only and is painted
    with the theme ink via CSS mask, so one asset serves every surface."""
    shell = (ROOT / "static/js/visual/visualShell.js").read_text(encoding="utf-8")
    css = (ROOT / "static/ecodata.css").read_text(encoding="utf-8")
    assert "eco-brand-ink" in shell
    assert "raven.png" in css
    assert "mask:" in css.split(".eco-brand-ink", 1)[1][:400]
    for asset in ("raven.png", "raven-favicon.png", "raven-cloud.png"):
        assert (ROOT / "static/icons" / asset).is_file(), asset
    brand = shell.split("const brand = document.createElement", 1)[1].split("navEl.appendChild(brand);", 1)[0]
    assert "showLanding(true);" in brand


def test_landing_is_a_field_of_lights_sized_by_what_each_pack_holds():
    shell = (ROOT / "static/js/visual/visualShell.js").read_text(encoding="utf-8")
    css = (ROOT / "static/ecodata.css").read_text(encoding="utf-8")
    assert "function renderSky" in shell
    assert "eco-spot-halo" in shell and ".eco-spot-halo" in css
    # One comparable measure across packs, or the sizes would lie: a pack
    # counting persondays must not outshine one counting detections.
    weight = shell.split("async function siteWeight(", 1)[1].split("\n}", 1)[0]
    assert "'records'" in weight
    assert weight.index("site-orientation") < weight.index("headline-stats")
    # Position carries no meaning, and the page says so.
    assert "Positions are composition, not geography" in shell


def test_wordmark_is_solid_type_not_a_scrawl():
    css = (ROOT / "static/ecodata.css").read_text(encoding="utf-8")
    assert "CaveatVendored" not in css
    assert not (ROOT / "static/lib/fonts/caveat-var.woff2").exists()
    brand = css.split(".eco-landing-name {", 1)[1].split("}", 1)[0]
    assert "var(--font-display)" in brand
