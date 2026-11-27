# Isolated FastAPI and RAG tests

Run from a clean checkout using a dedicated Python 3.14 environment. The
commands below start in the repository root and use PowerShell.

~~~powershell
py -3.14 -m venv .venv-rag
.\.venv-rag\Scripts\python.exe -m pip install -r ai-services/requirements-dev.txt -r ai-services/requirements-rag-documents.txt pytest==9.2.0 pymysql==1.2.4 faiss-cpu==1.15.1 pandas==3.1.1 scikit-learn==1.9.1
Set-Location ai-services

$rag = @(Get-ChildItem tests/test_rag*.py | ForEach-Object { "tests/$($_.Name)" })
..\.venv-rag\Scripts\python.exe -B tests/run_isolated.py -q @rag
~~~

For valuation coverage, set `SMARTPROP_V1_3_MODEL_DIR` to an isolated copy of
the approved V1.3 artifacts. Check the SHA256 of the model, feature schema,
and calibration against `app/models/xgboost/predictor_v1_3.py` before running
the suite. Check both copies again afterwards. The loader still verifies
each checksum. V6 tests that need the optional V6 artifacts can skip when
those artifacts are absent.

~~~powershell
$env:SMARTPROP_V1_3_MODEL_DIR = (Resolve-Path 'path/to/verified-v1_3').Path
..\.venv-rag\Scripts\python.exe -B tests/run_isolated.py --collect-only -q tests
..\.venv-rag\Scripts\python.exe -B tests/run_isolated.py -q --tb=short tests
~~~

The runner exits with pytest's result. It disables ambient pytest plugins
and RAG SQL, and blocks live Python socket operations, allowing ephemeral
loopback sockets owned by that test process. A blocked attempt fails the run
even if code catches the exception. Use in-memory ASGI, HTTP transports,
and mocked SQL for these tests. The guard does not sandbox child processes
or arbitrary native binaries. Only run the repository's offline test suite.
