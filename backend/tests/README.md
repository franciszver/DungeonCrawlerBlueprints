# Backend Tests

## Setup

Install test dependencies:

```bash
pip install -r requirements-test.txt
```

## Running Tests

Run all tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=../shared --cov=../functions --cov-report=html
```

Run specific test file:

```bash
pytest test_room_detector.py -v
```

Run only unit tests (skip integration):

```bash
pytest -m "not integration"
```

## Test Structure

- `test_room_detector.py` - Tests for room detection logic
- `test_room_generator.py` - Tests for procedural room generation
- `test_extend_handler.py` - Tests for /extend endpoint handler

## Mocking

Integration tests that require external API calls (OpenRouter, AWS) should be mocked using `pytest-mock` or `moto`.

Example:

```python
def test_with_mock(mocker):
    mock_api = mocker.patch('openrouter_client.requests.post')
    mock_api.return_value.json.return_value = {'rooms': []}
    # ... test code
```

## Coverage Goals

- Unit tests: >80% coverage
- Integration tests: Key workflows covered
- Edge cases: Invalid inputs, timeouts, errors

