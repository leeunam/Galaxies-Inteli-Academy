"""External pin of the single private plan; filled before the first real attempt.

This file is the trust anchor, committed after plan creation. It is excluded
from the plan's own source map to avoid a circular hash dependency.
"""

APPROVED_PLAN_SHA256 = "2e673c9c189c39a899c34df54ed5443b24d23c5e3dc78e5c3e48030d98ed7fd9"
