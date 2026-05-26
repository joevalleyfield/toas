
# 569: IndexError on empty frontier content in step runtime

## Symptom

Runtime crash with `IndexError: list index out of range` during `toas step`.

Traceback snippet:
```python
  File ".../src/toas/runtime/step_runtime.py", line 757, in run_step
    str(frontier.get("content", "")).splitlines()[0][:160]
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
IndexError: list index out of range
```

The crash occurs when `frontier["content"]` is empty (empty string or missing). `str().splitlines()` returns `[]`, and accessing `[0]` raises the error. This masks the underlying reason for the empty content (e.g., failed LLM generation, malformed transcript).

## Resolution

Modified `src/toas/runtime/step_runtime.py` line ~757 to:
1. Check if `frontier.get("content")` is truthy before slicing.
2. Use direct string slicing `[:160]` instead of `splitlines()[0][:160]` to avoid list indexing.

```python
# Before
"frontier_preview": (
    str(frontier.get("content", "")).splitlines()[0][:160]
    if isinstance(frontier, dict)
    else None
),

# After
"frontier_preview": (
    str(frontier.get("content", ""))[:160]
    if isinstance(frontier, dict) and frontier.get("content")
    else None
),
```

This makes the code robust against empty content, allowing the runtime to continue (or fail later with a clearer error) instead of crashing on a list index error.

## Notes

- This is a defensive fix for the symptom. The root cause of empty `content` (e.g., LLM failure) should be investigated if the error recurs.
- Off-by-one frontier issue (task 567) remains separate and unfixed."