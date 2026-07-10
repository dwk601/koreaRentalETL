"""Korean Rental ETL - Full ETL DAG.

Schedule: Every 6 hours.
Tasks: health_check -> source_preflight -> extract -> transform -> load -> validate [-> notify]
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.smtp.operators.smtp import EmailOperator

smtp_to = os.environ.get("SMTP_TO")

default_args = {
    "owner": "korean-rental-etl",
    "depends_on_past": False,
    "email": [smtp_to] if smtp_to else [],
    "email_on_failure": bool(smtp_to),
    "email_on_retry": False,
    "retries": 1,
    "execution_timeout": timedelta(hours=4),
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}

with DAG(
    dag_id="korean_rental_full_etl",
    default_args=default_args,
    description="Full ETL pipeline for Korean rental listings",
    schedule="0 */6 * * *",
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=5),
    tags=["korean-rental", "etl"],
) as dag:
    health_check = BashOperator(
        task_id="health_check",
        bash_command="echo 'Health check passed'",
    )

    source_preflight = BashOperator(
        task_id="source_preflight",
        bash_command="korean-rental-etl sources check",
    )

    extract = BashOperator(
        task_id="extract",
        bash_command='korean-rental-etl extract --all --dag-id "{{ dag.dag_id }}" --run-id "{{ run_id }}"',
    )

    transform = BashOperator(
        task_id="transform",
        bash_command='korean-rental-etl transform --all --dag-id "{{ dag.dag_id }}" --run-id "{{ run_id }}"',
    )

    load = BashOperator(
        task_id="load",
        bash_command='korean-rental-etl load --dag-id "{{ dag.dag_id }}" --run-id "{{ run_id }}"',
    )

    validate = BashOperator(
        task_id="validate",
        bash_command='korean-rental-etl validate --run-id "{{ run_id }}"',
    )

    health_check >> source_preflight >> extract >> transform >> load >> validate

    if smtp_to:
        notify = EmailOperator(
            task_id="notify",
            to=smtp_to,
            subject="Korean Rental ETL - Run Completed",
            html_content="<p>ETL run completed successfully at {{ execution_date }}</p>",
        )
        validate >> notify
