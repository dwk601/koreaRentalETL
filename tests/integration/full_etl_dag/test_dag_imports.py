import os

import pytest
from airflow.models import DagBag


@pytest.mark.integration
def test_dag_imports() -> None:
    """Assert that all DAGs in the airflow/dags directory can be loaded without import errors."""
    dag_dir = os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ),
        "airflow",
        "dags",
    )
    assert os.path.exists(dag_dir), f"DAG directory does not exist: {dag_dir}"

    dagbag = DagBag(dag_folder=dag_dir, include_examples=False)

    # Assert that there are no import errors in any of the loaded DAGs
    import_errors = dagbag.import_errors
    assert len(import_errors) == 0, f"DAG import errors found: {import_errors}"
