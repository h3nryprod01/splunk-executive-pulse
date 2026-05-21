from __future__ import annotations
import logging
import time
from datetime import datetime, timezone

from agents.impact_quantifier.models import QuantifierOutput, QuantifiedSignal
from .models import EditorOutput, StoryTheme, Persona
from .persona.ceo  import CEOProfile
from .persona.cfo  import CFOProfile
from .persona.ciso import CISOProfile
from .persona.cto  import CTOProfile
from .persona.coo  import COOProfile
from .clustering import cluster_signals, infer_theme
from .ranking    import rank_clusters
from .decision_extractor import extract_decisions

logger = logging.getLogger(__name__)


PERSONA_PROFILES = {
    Persona.CEO:  CEOProfile(),
    Persona.CFO:  CFOProfile(),
    Persona.CISO: CISOProfile(),
    Persona.CTO:  CTOProfile(),
    Persona.COO:  COOProfile(),
}


class ExecutiveEditorAgent:

    def edit(
        self, quantifier_output: QuantifierOutput, persona: Persona,
        briefing_date: datetime | None = None,
    ) -> EditorOutput:
        start = time.perf_counter()
        profile = PERSONA_PROFILES[persona]
        briefing_date = briefing_date or datetime.now(tz=timezone.utc)

        # 1. Cluster
        clusters = cluster_signals(quantifier_output.quantified_signals)
        logger.info(f"Clustered {len(quantifier_output.quantified_signals)} signals → {len(clusters)} clusters")

        # 2. Rank for this persona
        ranked = rank_clusters(clusters, profile)

        # 3. Split out "good news" candidates
        good_news_candidates = [c for c in ranked if c.theme == StoryTheme.POSITIVE_MILESTONE]
        non_positive = [c for c in ranked if c.theme != StoryTheme.POSITIVE_MILESTONE]

        # 4. Cap to max_stories
        selected = non_positive[: profile.max_stories]
        skipped = len(non_positive) - len(selected)

        good_news_id = None
        if profile.include_good_news and good_news_candidates:
            good_news_id = good_news_candidates[0].cluster_id
            selected.append(good_news_candidates[0])

        # 5. Headline = highest non-good-news cluster
        if not non_positive:
            # Edge case: a "calm day" with only good news
            headline_id = good_news_id or (selected[0].cluster_id if selected else "")
        else:
            headline_id = non_positive[0].cluster_id

        # 6. Decisions
        sig_index = {s.signal_id: s for s in quantifier_output.quantified_signals}
        decisions = extract_decisions(selected, sig_index, profile)

        total_shown = sum(c.aggregate_exposure_usd for c in selected)
        duration_ms = int((time.perf_counter() - start) * 1000)

        logger.info(
            f"[{persona.value}] selected={len(selected)} headline={headline_id} "
            f"decisions={len(decisions)} skipped={skipped} duration={duration_ms}ms"
        )

        return EditorOutput(
            persona=persona,
            briefing_date=briefing_date,
            headline_cluster_id=headline_id,
            clusters=selected,
            decisions_required=decisions,
            good_news_cluster_id=good_news_id,
            skipped_clusters_count=skipped,
            total_exposure_usd_shown=round(total_shown, 2),
        )
