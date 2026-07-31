from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_every_browser_load_opens_new_analysis_without_deleting_the_saved_chat():
    shell = (ROOT / "static/js/visual/visualShell.js").read_text(encoding="utf-8")
    boot = shell.split("async function boot()", 1)[1].split("setTimeout(boot", 1)[0]
    assert "showLanding(true);" in boot
    assert "setActiveNav('research');" in boot
    assert "deepLink" not in boot
    assert "hideLanding();" not in boot
    assert "stock session layer may restore that chat" in boot
