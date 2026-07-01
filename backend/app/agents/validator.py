import json
from langchain_core.prompts import ChatPromptTemplate
from app.agents.base import run_agent

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个叙事逻辑审查官。审查完整骨架，找出逻辑问题。

输出严格JSON，是一个问题数组，如无问题则返回空数组：
[
  {{
    "severity": "high/medium/low",
    "category": "因果断裂/OOC/伏笔悬空/规则违反/锚点缺失",
    "description": "问题的具体描述",
    "location": "涉及的事件ID或角色名",
    "suggestion": "修复建议"
  }}
]

审查维度：
1. 因果断裂：事件链是否有孤立节点？是否有节点只有入边没有出边（末端除外）？
2. OOC：角色行为是否和其 desire_topology/bottom_line 冲突？
3. 伏笔悬空：是否有伏笔没有对应的回收事件？
4. 规则违反：事件是否和世界规则的禁止项冲突？
5. 锚点缺失：用户指定的锚点事件是否都在图谱中？

注意：
- 只有明确的问题才报告，不要过度审查
- low 级别的问题可以忽略
- 只输出JSON数组，不要解释"""),
    ("user", "完整骨架数据：\n{full_skeleton}")
])


def run(state: dict) -> dict:
    full_skeleton = {
        "creative_doc": state["creative_doc"],
        "world_rules": state["world_rules"],
        "characters": state["characters"],
        "graph": state["graph_data"],
        "branches": state["branches"],
        "foreshadows": state["foreshadows"]
    }
    result = run_agent(prompt, {
        "full_skeleton": json.dumps(full_skeleton, ensure_ascii=False)
    }, temperature=0.2)
    report = result if isinstance(result, list) else result.get("issues", [])
    return {"validation_report": report}
