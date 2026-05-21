from .base import BasePersonaProfile
from ..models import StoryTheme, Persona


class CTOProfile(BasePersonaProfile):
    persona = Persona.CTO
    theme_weights = {
        StoryTheme.DEPLOY_INCIDENT:     1.00,
        StoryTheme.PERFORMANCE_DEGRAD:  0.95,
        StoryTheme.CAPACITY_RISK:       0.95,
        StoryTheme.REVENUE_INCIDENT:    0.80,
        StoryTheme.SECURITY_THREAT:     0.65,
        StoryTheme.COST_OVERRUN:        0.60,
        StoryTheme.COMPLIANCE_RISK:     0.55,
        StoryTheme.POSITIVE_MILESTONE:  0.75,
    }
    priority_floor = 45.0
    max_stories = 5
    owns_decisions_about = ["architecture", "headcount", "tech-debt"]
