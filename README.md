# json-schema-to-class [![Build Status](https://travis-ci.com/FebruaryBreeze/json-schema-to-class.svg?branch=master)](https://travis-ci.com/FebruaryBreeze/json-schema-to-class) [![codecov](https://codecov.io/gh/FebruaryBreeze/json-schema-to-class/branch/master/graph/badge.svg)](https://codecov.io/gh/FebruaryBreeze/json-schema-to-class) [![PyPI version](https://badge.fury.io/py/json-schema-to-class.svg)](https://pypi.org/project/json-schema-to-class/)

Convert JSON Schema into Python Class

## Installation

Need Python 3.6+.

```bash
pip install json-schema-to-class
```

## Usage

For example, convert [tests/test_schema.json](tests/test_schema.json) into Python class:

```bash
# generate & highlight
json-schema-to-class tests/test_schema.json --indent 2 | pygmentize

# or generate to file
json-schema-to-class tests/test_schema.json -o tests/schema_build.py
```

Get `tests/schema_build.py` as follow:

```python
from typing import List


class WarmUp:
    def __init__(self, values: dict = None):
        values = values if values is not None else {}
        self.start: float = values.get("start", 0.0)
        self.steps: int = values.get("steps", 0)


class LrSchedulerConfig:
    def __init__(self, values: dict = None):
        values = values if values is not None else {}
        self.lr_mode: str = values.get("lr_mode", 'cos')
        self.base_lr: float = values.get("base_lr", None)
        self.target_lr: float = values.get("target_lr", 0.0002)
        self.decay_factor: float = values.get("decay_factor", 0.1)
        self.milestones: List[float] = values.get("milestones", [0.3, 0.6, 0.9])
        self.lr_decay: float = values.get("lr_decay", 0.98)
        self.warm_up = WarmUp(values=values.get("warm_up"))


class LrSchedulerConfigs(list):
    def __init__(self, values: list = None):
        super().__init__()
        values = values if values is not None else []
        self[:] = [LrSchedulerConfig(value) for value in values]
```
