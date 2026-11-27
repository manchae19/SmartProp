# Cross-flow parity harness

Minimised capture + reproducible comparison. Only model-relevant fields are written
(see `CAPTURE_FIELDS`); titles, descriptions, addresses, headers, cookies and tokens
are never captured. The output JSONL is temporary and must not be committed.

See the module docstring of `run_parity.py` for the exact three-step procedure.
