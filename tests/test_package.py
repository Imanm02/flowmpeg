from flowmpeg import FlowmpegError, GraphError, __version__
from flowmpeg.cli import build_parser, main
from flowmpeg.ui.assets import load_asset


def test_version_is_public() -> None:
    assert __version__ == "0.1.0"


def test_specific_errors_share_base_class() -> None:
    assert issubclass(GraphError, FlowmpegError)


def test_cli_api_is_importable() -> None:
    assert build_parser().prog == "flowmpeg"
    assert callable(main)


def test_ui_assets_are_packaged() -> None:
    for name in ("index.html", "app.css", "app.js"):
        asset = load_asset(name)

        assert asset is not None
        assert asset.data
