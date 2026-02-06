.PHONY: install test lint typecheck pipeline pipeline-snowflake clean

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
