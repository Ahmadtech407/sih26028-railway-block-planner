"""
Standalone test: Verify the OR-Tools optimizer produces a correct
conflict-free window for the SIH demo scenario.

No API key or Antigravity SDK needed — just tests the pure math.
"""

import sys
import json

sys.path.insert(0, ".")

from tools.section_status import query_section_status
from tools.conflict_checker import check_track_conflicts
from tools.optimizer import run_or_tools_block_optimizer
from tools.commit import commit_block_schedule

print("=" * 60)
print("  STANDALONE TOOL VERIFICATION")
print("=" * 60)

# ── Step 1: Section Status ──
print("\n[1] query_section_status('KNP-PRYJ-SEC-B')")
result = query_section_status("KNP-PRYJ-SEC-B")
print(result)

# ── Step 2: Conflict Check (raw window 600-900) ──
print("\n[2] check_track_conflicts('KNP-PRYJ-SEC-B', 600, 900)")
result = check_track_conflicts("KNP-PRYJ-SEC-B", 600, 900)
print(result)

# ── Step 3: OR-Tools Optimizer ──
print("\n[3] run_or_tools_block_optimizer()")

maintenance = json.dumps([{
    "block_id": "MNT-KNP-04",
    "section_id": "KNP-PRYJ-SEC-B",
    "duration_minutes": 120,
    "earliest_start": 600,
    "latest_end": 900,
}])

result = run_or_tools_block_optimizer(maintenance)
parsed = json.loads(result)
print(json.dumps(parsed, indent=2))

# Validate the result
block = parsed.get("MNT-KNP-04", {})
if block.get("status") == "OPTIMAL_SCHEDULED":
    start = block["allocated_start_min"]
    end = block["allocated_end_min"]
    print(f"\n  [PASS] OPTIMAL window found: {block['formatted_window']}")
    print(f"     Start={start}min  End={end}min  Duration={end - start}min")

    # Verify no overlap with premium trains (VB: 630-660, Raj: 720-750)
    assert end + 5 <= 630 or start >= 665, "FAIL: Overlaps Vande Bharat!"
    assert end + 5 <= 720 or start >= 755, "FAIL: Overlaps Rajdhani!"
    print("     [PASS] No overlap with Vande Bharat (630-660)")
    print("     [PASS] No overlap with Rajdhani Express (720-750)")
else:
    print(f"\n  [FAIL] Optimizer returned: {block.get('status')}")
    sys.exit(1)

# ── Step 4: Commit ──
print(f"\n[4] commit_block_schedule('{block['formatted_window']}')")
result = commit_block_schedule(
    "MNT-KNP-04", "KNP-PRYJ-SEC-B",
    block["formatted_window"].split(" - ")[0],
    block["formatted_window"].split(" - ")[1],
)
print(result)

print("\n" + "=" * 60)
print("  ALL TESTS PASSED [OK]")
print("=" * 60)
