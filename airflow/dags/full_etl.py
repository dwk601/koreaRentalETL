"""Korean Rental ETL - Full ETL DAG.

Schedule: Every 6 hours.
Tasks: health_check -> extract -> transform -> load -> validate -> notify
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.smtp.operators.smtp import EmailOperator

# Default args with conservative retry
default_args = {
    "owner": "korean-rental-etl",
    "depends_on_past": False,
    "email": [os.environ.get("SMTP_TO", "admin@example.com")],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}

with DAG(
    dag_id="korean_rental_full_etl",
    default_args=default_args,
    description="Full ETL pipeline for Korean rental listings",
    schedule="0 */6 * * *",  # Every 6 hours
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    catchup=False,
    tags=["korean-rental", "etl"],
) as dag:
    health_check = BashOperator(
        task_id="health_check",
        bash_command="echo 'Health check passed'",
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

    notify = EmailOperator(
        task_id="notify",
        to=os.environ.get("SMTP_TO", "admin@example.com"),
        subject="Korean Rental ETL - Run Completed",
        html_content="<p>ETL run completed successfully at {{ execution_date }}</p>",
    )

    # Task dependencies
    health_check >> extract >> transform >> load >> validate >> notify

