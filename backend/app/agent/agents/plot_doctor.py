from app.agent.agents.base import BaseAgent
from app.agent.schema import PlotDoctorOutput


class PlotDoctor(BaseAgent):
    prompt_name = "plot_doctor"
    output_schema = PlotDoctorOutput
