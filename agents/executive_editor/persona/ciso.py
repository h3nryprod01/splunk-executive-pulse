from .base import BasePersonaProfile
from ..models import StoryTheme, Persona


class CISOProfile(BasePersonaProfile):
    persona = Persona.CISO

    theme_weights = {
        StoryTheme.SECURITY_THREAT:     1.00,
        StoryTheme.COMPLIANCE_RISK:     1.00,
        StoryTheme.REVENUE_INCIDENT:    0.55,  # mainly if data exposed
        StoryTheme.PERFORMANCE_DEGRAD:  0.30,
        StoryTheme.COST_OVERRUN:        0.40,
        StoryTheme.DEPLOY_INCIDENT:     0.50,  # supply-chain implications
        StoryTheme.CAPACITY_RISK:       0.35,
        StoryTheme.POSITIVE_MILESTONE:  0.50,
    }
    priority_floor = 45.0   # CISO wants more granularity
    max_stories = 5
    owns_decisions_about = ["security-investment", "compliance", "MFA", "WAF"]
