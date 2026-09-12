"""
End-to-End Frontend-to-Backend Integration Verification Test.
Simulates the exact Streamlit user journey:
1. Health Check (GET /)
2. Section Retrieval (GET /api/sections & GET /api/sections/{id})
3. Train Telemetry & Kinematic Prediction (GET /api/trains & POST /api/trains/predict)
4. Preliminary Conflict Scan (POST /api/conflicts/check)
5. OR-Tools Optimization (POST /api/optimizer/solve)
6. Block Approval & TMS Commit (POST /api/blocks/commit)
7. Committed Block Verification (GET /api/blocks)
"""

import sys
import json
import urllib.request
import urllib.error

BACKEND_URL = "http://localhost:8000"


def http_get(path: str) -> dict:
    url = f"{BACKEND_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "SIH26028-TestRunner"})
    with urllib.request.urlopen(req, timeout=5.0) as res:
        return json.loads(res.read().decode("utf-8"))


def http_post(path: str, payload: dict) -> dict:
    url = f"{BACKEND_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "SIH26028-TestRunner"})
    with urllib.request.urlopen(req, timeout=8.0) as res:
        return json.loads(res.read().decode("utf-8"))


def run_e2e_test():
    print("=" * 70)
    print(" [IR-SIH] END-TO-END FLOW VERIFICATION TEST (FRONTEND -> BACKEND)")
    print("=" * 70)

    # ── STEP 1: Health Check ──
    print("\n[STEP 1] Verifying Backend Health Check (GET /)...")
    health = http_get("/")
    print(f"  Status: {health.get('status')} | Version: {health.get('version')}")
    assert health.get("status") == "ONLINE", "Backend is not online!"
    print("  --> [PASS] Backend is ONLINE & Healthy.")

    # ── STEP 2: Section Retrieval ──
    print("\n[STEP 2] Fetching Active Track Sections (GET /api/sections)...")
    sections = http_get("/api/sections")
    print(f"  Found {len(sections)} sections:")
    for s in sections:
        print(f"   * {s['section_id']}: {s['section_name']} ({s['length_km']} km, {s['speed_limit_kmph']} km/h)")
    assert len(sections) > 0, "No sections found!"
    target_section = sections[0]["section_id"]
    print(f"  --> [PASS] Selected section: {target_section}")

    # ── STEP 3: Trains & Telemetry Extrapolation ──
    print(f"\n[STEP 3] Fetching Scheduled Trains on {target_section} (GET /api/trains)...")
    trains = http_get(f"/api/trains?section_id={target_section}")
    print(f"  Found {len(trains)} active trains:")
    for t in trains:
        print(f"   * Train {t['train_number']} {t['name']} (Tier {t['priority']}) | Window: {t['entry_time']} - {t['exit_time']} | Speed: {t['speed_kmph']} km/h")
    assert len(trains) >= 4, "Expected at least 4 trains!"

    print("\n  Testing Dead-Reckoning Prediction (POST /api/trains/predict for Vande Bharat with 120s GPS lag)...")
    pred = http_post("/api/trains/predict", {"train_number": "22436", "seconds_since_update": 120})
    print(f"   * Position: {pred['original_position_km']} km -> Predicted: {pred['predicted_position_km']} km | Confidence: {pred['confidence_pct']}% | Source: {pred['source']}")
    assert pred["source"] == "PREDICTED", "Prediction source incorrect!"
    print("  --> [PASS] Telemetry & Kinematics verified.")

    # ── STEP 4: Conflict Check ──
    print(f"\n[STEP 4] Scanning Preliminary Conflicts for 10:00-15:00 (POST /api/conflicts/check)...")
    conflicts = http_post("/api/conflicts/check", {
        "section_id": target_section,
        "proposed_start_min": 600,
        "proposed_end_min": 900
    })
    print(f"  Status: {conflicts['status']} | Conflicts Found: {conflicts['conflict_count']}")
    for c in conflicts['conflicting_trains']:
        print(f"   - {c['train']} (Priority {c['priority']}) overlaps by {c['overlap_minutes']} mins (Slot: {c['train_window']})")
    assert conflicts["has_conflict"] is True, "Expected conflicts in raw 10:00-15:00 window!"
    print("  --> [PASS] Conflict detection operational.")

    # ── STEP 5: OR-Tools Optimization ──
    print(f"\n[STEP 5] Executing OR-Tools CP-SAT Optimization (POST /api/optimizer/solve)...")
    opt_payload = {
        "block_id": "MNT-KNP-04",
        "section_id": target_section,
        "duration_minutes": 120,
        "earliest_start_min": 600,
        "latest_end_min": 900,
        "work_type": "Rail Replacement"
    }
    opt_res = http_post("/api/optimizer/solve", opt_payload)
    print(f"  Status: {opt_res['status']}")
    print(f"  Allocated Window:  {opt_res['formatted_window']} ({opt_res['duration_minutes']} mins)")
    print(f"  Safety Buffer:     {opt_res['safety_buffer_minutes']} minutes (strictly enforced)")
    print(f"  Total Delay:       {opt_res['total_delay_min']} minutes")
    print(f"  Weighted Cost:     {opt_res['weighted_cost']}")
    print(f"  Risk Level:        {opt_res['risk_level']}")
    print(f"  Confidence:        {opt_res['recommendation_confidence_pct']}%")
    print(f"  Top Alternatives:  {len(opt_res['alternatives'])} feasible candidate slots ranked")

    print("\n  Secondary Train Regulations:")
    for aff in opt_res['affected_trains']:
        print(f"   * {aff['name']} ({aff['train_number']}): {aff['delay_minutes']} min delay -> {aff['action']}")

    assert opt_res["status"] == "OPTIMAL_SCHEDULED", "Optimizer failed to find feasible schedule!"
    assert opt_res["allocated_start_min"] == 755, f"Expected 755 (12:35 PM), got {opt_res['allocated_start_min']}"
    assert opt_res["allocated_end_min"] == 875, f"Expected 875 (14:35 PM), got {opt_res['allocated_end_min']}"
    print("  --> [PASS] Optimization returned optimal mathematical window 12:35 - 14:35.")

    # ── STEP 6: Block Approval & TMS Commit ──
    print(f"\n[STEP 6] Operator Approving & Committing Block {opt_payload['block_id']} (POST /api/blocks/commit)...")
    commit_payload = {
        "block_id": opt_payload["block_id"],
        "section_id": target_section,
        "start_min": opt_res["allocated_start_min"],
        "end_min": opt_res["allocated_end_min"],
        "work_type": opt_payload["work_type"]
    }
    commit_res = http_post("/api/blocks/commit", commit_payload)
    print(f"  Transaction ID: {commit_res['transaction_id']}")
    print(f"  Committed Period: {commit_res['start_time']} to {commit_res['end_time']}")
    print(f"  Caution Board Notice:\n   \"{commit_res['caution_board_notice']}\"")
    assert commit_res["status"] == "SUCCESS", "Commit failed!"
    print("  --> [PASS] Block successfully committed to Central Railway TMS.")

    # ── STEP 7: Committed Block Verification ──
    print(f"\n[STEP 7] Refreshing and Verifying TMS Committed Feed (GET /api/blocks)...")
    blocks_feed = http_get("/api/blocks")
    print(f"  Committed blocks in Central TMS ({len(blocks_feed)} total):")
    found_committed = False
    for b in blocks_feed:
        print(f"   * TXN: {b['transaction_id']} | Block: {b['block_id']} on {b['section_id']} | Period: {b['start_time']}-{b['end_time']}")
        if b["block_id"] == "MNT-KNP-04":
            found_committed = True
    assert found_committed, "Committed block not found in /api/blocks feed!"
    print("  --> [PASS] TMS committed record verified.")

    print("\n" + "=" * 70)
    print(" [OK] COMPLETE FRONTEND-TO-BACKEND INTEGRATION TEST PASSED 100%!")
    print("=" * 70)


if __name__ == "__main__":
    run_e2e_test()
