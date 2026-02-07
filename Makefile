.PHONY: install test lint typecheck pipeline pipeline-snowflake clean dbt-run dbt-test dbt-docs dbt-run-snowflake dbt-test-snowflake dashboard dashboard-snowflake

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

typecheck:
	mypy src/

pipeline:
	python -m src.pipeline.run

pipeline-snowflake:
	DB_BACKEND=snowflake python -m src.pipeline.run

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

dbt-run:
	cd dbt && dbt run --target postgres

dbt-test:
	cd dbt && dbt test --target postgres

dbt-docs:
	cd dbt && dbt docs generate --target postgres && dbt docs serve --target postgres

dbt-run-snowflake:
	cd dbt && dbt run --target snowflake

dbt-test-snowflake:
	cd dbt && dbt test --target snowflake

dashboard:
	streamlit run src/dashboard/app.py

dashboard-snowflake:
	DB_BACKEND=snowflake streamlit run src/dashboard/app.py
