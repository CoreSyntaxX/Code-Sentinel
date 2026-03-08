# Fix Import Error in test_models.py

## Issue
`No module named 'models'` error when running `tests/test_models.py`

## Root Cause
The test file adds `src` to the Python path but then tries to import from `models.finding` instead of `src.models.finding`.

## Solution
Update imports in `tests/test_models.py` to use the correct module path.

## Changes Required
- [ ] Update import in tests/test_models.py:
  - Change `from models.finding import ...` to `from src.models.finding import ...`
  - Change `from models.scan_context import ...` to `from src.models.scan_context import ...`
  - Change `from models.rule import ...` to `from src.models.rule import ...`

## Verification
Run `python tests/test_models.py` to confirm the fix works.

