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

Install Node.js using the version range in `frontend/package.json` to run the
Python-to-browser contract tests. These tests pass actual FastAPI responses to
the frontend modules in a Node process. They need no HTTP listener.

For the Spring strict-area integration test, use a fresh loopback-only MySQL
instance with a separate datadir and an empty `rag_area_fixture` schema. Give a
dedicated `rag_area_fixture` test user access to that schema only. Check
`@@port`, `@@datadir` and `@@server_uuid` against the fixture identity and
set `RAG_AREA_FIXTURE_PORT`, `RAG_AREA_FIXTURE_DATADIR` and
`RAG_AREA_FIXTURE_UUID` accordingly. Supply the test user's password via
`RAG_AREA_FIXTURE_PASSWORD`. From `backend`, run
`./mvnw.cmd "-Dtest=PropertyStrictAreaIT" test`. The test verifies the
identity and empty schema before creating temporary fixture tables. It runs
the real controller and JPA specification against MySQL. Ports 3306, 3307
and 3311 are rejected. The fixture does not run Flyway.
