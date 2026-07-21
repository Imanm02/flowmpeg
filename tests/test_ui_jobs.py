import pytest
import threading

from flowmpeg.ui.jobs import BoundedOutput, JobManager, JobStatus, UiJob


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


def test_ui_job_snapshot_excludes_process_arguments() -> None:
    job = UiJob(
        "job-1",
        ("probe", "https://example.com/v.mp4?token=private"),
        "flowmpeg probe https://example.com/v.mp4?token=<redacted>",
    )

    snapshot = job.snapshot()

    assert snapshot.id == "job-1"
    assert "private" not in snapshot.display
    assert not hasattr(snapshot, "arguments")
    assert not hasattr(snapshot, "process")


def test_ui_job_manager_queues_runs_and_lists_jobs() -> None:
    manager = JobManager(runner=lambda job: 0)
    try:
        queued = manager.start(("errors",), "flowmpeg errors")
        finished = manager.wait(queued.id, timeout=2)

        assert finished.status is JobStatus.SUCCEEDED
        assert manager.get(queued.id) == finished
        assert manager.list() == (finished,)
    finally:
        manager.close()


def test_ui_job_manager_rejects_invalid_worker_counts() -> None:
    with pytest.raises(ValueError, match="between 1 and 4"):
        JobManager(max_parallel=0)


def test_ui_job_manager_runs_flowmpeg_without_a_shell() -> None:
    manager = JobManager()
    try:
        queued = manager.start(("errors",), "flowmpeg errors")
        finished = manager.wait(queued.id, timeout=10)

        assert finished.status is JobStatus.SUCCEEDED
        assert finished.returncode == 0
        assert "FMG200" in finished.output
    finally:
        manager.close()


def test_ui_job_manager_records_process_start_failures() -> None:
    def fail(job: UiJob) -> int:
        del job
        raise OSError("test process failure")

    manager = JobManager(runner=fail)
    try:
        queued = manager.start(("errors",), "flowmpeg errors")
        finished = manager.wait(queued.id, timeout=2)

        assert finished.status is JobStatus.FAILED
        assert finished.returncode == -1
        assert finished.output == "test process failure"
    finally:
        manager.close()


def test_ui_job_manager_rejects_nested_ui_servers() -> None:
    manager = JobManager(runner=lambda job: 0)
    try:
        with pytest.raises(ValueError, match="cannot be started from the UI"):
            manager.start(("ui",), "flowmpeg ui")
    finally:
        manager.close()


def test_ui_job_manager_cancels_queued_jobs() -> None:
    release = threading.Event()

    def wait_for_release(job: UiJob) -> int:
        del job
        release.wait(timeout=2)
        return 0

    manager = JobManager(max_parallel=1, runner=wait_for_release)
    try:
        first = manager.start(("errors",), "flowmpeg errors")
        second = manager.start(("commands",), "flowmpeg commands")

        assert manager.cancel(second.id) is True
        assert manager.get(second.id).status is JobStatus.CANCELLED  # type: ignore[union-attr]
        release.set()
        manager.wait(first.id, timeout=2)
    finally:
        release.set()
        manager.close()


def test_ui_job_manager_marks_running_jobs_cancelled() -> None:
    release = threading.Event()

    def wait_for_release(job: UiJob) -> int:
        del job
        release.wait(timeout=2)
        return 130

    manager = JobManager(runner=wait_for_release)
    try:
        queued = manager.start(("errors",), "flowmpeg errors")
        while manager.get(queued.id).status is JobStatus.QUEUED:  # type: ignore[union-attr]
            pass
        assert manager.cancel(queued.id) is True
        release.set()
        finished = manager.wait(queued.id, timeout=2)
        assert finished.status is JobStatus.CANCELLED
    finally:
        release.set()
        manager.close()


def test_ui_job_manager_cancels_work_during_shutdown() -> None:
    release = threading.Event()

    def wait_for_release(job: UiJob) -> int:
        del job
        release.wait(timeout=2)
        return 130

    manager = JobManager(runner=wait_for_release)
    queued = manager.start(("errors",), "flowmpeg errors")
    while manager.get(queued.id).status is JobStatus.QUEUED:  # type: ignore[union-attr]
        pass
    manager.close(wait=False)
    release.set()

    finished = manager.wait(queued.id, timeout=2)
    assert finished.status is JobStatus.CANCELLED


def test_ui_job_manager_clears_only_finished_jobs() -> None:
    manager = JobManager(runner=lambda job: 0)
    try:
        queued = manager.start(("errors",), "flowmpeg errors")
        manager.wait(queued.id, timeout=2)

        assert manager.clear_finished() == 1
        assert manager.get(queued.id) is None
        assert manager.clear_finished() == 0
    finally:
        manager.close()
