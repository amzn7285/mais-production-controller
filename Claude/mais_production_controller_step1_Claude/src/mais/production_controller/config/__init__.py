"""
Configuration schema.

Pydantic models describing the *shape* of Production Controller
configuration (retry defaults, timeout defaults, state-store
backend selection, per-stage provider lists). No provider names,
model names, or platform-specific values are hardcoded here — actual
values are supplied at runtime via environment variables or a config
file and validated against these models.
"""
