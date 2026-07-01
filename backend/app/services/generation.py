import logging
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.graph.story_graph import build_story_graph
from app.services.storage import update_project_status, save_skeleton

logger = logging.getLogger(__name__)


async def run_generation(project_id, raw_input: dict, session_factory: async_sessionmaker):
    try:
        async with session_factory() as db:
            graph = build_story_graph()
            initial_state = {
                "raw_input": raw_input,
                "creative_doc": {},
                "world_rules": {},
                "characters": [],
                "graph_data": {},
                "branches": [],
                "foreshadows": [],
                "validation_report": [],
                "iteration": 0
            }
            final_state = await graph.ainvoke(initial_state)

            skeleton = {
                "creative_doc": final_state.get("creative_doc"),
                "world_rules": final_state.get("world_rules"),
                "characters": final_state.get("characters"),
                "graph": final_state.get("graph_data"),
                "branches": final_state.get("branches"),
                "foreshadows": final_state.get("foreshadows")
            }
            validation_report = final_state.get("validation_report", [])

            await save_skeleton(db, project_id, skeleton, validation_report)
            await update_project_status(db, project_id, "completed")

            logger.info(
                f"Project {project_id} generated successfully. "
                f"Iterations: {final_state.get('iteration', 0)}. "
                f"Issues: {len(validation_report)}"
            )
    except Exception as e:
        logger.error(f"Generation failed for {project_id}: {str(e)}", exc_info=True)
        try:
            async with session_factory() as db:
                await update_project_status(db, project_id, "failed")
        except Exception:
            pass
