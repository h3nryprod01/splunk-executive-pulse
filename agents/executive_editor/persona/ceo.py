from .base import BasePersonaProfile
from ..models import StoryTheme, Persona


class CEOProfile(BasePersonaProfile):
    persona = Persona.CEO

    theme_weights = {
        StoryTheme.REVENUE_INCIDENT:    1.00,
        StoryTheme.SECURITY_THREAT:     0.85,  # only if reputation risk
        StoryTheme.COMPLIANCE_RISK:     0.90,
        StoryTheme.COST_OVERRUN:        0.55,
        StoryTheme.PERFORMANCE_DEGRAD:  0.60,
        StoryTheme.DEPLOY_INCIDENT:     0.35,  # technical detail
        StoryTheme.CAPACITY_RISK:       0.45,
        StoryTheme.POSITIVE_MILESTONE:  0.70,
    }
    priority_floor = 55.0
    max_stories = 3                          # CEO attention scarce
    include_good_news = True
    owns_decisions_about = ["strategic", "reputation", "major-investment"]
