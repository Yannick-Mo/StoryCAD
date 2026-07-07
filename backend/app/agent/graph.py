import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph, START, END
from app.agent.state import AgentState
from app.agent.tools import get_tool_registry
from app.llm.client import LLMClient
from app.llm.types import Message, ToolCall, ToolDef


def build_super_graph(db: AsyncSession) -> StateGraph:
    tools = get_tool_registry(db)

    async def classify_intent(state: AgentState) -> dict:
        last_msg = state["messages"][-1] if state["messages"] else None
        if not last_msg or last_msg.role not in ("user", "tool"):
            return {"current_intent": "simple_q"}

        content = last_msg.content or ""
        tool_names = ", ".join(tools.keys()) if tools else "无"
        system_text = (
            f"你是意图分类器。根据用户请求决定意图类别：\n"
            f"可用工具：{tool_names}\n"
            f"- simple_q：可以直接回答的简单问题\n"
            f"- tool_call：需要使用特定工具的请求\n"
            f"- complex：需要多步推理或子代理的复杂请求\n"
            f"如果请求匹配某个可用工具，调用该工具。否则只输出意图类别。"
        )

        msgs = [
            Message(role="system", content=system_text),
            Message(role="user", content=content),
        ]

        tool_defs = []
        for t_name, t_inst in tools.items():
            d = t_inst.to_openai_tool()
            tool_defs.append(ToolDef(type=d["type"], function=d["function"]))

        client = LLMClient()
        result = await client.chat(messages=msgs, tools=tool_defs or None)

        if result.tool_calls:
            return {
                "current_intent": "tool_call",
                "tool_calls": result.tool_calls,
                "intermediate_steps": state.get("intermediate_steps", [])
                + [{"action": "classify", "intent": "tool_call"}],
            }

        raw = (result.content or "").strip().lower()
        if "complex" in raw:
            intent = "complex"
        else:
            intent = "simple_q"

        return {
            "current_intent": intent,
            "intermediate_steps": state.get("intermediate_steps", [])
            + [{"action": "classify", "intent": intent}],
        }

    async def execute_tool(state: AgentState) -> dict:
        intent = state["current_intent"]
        results: list[dict] = []
        steps: list[dict] = list(state.get("intermediate_steps", []))

        if intent == "tool_call":
            tool_calls = state.get("tool_calls", [])
            for tc in tool_calls:
                fn_name = ""
                args: dict[str, Any] = {}
                if tc.function:
                    fn_name = tc.function.get("name", "")
                    try:
                        args = json.loads(tc.function.get("arguments", "{}"))
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                inst = tools.get(fn_name)
                if inst:
                    try:
                        tr = await inst.run(db=db, **args)
                        r = {"tool": fn_name, "success": tr.success, "data": tr.data}
                        if tr.error:
                            r["error"] = tr.error
                        results.append(r)
                        steps.append({"action": fn_name, "args": args, "result": r})
                    except Exception as e:
                        results.append({"tool": fn_name, "success": False, "error": str(e)})
                        steps.append({"action": fn_name, "args": args, "error": str(e)})

        elif intent == "complex":
            sub_results = await _run_sub_agents(state, db)
            steps.append({"action": "sub_agents", "results": sub_results})

        return {
            "tool_results": results,
            "intermediate_steps": steps,
            "sub_agent_results": state.get("sub_agent_results", {}),
        }

    async def generate(state: AgentState) -> dict:
        client = LLMClient()
        msgs = list(state["messages"])

        project_ctx = state.get("project_context", {})
        title = project_ctx.get("project_title", "未命名项目")
        sys_parts = [f"你是资深中文小说编辑与写作导师，正在协助用户创作《{title}》。"]

        rag = state.get("rag_context", [])
        if rag:
            sys_parts.append(f"\n参考知识：\n" + "\n".join(str(r) for r in rag))

        tool_results = state.get("tool_results", [])
        if tool_results:
            sys_parts.append("\n工具执行结果：\n" + json.dumps(tool_results, ensure_ascii=False))

        msgs.insert(0, Message(role="system", content="\n".join(sys_parts)))

        result = await client.chat(messages=msgs)
        assistant_msg = Message(role="assistant", content=result.content)
        msgs.append(assistant_msg)

        return {"messages": msgs}

    builder = StateGraph(AgentState)

    builder.add_node("classify_intent", classify_intent)
    builder.add_node("execute_tool", execute_tool)
    builder.add_node("generate", generate)

    builder.add_edge(START, "classify_intent")
    builder.add_conditional_edges(
        "classify_intent",
        _route_intent,
        {
            "simple_q": "generate",
            "tool_call": "execute_tool",
            "complex": "execute_tool",
        },
    )
    builder.add_edge("execute_tool", "generate")
    builder.add_edge("generate", END)

    return builder


def _route_intent(state: AgentState) -> str:
    return state.get("current_intent", "simple_q")


async def _run_sub_agents(state: AgentState, db: AsyncSession) -> dict[str, Any]:
    project_id = state.get("project_id") or (state.get("project_context") or {}).get("project_id")
    if not project_id:
        return {"note": "缺少 project_id，无法运行子代理"}
    return {"status": "deferred", "note": "复杂请求的子代理路由待实现"}
