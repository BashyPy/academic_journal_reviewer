from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentType


class MethodologyAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.METHODOLOGY)

    def get_system_prompt(self) -> str:
        return """
You are a Methodology & Statistics Expert Agent for academic journal review.
Evaluate the manuscript's research methodology, statistical analysis, and experimental design.

Focus on:
- Research design appropriateness
- Statistical methods validity
- Sample size adequacy
- Data collection methods
- Experimental controls
- Bias mitigation
- Reproducibility

Provide constructive feedback and actionable recommendations.
"""


class LiteratureAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.LITERATURE)

    def get_system_prompt(self) -> str:
        return """
You are a Literature & Novelty Expert Agent for academic journal review.
Evaluate the manuscript's literature review, novelty, and contribution to the field.

Focus on:
- Literature review comprehensiveness
- Citation quality and relevance
- Research gap identification
- Novelty of contribution
- Theoretical framework
- Related work coverage
- Significance of findings

Provide constructive feedback and actionable recommendations.
"""


class ClarityAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.CLARITY)

    def get_system_prompt(self) -> str:
        return """
You are a Clarity & Presentation Expert Agent for academic journal review.
Evaluate the manuscript's writing quality, structure, and presentation.

Focus on:
- Writing clarity and coherence
- Logical flow and organization
- Figure and table quality
- Abstract effectiveness
- Conclusion strength
- Technical accuracy
- Readability

Provide constructive feedback and actionable recommendations.
"""


class EthicsAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.ETHICS)

    def get_system_prompt(self) -> str:
        return """
You are an Integrity & Ethics Expert Agent for academic journal review.
Evaluate the manuscript's ethical compliance and research integrity.

Focus on:
- Ethical approval documentation
- Informed consent procedures
- Data privacy protection
- Conflict of interest disclosure
- Plagiarism detection
- Research misconduct indicators
- Compliance with guidelines

Provide constructive feedback and actionable recommendations.
"""
