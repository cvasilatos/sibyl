#!/usr/bin/env python3

from sibyl.reviewer import ReviewSystem
from unittest.mock import Mock

# Test the parsing with the bold headers
mock_client = Mock()
reviewer = ReviewSystem(mock_client)

response = """**NOVELTY:** The paper introduces **HowkGPT**, a novel approach.
**METHODOLOGY:** The methodology is **well-documented**.
**RESULTS:** The results demonstrate improvements.
**CLARITY:** The paper is well-written.
**IMPACT:** Makes a meaningful contribution.
**LIMITATIONS:** Some limitations exist.
**STRENGTHS:** Has multiple strengths.
**SCORE:** **7.5/10**
**RECOMMENDATION:** **Revise**
**DETAILED FEEDBACK:** Some feedback here."""

criteria = reviewer._parse_review_response(response)

print("Novelty:", repr(criteria.novelty))
print("Score:", criteria.overall_score)
print("Recommendation:", repr(criteria.recommendation))