from flowmpeg import FlowmpegError, GraphError, __version__


def test_version_is_public() -> None:
    assert __version__ == "0.1.0"


def test_specific_errors_share_base_class() -> None:
    assert issubclass(GraphError, FlowmpegError)
