"""Backward-compatible import — prefer state.jobs_pkg."""
from .jobs_pkg import JobsMixin

__all__ = ["JobsMixin"]
