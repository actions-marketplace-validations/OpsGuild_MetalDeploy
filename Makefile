.PHONY: test test-unit test-coverage lint install-dev clean

# Install development dependencies
install-dev:
	poetry install

# Run all tests
test:
	poetry run pytest tests/ -v -s --cov=src --cov=main --cov-report=xml

# Run only unit tests (fast)
test-unit:
	poetry run pytest tests/unit/ -v

# Run integration tests (requires Docker)
test-integration:
	poetry run pytest tests/integration/ -v -s

# Run tests with coverage
test-coverage:
	poetry run pytest tests/unit/ --cov=src --cov=main --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

# Run linting
lint:
	poetry run flake8 .
	poetry run black --check .
	poetry run isort --check-only .

# Format code
format:
	poetry run black .
	poetry run isort .

# Clean generated files
clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

# Validate action.yml
validate:
	poetry run python -c "import yaml; yaml.safe_load(open('action.yml'))"
	@grep -q "name:" action.yml || (echo "❌ Missing 'name' in action.yml" && exit 1)
	@grep -q "description:" action.yml || (echo "❌ Missing 'description' in action.yml" && exit 1)
	@grep -q "runs:" action.yml || (echo "❌ Missing 'runs' in action.yml" && exit 1)
	@echo "✅ action.yml is valid and structurally correct"
