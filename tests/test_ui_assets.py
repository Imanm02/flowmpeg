from flowmpeg.ui.assets import load_asset


def test_ui_assets_load_from_the_installed_package() -> None:
    index = load_asset("index.html")
    script = load_asset("app.js")
    style = load_asset("app.css")

    assert index is not None and b"<!doctype html>" in index.data
    assert script is not None and script.content_type.startswith("text/javascript")
    assert style is not None and style.content_type.startswith("text/css")


def test_ui_asset_loader_rejects_unknown_paths() -> None:
    assert load_asset("../pyproject.toml") is None
    assert load_asset("missing.js") is None
