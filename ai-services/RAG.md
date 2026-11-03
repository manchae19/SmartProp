<!-- STEP_19_5_3B_CURRENT -->
# Step 19.5.3B — Ổn định RAG trên máy 16 GB

Đã tái hiện strict `POST /chat` trả 503 tại validator với mã
`GENERATED_RANKING_DRIFT`; Ollama trả 200 và sinh hoàn tất, SQL/FAISS thành công.
Adapter hiện dùng các ô text gắn cố định với Top 3 ID theo API khi có BĐS.
Qwen vẫn sinh text thực; server chỉ chuyển cấu trúc JSON và kiểm tra nguyên văn,
không sửa giá, nội dung hay xếp hạng. Câu hỏi chỉ có tiện ích giữ cách chọn bằng
chứng cũ. Đây là trả lời trích xuất có kiểm chứng, không phải diễn giải tự do.

Trên máy Local này, dùng cấu hình giữ model **0 giây** để giải phóng runner và
prompt cache sau mỗi câu trả lời. Đây là retention, không phải HTTP timeout.
Không đổi Ollama toàn máy, model storage, cấu hình Windows hoặc `.env`.
Mặc định trong `Settings` vẫn là 300 giây để tương thích; biến server
`RAG_OLLAMA_KEEP_ALIVE_SECONDS` nhận số nguyên từ 0 đến 300, không cho giữ vô hạn.
E5 CPU/FAISS tiếp tục được giữ trong Chat process.

Nếu Backend Local 8080 đã chạy đúng V1.1 và cổng 8001 trống, tại `F:\SmartProp`:

```powershell
.\.scratch\rag-ollama-venv\Scripts\python.exe -X utf8 .\.scratch\tinix-integration\step19-5-3b\start_chat.py --keep-alive-seconds 0
```

Launcher riêng của lần kiểm thử này đọc bí mật cục bộ vào environment, không in
ra terminal. Mặc định Research OFF. Chỉ thêm `--research` để thử nội bộ loopback;
route Research vẫn cần ADMIN JWT hợp lệ và demo key do server giữ. Không đưa key
vào Vue. Không chạy launcher nếu 8001 đang được dùng; nó sẽ từ chối thay process.
Swagger: `http://127.0.0.1:8001/docs`. `GET /chat/health` cho biết retention thực tế.

Sau idle, model không nằm trong `/api/ps` là hành vi dự kiến của profile 0 giây;
request sau nạp lại model. Phải chấp nhận độ trễ nạp lại. Không chạy nhiều tác vụ
AI nặng cùng lúc. Bộ kiểm thử có resource gate; ứng dụng không áp quota bộ nhớ OS.
Không suy ra đã có SLA nhiều người dùng hoặc khả năng chạy khi RAM gần cạn.

Log `RAG_DIAGNOSTIC` có requestId, endpoint, strict, stage, timing, mã lỗi và loại
transport exception. Không ghi question, facts, raw output, JWT, mật khẩu hay SQL.
Khi dependency không sẵn sàng/output không qua validator, `requireGeneration=false`
vẫn trả `EVIDENCE_ONLY`; strict vẫn có thể trả 503 đúng thiết kế.

Báo cáo và số đo: `.scratch/tinix-integration/step19-5-3b/` gồm
`RAG_503_ROOT_CAUSE.md`, `MEMORY_STABILITY_REPORT.md`, `FINAL_RAG_VERIFICATION.md`.
Phần Step 19.5.3 bên dưới là tài liệu lịch sử trước bản sửa này.

---


<!-- STEP_19_5_3_CURRENT -->
# Step 19.5.3 - Ollama runtime (historical)

The Windows integration now executes the existing `qwen3:4b-instruct` in Ollama
at `127.0.0.1:11434`, with CPU multilingual-e5-small and a persisted, versioned
FAISS IndexFlatIP. Current qualification is **PARTIAL**: real grounded generation,
semantic retrieval, SQL/GIS and security have passed targeted checks; sporadic
strict-generation rejection and limited system RAM remain documented.

The 326-document corpus and E5 revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3` produce 326 normalized 384-dimensional
vectors. `scripts/build_rag_index.py` writes a content-versioned `.faiss` artifact
and manifest; loaders verify source IDs/ACLs, revision, SHA-256, dimensions and
count before use. Research records never enter that shared PUBLIC index.

Ollama generates **extractive answer text**, not just IDs. Only verbatim supplied
fact sentences survive validation; the server appends scope labels/citations.
This intentionally blocks free-form paraphrases, inferred distances, new prices
and unsupported verification claims. `QWEN_GROUNDED_ANSWER` identifies accepted
text with real Ollama eval statistics. `EVIDENCE_ONLY` remains the safe fallback;
strict `requireGeneration=true` may return 503 instead of passing bad output.

No routes or Java modules were rewritten. Set these server-side variables for
the Ollama profile; secrets are environment-only and must not enter Vue:

- `RAG_LLM_PROVIDER=ollama`
- `RAG_OLLAMA_URL=http://127.0.0.1:11434`
- `RAG_OLLAMA_MODEL=qwen3:4b-instruct`
- `RAG_OLLAMA_DIGEST` = installed model digest from `/api/tags` (pin for qualification)
- `RAG_E5_PATH` = existing local multilingual-e5-small snapshot
- `RAG_INDEX_DIR` = versioned FAISS artifact directory
- `RAG_CORPUS_PATH` = verified PUBLIC corpus snapshot
- `RAG_BACKEND_TIMEOUT_SECONDS=30` (bounded 1?60, legacy default remains 10)
- `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` during serving

Research remains OFF by default. For explicitly enabled local research, use
`RAG_RESEARCH_ENABLED=true` plus server-held `RAG_DEMO_KEY` and a live ADMIN JWT.
The launch command remains `uvicorn rag_main:app --host 127.0.0.1 --port 8001
--no-proxy-headers` from ai-services, using the separate runtime. The old default
provider is retained for backward compatibility; provider selection is explicit.

The current installed runtime is `.scratch/rag-ollama-venv` on F:, separate from
valuation `.venv`. `requirements-rag-ollama.txt` records tested dependencies;
CPU torch is installed separately from its official CPU index. E5 was downloaded
explicitly in this step; serving stays offline. No Qwen model was pulled or
replaced, and `F:/Ollama/Models` was not modified by this integration.

GIS points are read-only source coordinates from published properties. MySQL
SRID 4326 uses `ST_Latitude`/`ST_Longitude`; do not substitute X/Y axis guesses.
Returned GeoJSON labels these as source coordinates, not survey-verified points.
No TiniX GPS, area centroid, property-to-POI distance or pin is inferred.

Acceptance reports: `.scratch/tinix-integration/step19-5-3/` contains
`RAG_INTEGRATION_REPORT.md`, `RAG_TEST_REPORT.md`, `RUNTIME_BENCHMARK.md`,
`CHAT_API_CONTRACT.md` and the raw private receipts. Historical Step 19.5.2
instructions below describe the earlier evidence-only environment.

---

# SmartProp grounded Chat API

Step 19.5.2 extracts the Qwen3-4B / multilingual-e5-small / FAISS code from
`notebooks/SmartProp_RAG_Chatbot.ipynb`. The notebook's three DEMO properties are
never imported. Valuation `main:app` and XGBoost remain separate.

The current local integration is **PARTIAL**: evidence-only answers work against
real Backend/MySQL data. Qwen/E5/FAISS inference has not been executed locally;
the existing Windows/Python 3.14 environment lacks their libraries and weights.
Nothing installs or downloads models automatically.

## Run public SAFE locally

Requires the existing Hybrid V1.1 Backend at `127.0.0.1:8080`, configured with
public SAFE policy. From the repository root, when port 8001 is free:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 .\ai-services\scripts\build_rag_corpus.py --output ai-services/var/rag/public-corpus.json
$env:RAG_CORPUS_PATH = (Resolve-Path 'ai-services/var/rag/public-corpus.json').Path
$env:RAG_RESEARCH_ENABLED = 'false'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
.\ai-services\.venv\Scripts\python.exe -X utf8 -m uvicorn rag_main:app --app-dir ai-services --host 127.0.0.1 --port 8001 --no-proxy-headers
```

Open `http://127.0.0.1:8001/docs`. The corpus is a public API snapshot, expires
after 24 hours, and must match the current catalog version. It contains area
profiles and POI evidence references, not all individual POIs or crawler rows.

`POST /chat` accepts `question`, optional `budgetVnd`, `purpose`, `propertyType`,
`minAreaSqm`, `district`, `ward`, `limit`, and `requireGeneration`. Unknown fields,
arbitrary SQL, caller-controlled mode and demo keys are rejected.

Responses include `answer`, `citations`, `recommendedProperties`, `evidence`,
`dataLimitations`, plus truthful generation/retrieval modes. Missing models use
`EVIDENCE_ONLY` / `TOOL_EVIDENCE_ONLY`; `requireGeneration=true` returns 503 when
the full model runtime is unavailable.

## Model runtime and permissions

- `requirements-rag.txt` is optional, for a separately qualified runtime. It
  records model-library versions from the notebook. Do not install over the
  valuation environment without compatibility validation.
- Set `RAG_QWEN_PATH` and `RAG_E5_PATH` only to existing local model snapshots.
  Loaders use `local_files_only=True`, `trust_remote_code=False`; Qwen uses NF4
  double quantization, fp16, non-thinking deterministic generation.
- Qwen can only select known fact IDs. The server renders exact API facts in
  Vietnamese, preserving recommendation order. Unsupported prose or IDs are
  rejected; the model never executes SQL or supplies prices.
- SQL is optional: `RAG_SQL_ENABLED=true`, credentials in `RAG_DB_USER` and
  `RAG_DB_PASSWORD`. The only repository query is a parameterized, bounded,
  READ ONLY projection of published platform IDs returned by the authorized
  Recommendation API. Target is fixed to `127.0.0.1:3306/smartprop`.
- Research is OFF by default. Explicit internal operation requires
  `RAG_RESEARCH_ENABLED=true` and server-side `RAG_DEMO_KEY`. The caller must be
  loopback with a live ADMIN Bearer token accepted by Spring. Do not put the
  demo key in Vue, Vite, request bodies, logs or URLs.
- Public requests never forward research credentials. Research properties stay
  request-local and never enter the shared public corpus/index.
- Colab's loopback address does not reach the developer PC. Remote Colab
  hosting/private transport and a Vue chat screen have not been implemented.
  Do not expose MySQL or relax the local-only tool target to work around this.

## Validation evidence

New tests: `python -m unittest discover -s ai-services/tests -p test_rag.py -v`.
Actual local acceptance: 18 unit checks, 24 live HTTP checks, 8 platform rows
matched by SQL, and 30 returned research IDs checked read-only. Model inference
and semantic retrieval remain untested because dependencies/weights are absent.

Detailed reports and private research response evidence are in
`.scratch/tinix-integration/step19-5-2/`: `RAG_INTEGRATION_REPORT.md`,
`RAG_TEST_REPORT.md`, `CHAT_API_CONTRACT.md`. Do not publish private response
artifacts as verified listings.
