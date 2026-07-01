import json
from langchain_core.prompts import ChatPromptTemplate
from app.agents.base import run_agent

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个分支叙事设计师。根据因果图谱和角色档案，设计分支路线和伏笔系统。

输出严格JSON：
{{
  "branches": [
    {{
      "divergence_point": "evt_X（分歧发生的节点ID）",
      "paths": [
        ["分支路径上的事件ID列表"],
        ["另一条路径的事件ID列表"]
      ],
      "convergence_point": "evt_Y（汇合节点ID，可以为null）"
    }}
  ],
  "foreshadows": [
    {{
      "id": "fs_1",
      "planted_at": "evt_X（埋设节点ID）",
      "content": "伏笔的具体内容",
      "status": "pending",
      "planned_recycle_interval": "预期在evt_Y到evt_Z之间回收"
    }}
  ]
}}

要求：
1. 在情感值高或角色决策点处设置分歧点
2. 分支路径需有不同情感走向
3. 伏笔内容要具体，不要空泛
4. 每个伏笔都要有预期的回收区间
5. 如果图谱较小可以没有分支，返回空数组
6. 只输出JSON，不要解释"""),
    ("user", "因果图谱：{graph_data}\n角色档案：{characters}")
])


def run(state: dict) -> dict:
    result = run_agent(prompt, {
        "graph_data": json.dumps(state["graph_data"], ensure_ascii=False),
        "characters": json.dumps(state["characters"], ensure_ascii=False)
    }, temperature=0.4)
    return {
        "branches": result.get("branches", []),
        "foreshadows": result.get("foreshadows", [])
    }
