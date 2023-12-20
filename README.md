# Purpose
Experiments for determining the maintenance status of an EV charging station

# Usage
TBD

# Setting Up Dev Environment
## [With Poetry Installed](https://python-poetry.org/docs/basic-usage/#activating-the-virtual-environment)
```bash
poetry shell
```

## Without Poetry
First, create a virtual environment with your tool of choice (e.g. `venv` or `conda`) and activate it. Then:

```bash
pip install -e .
```

This works because `pip` and `setuptools` [now seem capable](https://til.simonwillison.net/python/pyproject) of reading `pyproject.toml` files!
