from .base import BasePersonaProfile
from ..models import StoryTheme, Persona


class COOProfile(BasePersonaProfile):
    persona = Persona.COO
    theme_weights = {
        StoryTheme.REVENUE_INCIDENT:    0.95,
        StoryTheme.PERFORMANCE_DEGRAD:  0.95,
        StoryTheme.CAPACITY_RISK:       0.85,
        StoryTheme.COMPLIANCE_RISK:     0.70,
        StoryTheme.COST_OVERRUN:        0.65,
        StoryTheme.SECURITY_THREAT:     0.55,
        StoryTheme.DEPLOY_INCIDENT:     0.40,
        StoryTheme.POSITIVE_MILESTONE:  0.70,
    }
    priority_floor = 50.0
    max_stories = 4
    owns_decisions_about = ["operations", "customer-success", "SLA"]
