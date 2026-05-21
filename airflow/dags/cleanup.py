"""Korean Rental ETL - Cleanup DAG.

Schedule: Daily at 3 AM.
Tasks: mark_stale_listings_inactive, purge_old_raw_pages
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

# Default args
default_args = {
    "owner": "korean-rental-etl",
    "depends_on_past": False,
    "email": [os.environ.get("SMTP_TO", "admin@example.com")],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="korean_rental_cleanup",
    default_args=default_args,
    description="Cleanup stale listings and old raw pages",
    schedule="0 3 * * *",  # Daily at 3 AM
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    catchup=False,
    tags=["korean-rental", "cleanup"],
) as dag:
    mark_stale = BashOperator(
        task_id="mark_stale_listings_inactive",
        bash_command="korean-rental-etl cleanup mark-stale --days 14",
    )

    purge_raw = BashOperator(
        task_id="purge_old_raw_pages",
        bash_command="korean-rental-etl cleanup purge-pages --days 90",
    )

    mark_stale >> purge_raw

