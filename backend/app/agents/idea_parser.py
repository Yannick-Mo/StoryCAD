import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME

# 初始化模型，要求返回 JSON
llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model=MODEL_NAME,
    temperature=0.3,
    model_kwargs={"response_format": {"type": "json_object"}}
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个专业的叙事骨架解析器。从用户的创意种子、约束、角色种子、锚点中提取结构化信息，输出严格JSON：

{{
  "core_conflict": "核心冲突的一句话描述",
  "implied_world_clues": ["隐含的世界观线索1", "线索2"],
  "character_seeds": [{{"name": "名字", "traits": "特质"}}],
  "structural_constraints": ["硬约束1", "约束2"],
  "anchor_events": [{{"description": "锚点事件描述", "order": 1}}]
}}

只输出JSON，不要解释。"""),
    ("user", """创意种子：{idea}
设计约束：{constraints}
角色种子：{character_seeds}
关键锚点：{anchors}""")
])

def parse(state: dict) -> dict:
    """解析用户输入，返回 creative_doc"""
    raw = state["raw_input"]
    chain = prompt | llm
    response = chain.invoke({
        "idea": raw.get("idea", ""),
        "constraints": raw.get("constraints", ""),
        "character_seeds": raw.get("character_seeds", ""),
        "anchors": raw.get("anchors", "")
    })
    creative_doc = json.loads(response.content)
    return {"creative_doc": creative_doc}