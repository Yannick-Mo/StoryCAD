import json
from app.agent.privacy import sanitise_event

errors = []

def check(desc, actual, expected):
    if actual != expected:
        errors.append(f"FAIL {desc}: expected={expected!r}, got={actual!r}")
    else:
        print(f"  OK {desc}")

# ── tool_done ──
td = sanitise_event("tool_done", json.dumps({"tool": "list_chapters", "success": True, "data": "x", "error": None, "_tool_use_id": "abc"}))
d = json.loads(td)
check("list_chapters tool name", d["tool"], "列出章节")
check("no _tool_use_id", "_tool_use_id" in d, False)

td2 = sanitise_event("tool_done", json.dumps({"tool": "search_nodes", "success": True, "data": "x"}))
d2 = json.loads(td2)
check("search_nodes tool name", d2["tool"], "搜索节点")

# ── plan ──
plan = sanitise_event("plan", json.dumps({
    "steps": [{"tool": "list_scenes", "params": {"project_id": "x"}, "description": "列出场景", "tool_use_id": "t1"}],
    "reasoning": "需要列出场景",
    "status": "awaiting_confirmation",
}))
p = json.loads(plan)
check("plan list_scenes", p["steps"][0]["tool"], "列出场景")
check("plan no params", "params" in p["steps"][0], False)
check("plan no tool_use_id", "tool_use_id" in p["steps"][0], False)

# ── project_updated ──
pu = sanitise_event("project_updated", json.dumps({
    "tools_executed": ["list_edges"],
    "tool_details": [{"name": "list_edges", "changes": {"data": "x"}}],
    "all_success": True,
}))
u = json.loads(pu)
check("list_edges display", u["tools_executed"][0], "列出关联")

# ── error sanitization ──
e = sanitise_event("error", "Tool 'search_nodes' failed: DB error")
check("error sanitized", e, "操作 failed: DB error")

# ── unknown tool ──
unk = sanitise_event("tool_done", json.dumps({"tool": "some_future_tool", "success": True, "data": "x"}))
du = json.loads(unk)
check("unknown tool name", du["tool"], "执行操作")

if errors:
    print(f"\n❌ {len(errors)} FAILURES:")
    for e in errors:
        print(f"  {e}")
else:
    print("\n✅ ALL PASSED")
