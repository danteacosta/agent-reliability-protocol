"""Optional domain profiles distributed beside the neutral ARP core."""

from .agent_smell_degradation_v1 import AGENT_SMELL_PROFILE, validate_agent_smell_run

__all__ = ["AGENT_SMELL_PROFILE", "validate_agent_smell_run"]
