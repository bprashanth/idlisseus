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


def test_brand_mark_is_the_idli_moon_and_opens_sites():
    shell = (ROOT / "static/js/visual/visualShell.js").read_text(encoding="utf-8")
    assert "idli-moon.png" in shell
    assert (ROOT / "static/icons/idli-moon.png").is_file()
    brand = shell.split("const brand = document.createElement", 1)[1].split("navEl.appendChild(brand);", 1)[0]
    assert "showLanding(true);" in brand
