import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import ProjectSkeleton
from app.services.storage import save_skeleton, get_latest_skeleton


async def add_graph_node(db: AsyncSession, project_id: uuid.UUID, node: dict) -> dict:
    sk = await get_latest_skeleton(db, project_id)
    if not sk:
        raise ValueError("No skeleton found")
    graph = sk.skeleton.get("graph", {})
    nodes = graph.get("nodes", [])
    max_id = max((int(n["id"].split("_")[1]) for n in nodes if n["id"].startswith("evt_")), default=0)
    node["id"] = f"evt_{max_id + 1}"
    nodes.append(node)
    graph["nodes"] = nodes
    sk.skeleton["graph"] = graph
    await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
    return node


async def update_graph_node(db: AsyncSession, project_id: uuid.UUID, node_id: str, updates: dict) -> dict | None:
    sk = await get_latest_skeleton(db, project_id)
    if not sk:
        return None
    for node in sk.skeleton.get("graph", {}).get("nodes", []):
        if node["id"] == node_id:
            node.update(updates)
            await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
            return node
    return None


async def delete_graph_node(db: AsyncSession, project_id: uuid.UUID, node_id: str) -> bool:
    sk = await get_latest_skeleton(db, project_id)
    if not sk:
        return False
    graph = sk.skeleton.get("graph", {})
    graph["nodes"] = [n for n in graph.get("nodes", []) if n["id"] != node_id]
    graph["edges"] = [e for e in graph.get("edges", []) if e["source"] != node_id and e["target"] != node_id]
    sk.skeleton["graph"] = graph
    await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
    return True


async def add_graph_edge(db: AsyncSession, project_id: uuid.UUID, source: str, target: str, edge_type: str) -> dict:
    sk = await get_latest_skeleton(db, project_id)
    if not sk:
        raise ValueError("No skeleton found")
    graph = sk.skeleton.get("graph", {})
    edge = {"source": source, "target": target, "type": edge_type}
    edges = graph.get("edges", [])
    edges.append(edge)
    graph["edges"] = edges
    sk.skeleton["graph"] = graph
    await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
    return edge


async def delete_graph_edge(db: AsyncSession, project_id: uuid.UUID, source: str, target: str) -> bool:
    sk = await get_latest_skeleton(db, project_id)
    if not sk:
        return False
    graph = sk.skeleton.get("graph", {})
    original_len = len(graph.get("edges", []))
    graph["edges"] = [e for e in graph.get("edges", []) if not (e["source"] == source and e["target"] == target)]
    if len(graph["edges"]) < original_len:
        sk.skeleton["graph"] = graph
        await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
        return True
    return False


async def add_character(db: AsyncSession, project_id: uuid.UUID, character: dict) -> dict:
    sk = await get_latest_skeleton(db, project_id)
    if not sk:
        raise ValueError("No skeleton found")
    chars = sk.skeleton.get("characters", [])
    if any(c["name"] == character["name"] for c in chars):
        raise ValueError(f"Character '{character['name']}' already exists")
    chars.append(character)
    sk.skeleton["characters"] = chars
    await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
    return character


async def update_character(db: AsyncSession, project_id: uuid.UUID, name: str, updates: dict) -> dict | None:
    sk = await get_latest_skeleton(db, project_id)
    if not sk:
        return None
    chars = sk.skeleton.get("characters", [])
    for char in chars:
        if char["name"] == name:
            char.update(updates)
            await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
            return char
    return None


async def delete_character(db: AsyncSession, project_id: uuid.UUID, name: str) -> bool:
    sk = await get_latest_skeleton(db, project_id)
    if not sk:
        return False
    original_len = len(sk.skeleton.get("characters", []))
    sk.skeleton["characters"] = [c for c in sk.skeleton.get("characters", []) if c["name"] != name]
    if len(sk.skeleton["characters"]) < original_len:
        await save_skeleton(db, project_id, sk.skeleton, sk.validation_report)
        return True
    return False
