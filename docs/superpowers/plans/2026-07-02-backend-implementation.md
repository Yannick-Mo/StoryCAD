# StoryCAD Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax.

**Goal:** Complete rewrite of StoryCAD backend matching the design spec (9 Agent system + Neo4j knowledge graph + full CAD workflow)

**Architecture:** DDD bounded contexts with FastAPI + PostgreSQL + Neo4j + LangGraph. Orchestrator state machine driving 7 specialized agents.

**Tech Stack:** FastAPI, SQLAlchemy async, asyncpg, Neo4j 5, Redis, LangGraph, LangChain, DeepSeek/GPT-4o, Docker Compose

---

## Phase 0: Project Setup

### Task P0-1: Initialize project structure

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/config.py`, `backend/app/database.py`
- Create: `backend/app/shared/__init__.py`, `backend/app/shared/models.py`, `backend/app/shared/errors.py`
- Create: `backend/requirements.txt`, `backend/Dockerfile`
- Modify: `backend/docker-compose.yml`

Step 1: Write requirements.txt (fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, neo4j, redis, langgraph, langchain, langchain-openai, pydantic, pydantic-settings, pytest, pytest-asyncio, httpx)

Step 2: Write config.py with Settings class (database_url, neo4j_uri, neo4j_user/password, redis_url, deepseek_api_key, deepseek_base_url, model_name, llm_provider, openai_api_key, openai_base_url). Use pydantic-settings BaseSettings with env_file=".env".

Step 3: Write database.py with async engine, async_sessionmaker, get_db dependency, init_db function.

Step 4: Write main.py with FastAPI app, lifespan context manager calling init_db, /health endpoint, register_routers function.

Step 5: Write shared/models.py (ProjectRef, TimestampMixin). Write shared/errors.py (AppError, NotFoundError, ConflictError).

Step 6: Update docker-compose.yml to add Neo4j 5 service (ports 7687:7687, 7474:7474, env NEO4J_AUTH: neo4j/password, volume neo4j_data).

Step 7: Verify: `docker compose up -d db redis neo4j` then `docker compose run --rm backend python -c "from app.main import app; print('OK')"`

Step 8: Commit: `git add backend/ docker-compose.yml && git commit -m "feat: project scaffolding with PostgreSQL, Neo4j, Redis"`

---

## Phase 1: Knowledge Graph + Project Context

### Task 1-1: Neo4j connection and repository

**Files:** `backend/app/knowledge_graph/{__init__,models,repository,service}.py`, `tests/test_knowledge_graph/{__init__,test_repository}.py`

Step 1: Write models.py - EntityType enum (CHARACTER, EVENT, CHAPTER, ACT, FORESHADOW, THEME, SETTING), RelationType enum (ACTED_IN, CAUSES, HAS_FORESHAW, RESOLVED_AT, RELATES_TO, BELONGS_TO, PART_OF, THEMATIZES, SET_IN), GraphEntity, GraphRelation pydantic models.

Step 2: Write repository.py - Neo4jRepository class with async connect/close/session, create_entity, get_entity, update_entity, delete_entity, create_relation, get_entity_relations, query_path (shortestPath), delete_project_graph. Uses AsyncGraphDatabase from neo4j.

Step 3: Write service.py - KnowledgeGraphService wrapping neo4j_repo with create_character, create_event, create_causal_edge, create_relationship, delete_project_data.

Step 4: Write tests - test_create_and_get_entity, test_create_relation.

Step 5: Run tests: `docker compose run --rm backend python -m pytest tests/test_knowledge_graph/ -v` (expect 2 passed)

Step 6: Commit

### Task 1-2: Project context (PostgreSQL ORM + Repository + Service)

**Files:** `backend/app/project/{__init__,models,repository,service}.py`, `tests/test_project/{__init__,test_repository}.py`

Step 1: Write models.py with SQLAlchemy async: Project (id UUID PK, title, description, genre, status, workflow_stage, created_at, updated_at), ProjectVersion (id UUID PK, project_id, version int, snapshot JSONB, created_at), ProjectConfig (id, project_id, total_words, template_type, target_audience, timestamps). Use DeclarativeBase.

Step 2: Write repository.py - ProjectRepository with create/get/list(pagination)/update/delete/save_version (auto-increment version)/get_versions/get_config/upsert_config.

Step 3: Write service.py - ProjectService wrapping repository, returning dicts. On delete also call neo4j_repo.delete_project_graph.

Step 4: Write tests - test_create_project, test_get_project.

Step 5: Run tests: `docker compose run --rm backend python -m pytest tests/test_project/ -v`

Step 6: Commit

### Task 1-3: Project API routes

**Files:** `backend/app/api/{__init__,deps,routes_project}.py`

Step 1: Write api/deps.py - get_db async generator using async_session.

Step 2: Write routes_project.py - CRUD endpoints: POST /api/projects, GET /api/projects?page=&size=, GET /api/projects/{id}, PATCH /api/projects/{id}, DELETE /api/projects/{id}, GET /api/projects/{id}/versions, GET /api/projects/{id}/versions/{version}. All with 404 handling.

Step 3: Register router in main.py.

Step 4: Test: `curl -s http://localhost:8000/health` then `curl -s -X POST "http://localhost:8000/api/projects?title=My+Story"`

Step 5: Commit

---

## Phase 2: Analysis Context

### Task 2-1: Base agent framework

**Files:** `backend/app/agents/{__init__,base}.py`

Step 1: Write agents/base.py - get_llm(temperature) using ChatOpenAI with response_format json_object, supporting both deepseek and openai providers via settings. run_agent(prompt_messages, inputs, temperature, schema) with 2 retry attempts, JSON parsing and optional Pydantic schema validation.

### Task 2-2: Analysis models + agent + service + API

**Files:** `backend/app/analysis/{__init__,models,agent,service,repository}.py`, `backend/app/api/routes_analysis.py`, `tests/test_analysis/{__init__,test_agent.py}`

Step 1: Write analysis/models.py - SixDimMetadata (core_high_concept, protagonist_identity, core_conflict, non_negotiable_events, tone_and_length, world_genre, main_characters, core_relationships, landmark_scenes, subplot_hints, style_details), MissingDiagnosis (field, severity: fatal/serious/suggestion, description, suggestion), AnalysisResult.

Step 2: Write analysis/agent.py - ANALYSIS_AGENT_PROMPT with 6-dimension extraction methodology. run_analysis(raw_input) -> AnalysisResult calling run_agent.

Step 3: Write analysis/repository.py - save_analysis/get_latest_analysis using ProjectVersion table with "analysis" key in snapshot.

Step 4: Write analysis/service.py - AnalysisService.analyze calls agent then saves via repo.

Step 5: Write routes_analysis.py - POST /api/projects/{id}/analysis (submit raw input), GET /api/projects/{id}/analysis (get result).

Step 6: Write test - test_analysis_agent with sample input.

Step 7: Register router in main.py. Commit.

---

## Phase 3: Character + World Contexts

### Task 3-1: Character context

**Files:** `backend/app/character/{__init__,models,agent,repository,service}.py`, `backend/app/api/routes_character.py`

Step 1: Write character/models.py - DesireTopology, CharacterProfile (name, role, desire_topology, bottom_line, vulnerability, language_genes, growth_arc, backstory), Relationship (from_name, to_name, trust/threat/attraction 0-100), CharacterDesignResult (logline, core_theme, characters, relationships, pending_choices).

Step 2: Write character/agent.py - SOUL_ARCHITECT_PROMPT. design_characters(metadata) -> CharacterDesignResult. Agent fills gaps, generates logline, designs characters with desire topology.

Step 3: Write character/repository.py - save_character_to_graph (creates :Character node in Neo4j), save_relationship (creates [:RELATES_TO] edge), get_characters, delete_character.

Step 4: Write character/service.py - generate_characters(fetches analysis metadata -> calls design_characters -> saves to Neo4j -> saves version). Also get_characters, update_character, delete_character.

Step 5: Write routes_character.py - GET /api/projects/{id}/characters, POST /api/projects/{id}/characters/generate, PUT /api/projects/{id}/characters/{name}, DELETE /api/projects/{id}/characters/{name}.

Step 6: Register router. Commit.

### Task 3-2: World context

**Files:** `backend/app/world/{__init__,models,agent,service}.py`, `backend/app/api/routes_world.py`

Step 1: Write world/models.py - WorldRule (category, description, limitation, conflict_potential), WorldRules (rules list, history, forbidden_events).

Step 2: Write world/agent.py - WORLD_BUILDER_PROMPT. build_world(metadata) -> WorldRules. Generates 4-7 rules with clear limitations.

Step 3: Write world/service.py - generate_world (fetches metadata -> calls agent -> saves to Neo4j as :Setting -> saves version), get_world (query Neo4j).

Step 4: Write routes_world.py - GET /api/projects/{id}/world, POST /api/projects/{id}/world/generate.

Step 5: Register router. Commit.

---

## Phase 4: Story Context (Structure + Plot)

### Task 4-1: Story models + agents + service + API

**Files:** `backend/app/story/{__init__,models,agent_structure,agent_plot,service}.py`, `backend/app/api/routes_story.py`

Step 1: Write story/models.py - Act (number, name, word_count, end_chapter, key_event, percentage), ActStructure (total_words, acts, turning_points), Chapter (number, title, core_event, hook_to_next, emotion_value, word_count, act), ChapterPlan (chapters, suspense_chain).

Step 2: Write agent_structure.py - STRUCTURE_DESIGNER_PROMPT for 4-act structure. design_structure(metadata, total_words) -> ActStructure.

Step 3: Write agent_plot.py - PLOT_PLANNER_PROMPT for chapter-by-chapter breakdown. plan_chapters(act_structure, characters, world) -> ChapterPlan.

Step 4: Write story/service.py - generate_structure (calls agent, saves Acts to Neo4j, saves version), generate_chapters (fetches metadata/characters, calls structure + plot agents, saves Chapters to Neo4j), get_structure, get_chapters, update_chapter.

Step 5: Write routes_story.py - GET /api/projects/{id}/structure, POST /api/projects/{id}/structure/generate, GET /api/projects/{id}/chapters, POST /api/projects/{id}/chapters/generate, PUT /api/projects/{id}/chapters/{chapter_number}.

Step 6: Register router. Commit.

---

## Phase 5: Validation + Knowledge Graph API + Orchestrator

### Task 5-1: Validation context

**Files:** `backend/app/validation/{__init__,models,agent,service}.py`, `backend/app/api/routes_validation.py`

Step 1: Write validation/models.py - Issue (severity: high/medium/low, category, description, location, suggestion), ValidationReport (round, logic_issues, character_issues, pacing_issues, affected_entities).

Step 2: Write validation/agent.py - VALIDATOR_PROMPT for 3-round validation (logic, character, pacing). run_validation(full_skeleton) -> ValidationReport.

Step 3: Write validation/service.py - validate(collects all data from Neo4j -> calls agent -> saves version), get_report.

Step 4: Write routes_validation.py - POST /api/projects/{id}/validate, GET /api/projects/{id}/validate/report.

### Task 5-2: Knowledge Graph API routes

**File:** `backend/app/api/routes_knowledge_graph.py`

Endpoints: GET /api/projects/{id}/graph/entities, GET /api/projects/{id}/graph/entities/{entity_id}, POST /api/projects/{id}/graph/query (body: {source_id, target_id, max_depth}).

### Task 5-3: Orchestrator state machine

**Files:** `backend/app/orchestrator/{__init__,models,state_machine}.py`, `backend/app/api/routes_orchestrator.py`

Step 1: Write orchestrator/models.py - WorkflowStage enum (INIT, ANALYSIS, CONFIRM_CORE, STRUCTURE, PLOT, VALIDATE, REPAIR, EXPORT, COMPLETED, FAILED), WorkflowState.

Step 2: Write orchestrator/state_machine.py - STAGE_ORDER list, can_transition(current, target), next_stage(current).

Step 3: Write routes_orchestrator.py - GET /api/projects/{id}/workflow, POST /api/projects/{id}/workflow/next, POST /api/projects/{id}/workflow/skip.

---

## Phase 6: Export + Final Integration

### Task 6-1: Export context

**Files:** `backend/app/export/{__init__,service}.py`, `backend/app/api/routes_export.py`

Step 1: Write export/service.py - export_json (merges all version snapshots, returns JSON string), export_markdown (formats as markdown with Characters and Chapters sections).

Step 2: Write routes_export.py - GET /api/projects/{id}/export/json (returns PlainTextResponse with Content-Disposition attachment), GET /api/projects/{id}/export/markdown.

### Task 6-2: Final main.py with all routers registered

Update main.py version to "0.3.0", register all 9 routers (project, analysis, character, world, story, validation, knowledge_graph, export, orchestrator).

### Task 6-3: Full integration test + final commit

Run full integration: docker compose restart, health check, create project, run analysis, generate characters, generate structure, generate chapters, validate, export.
