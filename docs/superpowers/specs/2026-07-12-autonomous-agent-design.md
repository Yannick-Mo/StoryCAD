# Autonomous Agent Architecture — Design Spec

**Date**: 2026-07-12  
**Branch**: `feature/ai-agent-optimization`  
**Status**: Draft → Implementation

---

## 1. Motivation

### Current State

The StoryCAD AI agent uses a **fixed workflow**:

```
User message → classify_intent (LLM tags into 1 of 7 buckets)
  → simple_q      → generate → END
  → tool_call     → execute_tool → generate → END
  → cowriter      → execute_tool (CoWriterMode JSON) → generate → END
  → complex       → plan → (confirm) → execute_tool → generate → END
  → plan_confirm  → execute_tool → generate → END
```

Problems:
1. **One round per user message.** The model cannot decide "I need more data, let me call another tool."
2. **classify_intent is a bottleneck.** An extra LLM call that only labels, doesn't contribute value. The model could directly decide what to do.
3. **Cowriter is a separate code path.** `CoWriterMode` forces JSON output every turn. The model can't mix natural discussion with option cards freely.
4. **Plan is a separate node.** Confirmation should be an interceptor, not a standalone phase.
5. **No token-aware context management.** Raw `MAX_HISTORY_MESSAGES=200` truncation.
6. **Recovery system (`recovery.py`) exists but is not wired into `agent_loop`.**

### Target State

A **model-driven loop** inspired by Claude Code's `queryLoop`:

- The LLM decides: reply, call tools, present options, ask questions
- The loop continues as long as the model wants to (tool calls present)
- Code handles **safety** (mode gating, confirmation, context budget), not **flow control**

```
while model_wants_to_continue:
    LLM streaming (text + tool_use interleaved)
    → StreamingToolExecutor (run tools as they arrive)
    → Interceptor layer (mode gate, confirm gate, option gate)
    → Decide: continue / stop / wait_for_user
```

---

## 2. Architecture

### 2.1 Three Layers

```
Layer 3: Presentation          Layer 2: Autonomous Loop        Layer 1: Infrastructure
┌─────────────────────┐       ┌────────────────────────┐      ┌──────────────────────┐
│ SSE events to front │←──────│ autonomous_loop()       │─────→│ Tool registry (37)    │
│ - token stream      │       │                         │      │ Concurrency modes     │
│ - tool_done cards   │       │ while model_active:     │      │ Token-aware compress  │
│ - option cards      │       │   prepare_context()     │      │ Error recovery (4层)  │
│ - plan confirm UI   │       │   llm_stream+tools()    │      │ Mode gating           │
│ - error display     │       │   execute_tools()       │      │ Skill filtering       │
└─────────────────────┘       │   intercept()           │      │ Attachment injection  │
                              │   decide_next()         │      └──────────────────────┘
                              └────────────────────────┘
```

### 2.2 State Object (aggregator pattern)

Following Claude Code's pattern — single `State` object, atomic updates at continue sites:

```python
@dataclass
class LoopState:
    messages: list[Message]
    mode: str
    project_context: dict
    tool_results: list[dict]
    intermediate_steps: list[dict]
    errors: list[str]
    cowriter_session: dict
    current_options: list[dict]
    pending_plan: dict
    plan_confirmed: bool
    planned_steps: list[dict]
    current_step_index: int
    retry_count: int
    max_retries: int
    recovery_state: dict
    turn_count: int
    active_skills: list
    trace_id: str
```

Each continue site writes the full state atomically:
```python
state = LoopState(
    messages=[...new messages...],
    ...  # all fields explicitly set
    transition="tool_executed",
)
```

### 2.3 Loop Pseudocode

```python
async def autonomous_loop(initial_state, tools, llm_client, db, tool_descriptions):
    state = LoopState.from_initial(initial_state)
    
    while state.turn_count < MAX_TURNS:
        # ── Step 1: Context Management ──
        token_estimate = estimate_tokens(state.messages)
        if token_estimate > MODEL_LIMIT * 0.8:
            state.messages = compress_history(state.messages)
            yield BoundaryMessage("context_compressed")
        
        # ── Step 2: Attachment Injection ──
        attachments = await attachment_injector.collect(state, ...)
        messages_for_llm = state.messages + attachments
        
        # ── Step 3: LLM Call + Stream Processing ──
        streaming_executor = StreamingToolExecutor(filtered_tools, db)
        tool_blocks = []
        
        async for chunk in llm_client.chat_stream_with_tools(
            messages=messages_for_llm,
            tools=filtered_tool_schemas,
            ...
        ):
            if chunk.is_text:
                yield StreamToken(chunk.content)
            
            elif chunk.is_tool_call:
                tool_blocks.append(chunk.tool_call)
                streaming_executor.add_tool(chunk.tool_call, mode=state.mode)
            
            # Yield completed results during streaming
            for result in streaming_executor.get_completed_results():
                yield ToolDone(result)
        
        # ── Step 4: Await remaining tools ──
        all_results = await streaming_executor.get_remaining_results()
        state.tool_results.extend(all_results)
        
        # ── Step 5: Interceptor Layer ──
        intercept_result = apply_interceptors(state, tool_blocks)
        if intercept_result.blocked:
            # Mode gate rejected a write
            state.messages.append(intercept_result.error_message)
            continue
        
        if intercept_result.needs_confirmation:
            # Write operation needs user approval
            plan = build_confirmation_plan(intercept_result.pending_tools)
            yield PendingPlan(plan)
            return  # Wait for user
        
        if intercept_result.has_options:
            yield CurrentOptions(intercept_result.options)
        
        # ── Step 6: Decide next ──
        if not tool_blocks:
            # Model only returned text — done
            break
        
        if tool_blocks and state.mode == "cowriter":
            # Model called tools in cowriter mode
            # Inject tool results and continue
            state = state.replace(
                messages=state.messages + build_tool_result_messages(all_results),
                turn_count=state.turn_count + 1,
                transition="tool_executed",
            )
            continue
        
        if state.pending_plan and not state.plan_confirmed:
            # Plan was generated, waiting for user
            break
        
        # Default: tool results in, continue
        state = state.replace(
            messages=state.messages + build_tool_result_messages(all_results),
            turn_count=state.turn_count + 1,
            transition="tool_executed",
        )
    
    # ── Final: Generate Response ──
    if not state.messages[-1].role == "assistant":
        system_prompt = await build_system_prompt(state)
        async for token in llm_client.chat_stream_tokens(
            [Message(role="system", content=system_prompt)] + state.messages
        ):
            yield StreamToken(token)
    
    yield LoopDone(final_state=state.to_dict())
```

### 2.4 Interceptor Design

Three interceptors, applied in order:

```python
def apply_interceptors(state, tool_blocks):
    result = InterceptResult()
    
    for block in tool_blocks:
        tool = tool_registry[block.name]
        
        # Interceptor 1: Mode Gate
        if state.mode == "chat" and not tool.is_read_only:
            result.blocked = True
            result.error_message = Message(
                role="system",
                content=f"对话模式禁止写入操作。工具 '{block.name}' 被拦截。"
            )
            return result
        
        # Interceptor 2: Confirmation Gate
        if tool.meta.is_destructive or tool.meta.needs_confirmation:
            result.needs_confirmation = True
            result.pending_tools.append(block)
        
        # Interceptor 3: Option Gate
        if block.name == "present_options":
            result.has_options = True
            result.options = block.arguments.get("options", [])
    
    return result
```

### 2.5 The `present_options` Tool

A special tool that the LLM can call to present structured option cards to the user:

```python
present_options_meta = ToolMeta(
    name="present_options",
    description="Present 2-3 structured options to the user for a decision. "
                "Each option has a label, description, pros/cons, and the action "
                "that will be taken if selected.",
    parameters={
        "type": "object",
        "properties": {
            "analysis": {
                "type": "string",
                "description": "Analysis text explaining the situation and the options (markdown)"
            },
            "options": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                        "description": {"type": "string"},
                        "pros": {"type": "array", "items": {"type": "string"}},
                        "cons": {"type": "array", "items": {"type": "string"}},
                        "action": {
                            "type": "object",
                            "properties": {
                                "tool": {"type": "string"},
                                "params": {"type": "object"}
                            }
                        }
                    }
                }
            },
            "session_update": {
                "type": "object",
                "properties": {
                    "phase": {"type": "string", "enum": ["explore", "plan", "execute", "review", "complete"]},
                    "goal": {"type": "string"},
                    "current_focus": {"type": "string"},
                    "is_complete": {"type": "boolean"}
                }
            }
        },
        "required": ["analysis", "options"]
    },
    concurrency=ConcurrencyMode.EXCLUSIVE,
    is_destructive=False,
    timeout=30,
    search_hint="present options to user",
)
```

When the LLM calls `present_options`:
1. The interceptor captures it (doesn't execute it as a normal tool)
2. The `analysis` text is streamed as tokens
3. The `options` array is emitted as SSE `option` events for the frontend
4. The session is saved with the options, waiting for user choice
5. When the user selects an option: the `action` from the selected option is executed, and the result is injected into the next turn's context

### 2.6 Context Compression

```python
def compress_history(messages: list[Message], target_ratio: float = 0.6) -> list[Message]:
    """Keep head (3 msgs) + tail (6 msgs), compress middle into summary."""
    
    if len(messages) <= 12:
        return messages
    
    head = messages[:3]
    tail = messages[-6:]
    middle = messages[3:-6]
    
    # Build summary of middle messages
    summary_parts = []
    for msg in middle:
        role = "用户" if msg.role == "user" else ("AI" if msg.role == "assistant" else msg.role)
        content = (msg.content or "")[:150]
        if content:
            summary_parts.append(f"[{role}]: {content}")
    
    summary = Message(
        role="system",
        content=(
            "<system-reminder>\n"
            "[已压缩的历史上下文]\n"
            + "\n".join(summary_parts[-10:])  # Keep last 10 summaries
            + "\n</system-reminder>"
        )
    )
    
    return head + [summary] + tail
```

### 2.7 Mode-Specific System Prompts

**Chat mode**: inject restrictions, read-only tools only
```
# ——— 当前模式：对话模式（只读）———
- 你只能读取和分析，不能执行任何写入操作
- 如果用户要求修改内容，礼貌地建议切换到协作模式
- 工具列表仅包含只读工具
```

**Cowriter mode**: inject collaborator persona + all tools
```
# ——— 当前模式：协作模式（可读写）———
- 你是合著者，不是代笔人
- 分析问题，提供选项，帮助用户自己写出更好的故事
- 当需要对方向做出选择时，调用 present_options 工具
- 步骤: 探索 → 选项 → 用户选择 → 执行 → 评审
```

This replaces the current JSON-forced `CoWriterMode._COWRITER_SYSTEM_PROMPT`.

### 2.8 Layered Error Recovery

Wire existing `ErrorClassifier` + `RecoveryExecutor` into the loop:

```python
try:
    async for chunk in llm.chat_stream_with_tools(...):
        ...
except Exception as e:
    decision = ErrorClassifier.classify(str(e), state.retry_count, 
                                         recovery_history=state.recovery_state.get("history", []))
    
    if decision.action == RecoveryAction.RETRY:
        await asyncio.sleep(decision.delay_seconds)
        state.retry_count += 1
        continue
    
    elif decision.action == RecoveryAction.RETRY_WITH_ERROR_CONTEXT:
        state.messages.append(Message(role="system", 
            content=f"[SELF-CORRECTION] Previous attempt failed: {str(e)}"))
        state.retry_count += 1
        continue
    
    elif decision.action == RecoveryAction.RETRY_WITH_COMPRESSED_CONTEXT:
        state.messages = RecoveryExecutor._compress_messages(state.messages)
        state.retry_count += 1
        continue
    
    elif decision.action == RecoveryAction.SWITCH_MODEL:
        llm_client.current_model = fallback_models[state.recovery_state.get("model_index", 0)]
        state.recovery_state["model_index"] = state.recovery_state.get("model_index", 0) + 1
        continue
    
    elif decision.action == RecoveryAction.GIVE_UP:
        yield StreamToken(f"\n\n[无法完成操作: {decision.message}]")
        break
```

---

## 3. File Changes

| File | Action | Description |
|------|--------|-------------|
| `agent/loop.py` | **Rewrite** | New `autonomous_loop()` replacing fixed workflow |
| `agent/super_agent.py` | Modify | Call new loop; clean up old codepaths |
| `agent/tools/base.py` | Modify | Add `needs_confirmation` to `ToolMeta` |
| `agent/tools/present_options.py` | **New** | `present_options` tool |
| `agent/tools/__init__.py` | Modify | Register `present_options` |
| `agent/prompts/system.yaml` | Modify | Add autonomous/cowriter mode sections |
| `agent/prompts/cowriter_persona.yaml` | **New** | Cowriter persona prompt section |
| `agent/nodes/classify_intent.py` | Deprecate | No longer needed (kept for backward compat) |
| `agent/nodes/plan.py` | Deprecate | Replaced by confirmation interceptor |
| `agent/agent/interceptors.py` | **New** | Mode gate, confirmation gate, option gate |
| `agent/context_compressor.py` | **New** | Token-aware context compression |
| `agent/loop_state.py` | **New** | LoopState dataclass with atomic replace |
| `agent/graph.py` | No change | LangGraph path preserved for fallback |
| `agent/cowriter/mode.py` | No change | Preserved for backward compat |
| `agent/tools/streaming_executor.py` | No change | Core executor unchanged |
| `agent/recovery.py` | No change | Already well-designed |
| `agent/attachments.py` | No change | Already well-designed |

### Total new files: ~5 (loop_state, interceptors, context_compressor, present_options, cowriter_persona)
### Total modified files: ~4 (loop, super_agent, base, system.yaml, __init__)
### Total deprecated: 2 (classify_intent, plan — kept for backward compat)

---

## 4. Migration Strategy

1. **New code lives in `autonomous_loop()`** — parallel to existing `agent_loop()`
2. **Feature flag**: `AGENT_USE_LOOP=true` already enables the loop path. We repurpose this flag.
3. **Old paths preserved**: LangGraph graph + old agent_loop remain untouched
4. **Rollback**: Set `AGENT_USE_LOOP=false` → back to LangGraph immediately

---

## 5. Non-Goals (for this iteration)

- Cowriter phase management rewrite (the 5-phase system stays accessible via session_update in present_options)
- MCP/Bedrock/Vertex support
- Multi-model orchestration (coordinator/worker pattern)
- Prompt caching with API-level cache breakpoints
- Tool use summary generation (Claude Code's `generateToolUseSummary`)
- Microcompact/snip compact
- Stop hooks (Claude Code's `executeStopHooks`)
- Token budget system with percentage-based continuation

These are advanced Claude Code features that don't have clear ROI for StoryCAD's scale yet.

---

## 6. Success Metrics

1. Multi-tool turns: model can chain 3+ tool calls in one turn (read → analyze → suggest)
2. Option cards via tool call: `present_options` produces same structured cards as current CoWriterMode
3. Mode safety: chat mode still blocks write tools correctly
4. Context compression: long conversations stay under token limit automatically
5. Error recovery: transient failures auto-retry; model errors switch to fallback
6. Backward compat: LangGraph path works identically when flag is off
