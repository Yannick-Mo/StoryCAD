import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.storage import get_latest_skeleton


def _to_markdown(skeleton: dict) -> str:
    lines = []
    doc = skeleton.get("creative_doc", {})
    wr = skeleton.get("world_rules", {})
    chars = skeleton.get("characters", [])
    graph = skeleton.get("graph", {})
    branches = skeleton.get("branches", [])
    foreshadows = skeleton.get("foreshadows", [])

    lines.append("# Narrative Skeleton\n")

    lines.append("## Core Conflict\n")
    lines.append(f"{doc.get('core_conflict', 'N/A')}\n")

    lines.append("## World Rules\n")
    for rule in wr.get("rules", []):
        lines.append(f"- **{rule.get('category')}**: {rule.get('description')}")
        lines.append(f"  - Limitation: {rule.get('limitation')}\n")

    lines.append("## Characters\n")
    for c in chars:
        lines.append(f"### {c.get('name')}\n")
        dt = c.get("desire_topology", {})
        lines.append(f"- Surface Desire: {dt.get('表层欲望', 'N/A')}")
        lines.append(f"- Deep Need: {dt.get('深层需求', 'N/A')}")
        lines.append(f"- Core Fear: {dt.get('核心恐惧', 'N/A')}")
        lines.append(f"- Bottom Line: {c.get('bottom_line', 'N/A')}")
        lines.append(f"- Growth Arc: {c.get('growth_arc', 'N/A')}\n")

    lines.append("## Plot Graph\n")
    for n in graph.get("nodes", []):
        lines.append(f"- [{n.get('id')}] {n.get('description')} (emotion: {n.get('emotion_value')})")
    lines.append("")
    for e in graph.get("edges", []):
        lines.append(f"  {e.get('source')} -[{e.get('type')}]-> {e.get('target')}")

    lines.append("\n## Branches\n")
    for b in branches:
        lines.append(f"- Divergence: {b.get('divergence_point')} -> Convergence: {b.get('convergence_point', 'None')}")
        for i, path in enumerate(b.get("paths", [])):
            lines.append(f"  - Path {i+1}: {' -> '.join(path)}")

    lines.append("\n## Foreshadows\n")
    for f in foreshadows:
        lines.append(f"- [{f.get('status')}] {f.get('content')}")
        lines.append(f"  Planted: {f.get('planted_at')}, {f.get('planned_recycle_interval')}")

    return "\n".join(lines)


async def export_json(db: AsyncSession, project_id: uuid.UUID) -> str | None:
    sk = await get_latest_skeleton(db, project_id)
    if not sk or not sk.skeleton:
        return None
    return json.dumps(sk.skeleton, ensure_ascii=False, indent=2)


async def export_markdown(db: AsyncSession, project_id: uuid.UUID) -> str | None:
    sk = await get_latest_skeleton(db, project_id)
    if not sk or not sk.skeleton:
        return None
    return _to_markdown(sk.skeleton)
