"""
Retry Policy interface.

Retry decisions (whether to retry, how long to wait) are owned by
the Controller per the architecture review, and are made through
this interface so the policy — fixed backoff, exponential backoff,
jittered, etc. — is swappable per stage via `RetryPolicyConfig`
without changing Controller or agent code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mais.production_controller.domain.models import RetryDecision, RetryPolicyConfig


class IRetryPolicy(ABC):
    """Abstract contract for a retry policy."""

    @abstractmethod
    def configure(self, config: RetryPolicyConfig) -> None:
        """Apply `config` to this policy instance before use."""
        raise NotImplementedError

    @abstractmethod
    def decide(self, attempt_number: int, error_was_retriable: bool) -> RetryDecision:
        """Given the attempt number just completed (1-indexed) and
        whether the failure was flagged retriable, return a
        `RetryDecision` describing whether to retry and how long to
        wait first."""
        raise NotImplementedError
