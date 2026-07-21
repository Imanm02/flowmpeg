import pytest

from flowmpeg.ui.jobs import BoundedOutput, JobStatus, UiJob


def test_ui_job_starts_in_the_queue() -> None:
    job = UiJob("job-1", ("probe", "input.mp4"), "flowmpeg probe input.mp4")

    assert job.status is JobStatus.QUEUED
    assert job.returncode is None
    assert job.process is None
    assert job.created_at > 0


def test_ui_job_output_keeps_only_the_newest_text() -> None:
    output = BoundedOutput(limit=8)
    output.append("first-")
    output.append("second")

    assert output.value == "t-second"


def test_ui_job_output_requires_a_positive_limit() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        BoundedOutput(limit=0)
