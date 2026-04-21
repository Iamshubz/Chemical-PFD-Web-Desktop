# Desktop Frontend Unit Tests

This folder contains module-wise unit tests for the desktop frontend.

## Run Tests

Activate your Python environment first, then run tests.

From repository root:

```bash
python -m pytest desktop-frontend/desktop-frontend-UnitTests -q
```

From this folder:

```bash
pytest -q
```

Run a single file:

```bash
pytest test_validation.py -q
```

## Test Modules

- `test_validation.py`: graph validation behavior
- `test_label_generation.py`: label formatting and metadata loading
- `test_routing.py`: connection and pathfinding behavior
- `test_component_widget.py`: component widget behavior
- `test_component_library.py`: component library behavior
- `test_canvas_resources.py`: canvas resource utility behavior
- `test_api_client.py`: API client behavior
