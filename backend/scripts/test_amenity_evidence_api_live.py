"""Live Integration & Acceptance Test Suite for Step 19.4.1D: Amenity Evidence API.

Tests real HTTP endpoints against the canonical Spring Boot backend running in
SAFE_READ_ONLY mode:
1. GET /api/v1/amenities/summary (Catalog metadata, 82 areas, 1323 POIs, weights)
2. GET /api/v1/amenities/areas (Full listing & filtering by level and district)
3. GET /api/v1/amenities/lookup (Ward, District, Corridor, Prefix handling, Fallbacks)
4. GET /api/v1/amenities/{areaId} (Direct retrieval by area slug)
5. Missing & Invalid Area Graceful Error Handling (404 Not Found)
6. Security Boundary Audit (Research APIs require ROLE_ADMIN, Amenities GET is public)
7. Query Latency & Performance Benchmark (50 sequential requests)
8. Spatial Attribution & Data Limitations Audit (Zero fake coordinates, zero fake distances)
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(os.environ.get("SMARTPROP_ROOT", Path(__file__).resolve().parents[2]))
OUT_DIR = ROOT / ".scratch/tinix-integration/step19-4-1d"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PORT = 8089
BASE_URL = f"http://127.0.0.1:{PORT}"

# Load runtime environment from run-recommendation-local.py
spec = importlib.util.spec_from_file_location("rec", ROOT / "backend/scripts/run-recommendation-local.py")
rec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rec)

jar = rec.artifact()
env = rec.private_environment()

rt = ROOT / ".scratch/devtools/runtime.json"
jdk = os.environ.get("JAVA_HOME")
if not jdk and rt.exists():
    jdk = json.loads(rt.read_text())["jdk"]
java = Path(jdk) / "bin/java.exe" if jdk else Path(shutil.which("java") or "")
if not java.is_file():
    raise RuntimeError("JDK21 required")

command = rec.command(java, jar, PORT)

print(f"[*] Starting Spring Boot Backend on port {PORT} in SAFE_READ_ONLY mode...", flush=True)
boot_log_file = open(OUT_DIR / "backend_live_test.log", "w", encoding="utf-8")
proc = subprocess.Popen(command, cwd=ROOT / "backend", env=env, stdout=boot_log_file, stderr=subprocess.STDOUT)

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def http_get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "SmartProp-Test/1.0"})
    start = time.perf_counter()
    try:
        with opener.open(req, timeout=10) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000
            data = resp.read()
            return resp.status, json.loads(data.decode("utf-8")), elapsed_ms
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        data = e.read()
        try:
            body = json.loads(data.decode("utf-8"))
        except Exception:
            body = data.decode("utf-8", errors="replace")
        return e.code, body, elapsed_ms

def http_post_anonymous(path, json_body="{}"):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(
        url,
        data=json_body.encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "SmartProp-Test/1.0"},
        method="POST"
    )
    try:
        with opener.open(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")

test_results = {
    "step": "19.4.1D",
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "port": PORT,
    "tests": {},
    "performance": {},
    "overall": "UNKNOWN"
}

try:
    # 1. Wait for Actuator Health
    print("[*] Waiting for backend to become healthy...")
    ready = False
    for _ in range(60):
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            raise RuntimeError(f"Backend died on startup: {stderr.decode(errors='replace')}")
        try:
            with opener.open(f"{BASE_URL}/actuator/health", timeout=2) as r:
                if r.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(1)

    if not ready:
        raise RuntimeError("Timed out waiting for Spring Boot /actuator/health")
    print("[+] Backend is UP and HEALTHY on port", PORT)

    # TEST 1: Summary API
    print("\n--- TEST 1: Catalog Summary API ---")
    status, body, ms = http_get("/api/v1/amenities/summary")
    print(f"Status: {status}, Total Areas: {body.get('totalAreasAnalyzed')}, Total POIs: {body.get('totalEffectivePois')} ({ms:.1f}ms)")
    t1_pass = (
        status == 200 and
        body.get("totalAreasAnalyzed") == 82 and
        body.get("totalEffectivePois") == 1323 and
        body.get("countsByLevel", {}).get("DISTRICT") == 7 and
        body.get("countsByLevel", {}).get("WARD") == 55 and
        body.get("countsByLevel", {}).get("CORRIDOR") == 20 and
        body.get("livingPurposeWeights", {}).get("essentials") == 0.25 and
        body.get("livingPurposeWeights", {}).get("transit") == 0.15 and
        body.get("livingPurposeWeights", {}).get("recreation") == 0.20
    )
    test_results["tests"]["test1_summary"] = {
        "status": status,
        "pass": t1_pass,
        "payload": body,
        "latency_ms": round(ms, 2)
    }
    assert t1_pass, f"Test 1 failed: {body}"

    # TEST 2: Areas List & Filters
    print("\n--- TEST 2: Areas List & Filters ---")
    status_all, all_areas, ms_all = http_get("/api/v1/amenities/areas")
    status_dist, dist_areas, _ = http_get("/api/v1/amenities/areas?level=DISTRICT")
    status_ward, ward_areas, _ = http_get("/api/v1/amenities/areas?level=WARD")
    status_corr, corr_areas, _ = http_get("/api/v1/amenities/areas?level=CORRIDOR")
    status_filtdist, filtdist_areas, _ = http_get("/api/v1/amenities/areas?district=Ngu+Hanh+Son")

    print(f"Total: {len(all_areas)}, Districts: {len(dist_areas)}, Wards: {len(ward_areas)}, Corridors: {len(corr_areas)}, Ngũ Hành Sơn areas: {len(filtdist_areas)}")
    t2_pass = (
        status_all == 200 and len(all_areas) == 82 and
        status_dist == 200 and len(dist_areas) == 7 and
        status_ward == 200 and len(ward_areas) == 55 and
        status_corr == 200 and len(corr_areas) == 20 and
        status_filtdist == 200 and len(filtdist_areas) > 0 and
        all(a["parentDistrict"] == "Ngũ Hành Sơn" for a in filtdist_areas)
    )
    test_results["tests"]["test2_areas_filters"] = {
        "pass": t2_pass,
        "total_count": len(all_areas),
        "district_count": len(dist_areas),
        "ward_count": len(ward_areas),
        "corridor_count": len(corr_areas),
        "filtered_nguhanhson_count": len(filtdist_areas)
    }
    assert t2_pass, "Test 2 failed"

    # TEST 3: Ward Lookup (Mỹ An, Ngũ Hành Sơn)
    print("\n--- TEST 3: Ward Lookup (Mỹ An) ---")
    status_w, body_w, ms_w = http_get("/api/v1/amenities/lookup?district=Ngu+Hanh+Son&ward=My+An")
    print(f"Status: {status_w}, Area: {body_w.get('areaName')}, Score: {body_w.get('livingScore')}, Conf: {body_w.get('confidence')} ({ms_w:.1f}ms)")

    # Check evidence structure & attribution
    evidence = body_w.get("poiEvidence", [])
    bases = set(ev.get("attributionBasis") for ev in evidence)
    print(f"Evidence items: {len(evidence)}, Attribution Bases present: {bases}")

    t3_pass = (
        status_w == 200 and
        body_w.get("areaId") == "ward-my-an-ngu-hanh-son" and
        body_w.get("livingScore") == 66.7 and
        body_w.get("parentDistrict") == "Ngũ Hành Sơn" and
        body_w.get("sampleListingCount") == 4700 and
        body_w.get("categoryScores", {}).get("essentials") is not None and
        len(evidence) > 0 and
        "DIRECT_WARD_EVIDENCE" in bases and
        len(body_w.get("dataLimitations", [])) > 0
    )
    test_results["tests"]["test3_ward_lookup"] = {
        "pass": t3_pass,
        "areaId": body_w.get("areaId"),
        "livingScore": body_w.get("livingScore"),
        "sampleListingCount": body_w.get("sampleListingCount"),
        "evidenceCount": len(evidence),
        "attributionBases": list(bases),
        "dataLimitations": body_w.get("dataLimitations"),
        "latency_ms": round(ms_w, 2)
    }
    assert t3_pass, f"Test 3 failed: {body_w}"

    # TEST 4: District Lookup (Hải Châu)
    print("\n--- TEST 4: District Lookup (Hải Châu) ---")
    status_d, body_d, ms_d = http_get("/api/v1/amenities/lookup?district=Hai+Chau")
    print(f"Status: {status_d}, Area: {body_d.get('areaName')}, Score: {body_d.get('livingScore')} ({ms_d:.1f}ms)")
    t4_pass = (
        status_d == 200 and
        body_d.get("areaId") == "district-hai-chau" and
        body_d.get("livingScore") == 100.0 and
        body_d.get("areaLevel") == "DISTRICT" and
        body_d.get("confidence") == 0.95 and
        body_d.get("sampleListingCount") == 6056
    )
    test_results["tests"]["test4_district_lookup"] = {
        "pass": t4_pass,
        "areaId": body_d.get("areaId"),
        "livingScore": body_d.get("livingScore"),
        "confidence": body_d.get("confidence"),
        "sampleListingCount": body_d.get("sampleListingCount"),
        "latency_ms": round(ms_d, 2)
    }
    assert t4_pass, f"Test 4 failed: {body_d}"

    # TEST 5: Corridor Lookup & Prefix Handling
    print("\n--- TEST 5: Corridor Lookup & Vietnamese Prefix Handling ---")
    # Exact corridor
    status_c, body_c, ms_c = http_get("/api/v1/amenities/lookup?street=Vo+Nguyen+Giap")
    # Prefix "Quận Hải Châu"
    status_pfx, body_pfx, _ = http_get("/api/v1/amenities/lookup?district=Quan+Hai+Chau")
    # Ward without district
    status_wnod, body_wnod, _ = http_get("/api/v1/amenities/lookup?ward=My+An")

    print(f"Corridor: {body_c.get('areaName')}, Score: {body_c.get('livingScore')} ({ms_c:.1f}ms)")
    print(f"Prefix 'Quan Hai Chau': {body_pfx.get('areaId')}")
    print(f"Ward only 'My An': {body_wnod.get('areaId')}")

    t5_pass = (
        status_c == 200 and body_c.get("areaLevel") == "CORRIDOR" and "vo-nguyen-giap" in body_c.get("areaId", "") and
        status_pfx == 200 and body_pfx.get("areaId") == "district-hai-chau" and
        status_wnod == 200 and body_wnod.get("areaId") == "ward-my-an-ngu-hanh-son"
    )
    test_results["tests"]["test5_corridor_and_prefixes"] = {
        "pass": t5_pass,
        "corridor_areaId": body_c.get("areaId"),
        "prefix_match_areaId": body_pfx.get("areaId"),
        "ward_only_areaId": body_wnod.get("areaId")
    }
    assert t5_pass, "Test 5 failed"

    # TEST 6: Direct ID Lookup
    print("\n--- TEST 6: Direct ID Lookup ---")
    s_d, b_d, _ = http_get("/api/v1/amenities/district-hai-chau")
    s_w, b_w, _ = http_get("/api/v1/amenities/ward-my-an-ngu-hanh-son")
    s_c, b_c, _ = http_get("/api/v1/amenities/corridor-duong-vo-nguyen-giap-ngu-hanh-son")

    t6_pass = (
        s_d == 200 and b_d.get("areaId") == "district-hai-chau" and
        s_w == 200 and b_w.get("areaId") == "ward-my-an-ngu-hanh-son" and
        s_c == 200 and b_c.get("areaId") == "corridor-duong-vo-nguyen-giap-ngu-hanh-son"
    )
    test_results["tests"]["test6_direct_id"] = {
        "pass": t6_pass,
        "district_status": s_d,
        "ward_status": s_w,
        "corridor_status": s_c
    }
    assert t6_pass, "Test 6 failed"

    # TEST 7: Graceful 404 for Missing / Unknown Areas
    print("\n--- TEST 7: Graceful 404 for Missing Areas ---")
    s_inv_lookup, _, _ = http_get("/api/v1/amenities/lookup?district=Atlantis&ward=UnknownWard")
    s_inv_id, _, _ = http_get("/api/v1/amenities/nonexistent-id-xyz")

    print(f"Invalid lookup status: {s_inv_lookup}, Invalid ID status: {s_inv_id}")
    t7_pass = (s_inv_lookup == 404 and s_inv_id == 404)
    test_results["tests"]["test7_missing_area_404"] = {
        "pass": t7_pass,
        "invalid_lookup_status": s_inv_lookup,
        "invalid_id_status": s_inv_id
    }
    assert t7_pass, "Test 7 failed"

    # TEST 8: Security Boundary (Zero Leak of Research API)
    print("\n--- TEST 8: Security Boundary Audit ---")
    # Anonymous POST to /api/v1/recommendations/research
    code_res_post, body_res_post = http_post_anonymous("/api/v1/recommendations/research")
    # Anonymous GET to /api/v1/recommendations/research/config
    code_res_get, body_res_get, _ = http_get("/api/v1/recommendations/research/config")
    # Anonymous GET to /api/v1/amenities/summary
    code_amen_get, _, _ = http_get("/api/v1/amenities/summary")

    print(f"Anonymous Research POST: {code_res_post} (Expected 401)")
    print(f"Anonymous Research GET config: {code_res_get} (Expected 401)")
    print(f"Anonymous Amenities GET: {code_amen_get} (Expected 200)")

    t8_pass = (
        code_res_post == 401 and
        code_res_get == 401 and
        code_amen_get == 200
    )
    test_results["tests"]["test8_security_boundary"] = {
        "pass": t8_pass,
        "research_post_status": code_res_post,
        "research_get_config_status": code_res_get,
        "amenities_summary_status": code_amen_get,
        "research_api_protected": True
    }
    assert t8_pass, "Test 8 failed: Research API leaked or Amenities API incorrectly blocked"

    # TEST 9: Latency Benchmark (50 sequential requests)
    print("\n--- TEST 9: Performance & Latency Benchmark ---")
    latencies = []
    for _ in range(50):
        s, _, ms = http_get("/api/v1/amenities/lookup?district=Ngu+Hanh+Son&ward=My+An")
        if s == 200:
            latencies.append(ms)

    latencies.sort()
    avg_ms = sum(latencies) / len(latencies)
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    min_ms = latencies[0]
    max_ms = latencies[-1]

    print(f"50 requests: Avg={avg_ms:.2f}ms, P50={p50:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms, Min={min_ms:.2f}ms, Max={max_ms:.2f}ms")
    t9_pass = (avg_ms < 25.0 and p95 < 35.0)
    test_results["performance"] = {
        "requests": len(latencies),
        "avg_ms": round(avg_ms, 2),
        "min_ms": round(min_ms, 2),
        "max_ms": round(max_ms, 2),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "pass": t9_pass
    }
    assert t9_pass, f"Test 9 performance failed: Avg={avg_ms}ms"

    # TEST 10: Data Sparsity & Spatial Integrity Audit
    print("\n--- TEST 10: Data Sparsity & Spatial Integrity Audit ---")
    # Verify no fake coordinates in any profile
    fake_gps_found = False
    fake_distances_found = False
    for a in all_areas:
        status_item, p_item, _ = http_get(f"/api/v1/amenities/{a['areaId']}")
        if status_item == 200:
            for ev in p_item.get("poiEvidence", []):
                if "lat" in ev or "lng" in ev or "distance_meters" in ev:
                    # If distance claimed without GPS, flag it
                    fake_distances_found = True
            if "exactPropertyDistance" in p_item or "centroidDistance" in p_item:
                fake_distances_found = True

    t10_pass = (not fake_gps_found and not fake_distances_found)
    test_results["tests"]["test10_spatial_integrity"] = {
        "pass": t10_pass,
        "fake_gps_found": fake_gps_found,
        "fake_distances_found": fake_distances_found,
        "message": "Zero fake GPS or synthetic distances. Evidence strictly based on area-level aggregation."
    }
    assert t10_pass, "Test 10 failed: Synthetic coordinates/distances detected"

    test_results["overall"] = "PASS"
    print("\n==========================================")
    print("ALL 10 TEST SUITES PASSED EMPIRICALLY!")
    print("==========================================")

finally:
    print("\n[*] Stopping background Spring Boot process...", flush=True)
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    try:
        boot_log_file.close()
    except Exception:
        pass
    print("[*] Spring Boot stopped cleanly.", flush=True)

# Save results JSON
with open(OUT_DIR / "api_test_results.json", "w", encoding="utf-8") as f:
    json.dump(test_results, f, indent=2, ensure_ascii=False)
print(f"[+] Saved test report to {OUT_DIR / 'api_test_results.json'}")
