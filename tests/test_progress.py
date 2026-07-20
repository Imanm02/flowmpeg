from datetime import timedelta

from flowmpeg.progress import ProgressParser


def test_parser_waits_for_a_complete_record() -> None:
    parser = ProgressParser(expected_duration=2.0)

    assert parser.feed_line("frame=12\n") is None
    assert parser.feed_line("fps=24.0\n") is None
    assert parser.feed_line("out_time_us=1500000\n") is None
    assert parser.feed_line("speed=1.5x\n") is None
    event = parser.feed_line("progress=continue\n")

    assert event is not None
    assert event.frame == 12
    assert event.fps == 24.0
    assert event.output_time == timedelta(seconds=1.5)
    assert event.speed == 1.5
    assert event.percent == 75.0
    assert event.state == "continue"


def test_parser_keeps_unknown_fields() -> None:
    parser = ProgressParser()

    parser.feed_line("future_field=value\r\n")
    event = parser.feed_line("progress=end\r\n")

    assert event is not None
    assert ("future_field", "value") in event.raw
    assert event.percent is None


def test_parser_ignores_non_protocol_lines() -> None:
    parser = ProgressParser()

    assert parser.feed_line("ordinary stderr text") is None
    assert parser.feed_line("") is None
