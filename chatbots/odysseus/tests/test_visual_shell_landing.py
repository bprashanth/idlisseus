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
    assert weight.index("orientation(site)") < weight.index("headline-stats")
    # The lights are stories, and the note says what their reach means.
    assert "Welcome to Understory" in shell
    assert "how much data sits beneath that story" in shell


def test_wordmark_is_solid_type_not_a_scrawl():
    css = (ROOT / "static/ecodata.css").read_text(encoding="utf-8")
    assert "CaveatVendored" not in css
    assert not (ROOT / "static/lib/fonts/caveat-var.woff2").exists()
    brand = css.split(".eco-landing-name {", 1)[1].split("}", 1)[0]
    assert "var(--font-display)" in brand


def test_composer_offers_only_attach():
    """No shell, ever; web search belongs to the pack; the empty-state "+"
    duplicated New analysis. What is left is one attach button."""
    css = (ROOT / "static/ecodata.css").read_text(encoding="utf-8")
    shell = (ROOT / "static/js/visual/visualShell.js").read_text(encoding="utf-8")
    hidden = css.split("the composer, slimmed", 1)[1]
    for gone in ("#bash-toggle-btn", "#web-toggle-btn", "#overflow-menu", ".send-btn.newchat-mode"):
        assert gone in hidden, f"{gone} still offered"
    # The tools button became the attach button, delegating to the stock picker.
    assert "function slimComposer" in shell
    assert "overflow-attach-btn" in shell
    assert "Attach a file" in shell


def test_landing_dots_are_people_never_invented():
    """Each mote is a person credited with the data. The producer publishes
    DOIs but not authors, so the names are resolved from the public registries
    that minted them — and a source that resolves to nobody contributes
    nobody, because an invented name is worse than a missing one."""
    shell = (ROOT / "static/js/visual/visualShell.js").read_text(encoding="utf-8")
    routes = (ROOT / "routes/visual_routes.py").read_text(encoding="utf-8")
    assert "async function siteContributors(" in shell
    assert "doi-authors" in shell and "is-person" in shell
    # No landing experiment toggle survives; Lights is the landing.
    assert "idli-landing-mode" not in shell
    assert "renderMapUnderlay" not in shell
    # The resolver is allowlisted, cached, and answers empty rather than guessing.
    assert "api.datacite.org" in routes and "api.crossref.org" in routes
    assert "_SAFE_DOI" in routes
    assert '"people": people' in routes or "'people': people" in routes
    fn = routes.split("def doi_authors(", 1)[1].split("\n    @router", 1)[0]
    assert "people: list[dict] = []" in fn


def test_composer_is_one_line_with_a_prompt_and_attach():
    css = (ROOT / "static/ecodata.css").read_text(encoding="utf-8")
    shell = (ROOT / "static/js/visual/visualShell.js").read_text(encoding="utf-8")
    bar = css.split("the composer, slimmed", 1)[1]
    assert "content: '>'" in bar
    assert "ready when you are" in shell
