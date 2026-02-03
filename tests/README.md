# MetalDeploy Test Suite

This directory is organized into unit and integration tests.

## Structure

- `tests/unit/`: Fast unit tests that mock external dependencies (SSH, Git, etc.).
- `tests/integration/`: Docker-based integration tests that simulate a real SSH deployment environment.

## Running Tests

### All Tests
```bash
make test
# OR
pytest tests/ -v -s
```

### Unit Tests
```bash
make test-unit
# OR
pytest tests/unit/ -v
```

### Integration Tests
```bash
pytest tests/integration/ -v -s
```

### Why `-s` is Required

Pytest's default output capture mechanism interferes with the SSH connections used by Fabric/Paramiko. The `-s` flag (`--capture=no`) disables this capture, allowing the SSH connections to work properly.

## Test Suite

The integration tests include:
1. **SSH Connection Test**: Verifies basic SSH connectivity
2. **Git Tools Test**: Confirms Git is installed on the remote
3. **Environment File Generation Test**: Tests remote `.env` file creation
4. **Deploy Simulation Test**: Validates deployment command execution

## Docker Environment

- **Container**: Ubuntu 22.04 with SSH, Git, Python3
- **Port**: 2222 (mapped to container's port 22)
- **Credentials**: root/root
- **Lifecycle**: Automatically managed by pytest fixtures

The Docker container is automatically started before tests and stopped after completion.
