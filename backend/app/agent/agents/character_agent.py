from app.agent.agents.base import BaseAgent
from app.agent.schema import CharacterOutput


class CharacterAgent(BaseAgent):
    prompt_name = "character"
    output_schema = CharacterOutput
