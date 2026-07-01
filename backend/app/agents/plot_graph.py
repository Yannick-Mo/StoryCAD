import json
from langchain_core.prompts import ChatPromptTemplate
from app.agents.base import run_agent

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个情节架构师。根据世界观、角色档案和创意文档，生成因果事件图谱。

输出严格JSON：
{{
  "nodes": [
    {{"id": "evt_1", "description": "事件描述（15-30字）", "emotion_value": 0-100}}
  ],
  "edges": [
    {{"source": "evt_1", "target": "evt_2", "type": "necessary/possible/indirect"}}
  ]
}}

要求：
1. 必须包含创意文档中的所有 anchor_events
2. 因果关系类型：necessary(必然导致), possible(可能导致), indirect(间接影响)
3. 节点 8-15 个，形成完整的故事弧线
4. emotion_value 要有起伏：开场中等(50-70)→上升→高潮(80-100)→下降→结局(40-60)
5. 边必须闭合：每个节点至少有一条入边和一条出边（开头和结尾节点除外）
6. 事件描述要具体，不要泛泛而谈
7. 只输出JSON，不要解释"""),
    ("user", "创意文档：{creative_doc}\n世界观规则：{world_rules}\n角色档案：{characters}")
])


def run(state: dict) -> dict:
    result = run_agent(prompt, {
        "creative_doc": json.dumps(state["creative_doc"], ensure_ascii=False),
        "world_rules": json.dumps(state["world_rules"], ensure_ascii=False),
        "characters": json.dumps(state["characters"], ensure_ascii=False)
    }, temperature=0.4)
    return {"graph_data": result}
