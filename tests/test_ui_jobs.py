from flowmpeg.ui.jobs import JobStatus, UiJob


def test_ui_job_starts_in_the_queue() -> None:
    job = UiJob("job-1", ("probe", "input.mp4"), "flowmpeg probe input.mp4")

    assert job.status is JobStatus.QUEUED
    assert job.returncode is None
    assert job.process is None
    assert job.created_at > 0
