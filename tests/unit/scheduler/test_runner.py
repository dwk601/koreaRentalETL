import json
from dataclasses import replace

from korean_rental_etl.scheduler import runner


def test_workflows_preserve_airflow_schedules_and_task_order():
    full = runner.WORKFLOWS["korean_rental_full_etl"]
    cleanup = runner.WORKFLOWS["korean_rental_cleanup"]

    assert full.schedule == "0 */6 * * *"
    assert full.retries == 1
    assert full.task_timeout_seconds == 14400
    assert full.run_timeout_seconds == 18000
    assert [task.name for task in full.tasks] == [
        "health_check",
        "source_preflight",
        "extract",
        "transform",
        "load",
        "validate",
    ]
    assert cleanup.schedule == "0 3 * * *"
    assert cleanup.retries == 2
    assert [task.command for task in cleanup.tasks] == [
        ("korean-rental-etl", "cleanup", "mark-stale", "--days", "14"),
        ("korean-rental-etl", "cleanup", "purge-pages", "--days", "90"),
    ]


def test_command_propagates_same_audit_identifiers():
    workflow = runner.WORKFLOWS["korean_rental_full_etl"]
    tasks = {task.name: task for task in workflow.tasks}

    assert runner._command_for(tasks["extract"], workflow, "run-1")[-4:] == [
        "--dag-id",
        "korean_rental_full_etl",
        "--run-id",
        "run-1",
    ]
    assert runner._command_for(tasks["validate"], workflow, "run-1")[-2:] == [
        "--run-id",
        "run-1",
    ]
    assert runner._command_for(tasks["source_preflight"], workflow, "run-1") == [
        "korean-rental-etl",
        "sources",
        "check",
    ]


def test_successful_run_executes_in_order_and_persists_history(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "STATE", tmp_path / "state")
    monkeypatch.setattr(runner, "LOGS", tmp_path / "logs")
    workflow = replace(
        runner.WORKFLOWS["korean_rental_full_etl"],
        tasks=(runner.Task("extract", ("extract",)), runner.Task("validate", ("validate",))),
        retries=0,
    )
    monkeypatch.setitem(runner.WORKFLOWS, workflow.dag_id, workflow)
    commands = []

    def fake_run(command, output, timeout):
        commands.append(command)
        return None, 0

    monkeypatch.setattr(runner, "_run_task", fake_run)
    monkeypatch.setattr(runner, "notify", lambda run: None)

    assert runner.run_workflow(workflow.dag_id, "manual-1") == 0
    assert commands == [
        ["extract", "--dag-id", workflow.dag_id, "--run-id", "manual-1"],
        ["validate", "--run-id", "manual-1"],
    ]
    rows = runner.history()
    assert [row["status"] for row in rows] == ["running", "success"]
    assert rows[-1]["tasks"] == [
        {"name": "extract", "attempt": 1, "exit_code": 0},
        {"name": "validate", "attempt": 1, "exit_code": 0},
    ]


def test_failed_task_retries_and_stops_following_tasks(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "STATE", tmp_path / "state")
    monkeypatch.setattr(runner, "LOGS", tmp_path / "logs")
    workflow = replace(
        runner.WORKFLOWS["korean_rental_full_etl"],
        tasks=(runner.Task("extract", ("extract",)), runner.Task("load", ("load",))),
        retries=1,
        retry_delay_seconds=0,
    )
    monkeypatch.setitem(runner.WORKFLOWS, workflow.dag_id, workflow)
    commands = []

    def fake_run(command, output, timeout):
        commands.append(command)
        return None, 2

    monkeypatch.setattr(runner, "_run_task", fake_run)
    monkeypatch.setattr(runner, "notify", lambda run: None)

    assert runner.run_workflow(workflow.dag_id, "failed-1") == 1
    assert len(commands) == 2
    final = runner.history()[-1]
    assert final["status"] == "failed"
    assert [task["attempt"] for task in final["tasks"]] == [1, 2]


def test_cli_status_and_workflows(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(runner, "STATE", tmp_path / "state")
    monkeypatch.setattr(runner, "LOGS", tmp_path / "logs")

    assert runner.main(["status"]) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "never-run"}
    assert runner.main(["workflows"]) == 0
    assert "korean_rental_full_etl" in json.loads(capsys.readouterr().out)
    assert runner.main(["healthcheck"]) == 0
