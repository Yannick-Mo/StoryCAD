import json
from langchain_core.prompts import ChatPromptTemplate
from app.agents.base import run_agent

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个世界观架构师。根据创意解析文档，构建世界规则体系。

输出严格JSON：
{{
  "rules": [
    {{
      "category": "物理规则/魔法体系/社会结构/科技水平/文化习俗",
      "description": "规则的具体描述",
      "limitation": "规则的边界或限制条件"
    }}
  ],
  "history": "世界背景历史概要（100-200字）",
  "forbidden_events": ["在这个世界中不可能发生的事件1", "不可能发生的事件2"]
}}

要求：
1. 从创意文档的 implied_world_clues 推断世界观
2. 每个规则必须有明确的 limitation（不能空泛）
3. forbidden_events 必须覆盖约束中提到的限制
4. 输出 3-5 条核心规则
5. 只输出JSON，不要解释"""),
    ("user", "创意文档：{creative_doc}")
])


def run(state: dict) -> dict:
    result = run_agent(prompt, {
        "creative_doc": json.dumps(state["creative_doc"], ensure_ascii=False)
    })
    return {"world_rules": result}
