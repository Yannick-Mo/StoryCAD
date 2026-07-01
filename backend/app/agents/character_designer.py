import json
from langchain_core.prompts import ChatPromptTemplate
from app.agents.base import run_agent

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个角色设计师。根据创意文档和世界观规则，设计角色全息档案。

输出严格JSON，是一个数组：
[
  {{
    "name": "角色名",
    "desire_topology": {{
      "表层欲望": "角色表面追求的目标",
      "深层需求": "角色真正需要的心理需求",
      "核心恐惧": "角色最害怕发生的事"
    }},
    "bottom_line": "角色绝不会越过的底线",
    "vulnerability": "可以被对手利用的弱点",
    "language_genes": ["典型台词1", "典型台词2", "典型台词3"],
    "relationships": {{
      "其他角色名": {{"信任": 0-100, "威胁": 0-100, "吸引力": 0-100}}
    }},
    "growth_arc": "角色在故事中的成长弧线描述"
  }}
]

要求：
1. 如有 character_seeds，必须包含这些角色，并丰富其档案
2. 如无角色种子，根据核心冲突自动创建 2-3 个角色
3. 关系矩阵中的数值需合理：对立角色威胁高、信任低
4. 语言基因要符合角色身份
5. 只输出JSON，不要解释"""),
    ("user", "创意文档：{creative_doc}\n世界观规则：{world_rules}")
])


def run(state: dict) -> dict:
    result = run_agent(prompt, {
        "creative_doc": json.dumps(state["creative_doc"], ensure_ascii=False),
        "world_rules": json.dumps(state["world_rules"], ensure_ascii=False)
    }, temperature=0.4)
    characters = result if isinstance(result, list) else result.get("characters", [])
    return {"characters": characters}
