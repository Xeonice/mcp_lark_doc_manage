import os
import json
from collections import OrderedDict
from pathlib import Path

# Set testing environment
os.environ["TESTING"] = "true"

def load_test_data(filename):
    """Load test data from a file."""
    with open(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'markdown', filename), 'r', encoding='utf-8') as f:
        return f.read()

def load_expected_result(filename):
    """Load expected result from a file."""
    with open(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'json', filename), 'r', encoding='utf-8') as f:
        data = json.load(f)
        return convert_to_ordered_dict(data)

def convert_to_ordered_dict(obj):
    """Convert a dictionary to OrderedDict recursively."""
    if isinstance(obj, dict):
        result = OrderedDict()
        for k, v in obj.items():
            result[k] = convert_to_ordered_dict(v)
        return result
    elif isinstance(obj, list):
        return [convert_to_ordered_dict(item) for item in obj]
    return obj 