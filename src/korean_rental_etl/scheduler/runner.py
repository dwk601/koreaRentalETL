"""Small, durable workflow runner used by Supercronic.

This preserves the former Airflow task order, retries, timeouts, run identifiers,
audit metadata, persisted history, logs, and optional SMTP notifications without
running an Airflow metadata database, scheduler, or webserver.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import smtplib
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import IO, cast

STATE = Path(os.getenv("SCHEDULER_STATE_DIR", "/var/lib/korean-rental-etl"))
LOGS = Path(os.getenv("SCHEDULER_LOG_DIR", "/var/log/korean-rental-etl"))
TERMINATE_GRACE_SECONDS = 10


@dataclass(frozen=True)
class Task:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class Workflow:
    dag_id: str
    schedule: str
    tasks: tuple[Task, ...]
    retries: int
    retry_delay_seconds: int = 300
    task_timeout_seconds: int = 14400
    run_timeout_seconds: int = 18000


WORKFLOWS = {
    "korean_rental_full_etl": Workflow(
        dag_id="korean_rental_full_etl",
        schedule="0 */6 * * *",
        tasks=(
            Task("health_check", ("python", "-c", "print('Health check passed')")),
            Task("source_preflight", ("korean-rental-etl", "sources", "check")),
            Task("extract", ("korean-rental-etl", "extract", "--all")),
            Task("transform", ("korean-rental-etl", "transform", "--all")),
            Task("load", ("korean-rental-etl", "load")),
            Task("validate", ("korean-rental-etl", "validate")),
        ),
        retries=1,
    ),
    "korean_rental_cleanup": Workflow(
        dag_id="korean_rental_cleanup",
        schedule="0 3 * * *",
        tasks=(
            Task(
                "mark_stale_listings_inactive",
                ("korean-rental-etl", "cleanup", "mark-stale", "--days", "14"),
            ),
            Task(
                "purge_old_raw_pages",
                ("korean-rental-etl", "cleanup", "purge-pages", "--days", "90"),
            ),
        ),
        retries=2,
    ),
}


def paths() -> tuple[Path, Path]:
    STATE.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    return STATE / "history.jsonl", STATE / "runner.lock"


def history(limit: int = 20) -> list[dict[str, object]]:
    history_path, _ = paths()
    if not history_path.exists():
        return []
    lines = history_path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-limit:]]


def record(run: dict[str, object]) -> None:
    history_path, _ = paths()
    with history_path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(run, ensure_ascii=False) + "\n")
        output.flush()
        os.fsync(output.fileno())


def notify(run: dict[str, object]) -> None:
    recipient = os.getenv("SMTP_TO")
    host = os.getenv("SMTP_HOST")
    if not recipient or not host:
        return

    message = EmailMessage()
    message["To"] = recipient
    message["From"] = os.getenv("SMTP_FROM", "etl@localhost")
    message["Subject"] = f"Korean Rental ETL - {run['status']}"
    message.set_content(json.dumps(run, ensure_ascii=False, indent=2))
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "25")), timeout=30) as smtp:
        if os.getenv("SMTP_STARTTLS", "false").lower() == "true":
            smtp.starttls()
        if os.getenv("SMTP_USER"):
            smtp.login(os.environ["SMTP_USER"], os.getenv("SMTP_PASSWORD", ""))
        smtp.send_message(message)


def _command_for(task: Task, workflow: Workflow, run_id: str) -> list[str]:
    command = list(task.command)
    if task.name in {"extract", "transform", "load"}:
        command += ["--dag-id", workflow.dag_id, "--run-id", run_id]
    elif task.name == "validate":
        command += ["--run-id", run_id]
    return command


def _stop_process(child: subprocess.Popen[bytes] | None) -> None:
    if child is None or child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def _run_task(
    command: list[str],
    output: IO[bytes],
    timeout_seconds: float,
) -> tuple[subprocess.Popen[bytes], int]:
    child = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
    try:
        return child, child.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _stop_process(child)
        return child, 124


def run_workflow(dag_id: str, run_id: str | None = None) -> int:
    workflow = WORKFLOWS[dag_id]
    run_id = run_id or "scheduled__" + datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    _, lock_path = paths()

    with lock_path.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another workflow is already running; skipping this invocation.", file=sys.stderr)
            return 75

        run: dict[str, object] = {
            "dag_id": dag_id,
            "run_id": run_id,
            "status": "running",
            "started_at": datetime.now(UTC).isoformat(),
            "tasks": [],
        }
        record(run)
        started = time.monotonic()
        child: subprocess.Popen[bytes] | None = None
        interrupted = False

        def stop(*_: object) -> None:
            nonlocal interrupted
            interrupted = True
            _stop_process(child)

        previous_handlers = {
            sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)
        }
        log_path = LOGS / f"{dag_id}__{run_id.replace('/', '_')}.log"
        try:
            with log_path.open("ab", buffering=0) as output:
                for task in workflow.tasks:
                    command = _command_for(task, workflow, run_id)
                    exit_code = 1
                    for attempt in range(workflow.retries + 1):
                        remaining = workflow.run_timeout_seconds - (time.monotonic() - started)
                        if remaining <= 0 or interrupted:
                            exit_code = 124 if not interrupted else 143
                            break
                        child, exit_code = _run_task(
                            command,
                            output,
                            min(workflow.task_timeout_seconds, remaining),
                        )
                        task_result = {
                            "name": task.name,
                            "attempt": attempt + 1,
                            "exit_code": exit_code,
                        }
                        tasks = cast("list[dict[str, object]]", run["tasks"])
                        tasks.append(task_result)
                        if exit_code == 0:
                            break
                        if attempt < workflow.retries and not interrupted:
                            time.sleep(workflow.retry_delay_seconds)
                    if exit_code:
                        run["status"] = "cancelled" if interrupted else "failed"
                        break
                else:
                    run["status"] = "success"
        except Exception as error:
            run["status"] = "failed"
            run["error"] = f"{type(error).__name__}: {error}"
        finally:
            for sig, handler in previous_handlers.items():
                signal.signal(sig, handler)
            run.update(finished_at=datetime.now(UTC).isoformat(), log_path=str(log_path))
            record(run)

    try:
        notify(run)
    except Exception as error:
        print(f"SMTP notification failed: {error}", file=sys.stderr)
    return 0 if run["status"] == "success" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="etl-runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Run one workflow immediately")
    run_parser.add_argument("workflow", choices=WORKFLOWS)
    run_parser.add_argument("--run-id")
    subparsers.add_parser("status", help="Print the latest persisted run")
    history_parser = subparsers.add_parser("history", help="Print persisted run history")
    history_parser.add_argument("--limit", type=int, default=20)
    subparsers.add_parser("healthcheck", help="Check writable scheduler state")
    subparsers.add_parser("workflows", help="Print workflow definitions")
    args = parser.parse_args(argv)

    if args.command == "run":
        return run_workflow(args.workflow, args.run_id)
    if args.command == "healthcheck":
        history_path, lock_path = paths()
        for path in (history_path, lock_path):
            with path.open("a", encoding="utf-8"):
                pass
        return 0
    if args.command == "workflows":
        print(json.dumps({name: asdict(item) for name, item in WORKFLOWS.items()}, indent=2))
        return 0

    rows = history(getattr(args, "limit", 20))
    result = rows[-1] if rows and args.command == "status" else rows
    if args.command == "status" and not rows:
        result = {"status": "never-run"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
