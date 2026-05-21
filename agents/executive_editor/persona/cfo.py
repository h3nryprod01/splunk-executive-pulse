from .base import BasePersonaProfile
from ..models import StoryTheme, Persona


class CFOProfile(BasePersonaProfile):
    persona = Persona.CFO

    theme_weights = {
        StoryTheme.REVENUE_INCIDENT:    1.00,
        StoryTheme.COST_OVERRUN:        1.00,
        StoryTheme.COMPLIANCE_RISK:     0.85,  # fines = $
        StoryTheme.SECURITY_THREAT:     0.65,  # only if breach has $ impact
        StoryTheme.PERFORMANCE_DEGRAD:  0.70,  # conversion drop = $
        StoryTheme.CAPACITY_RISK:       0.55,
        StoryTheme.DEPLOY_INCIDENT:     0.30,
        StoryTheme.POSITIVE_MILESTONE:  0.55,
    }
    priority_floor = 50.0
    max_stories = 4
    owns_decisions_about = ["budget", "investment-approval", "cost-control"]
