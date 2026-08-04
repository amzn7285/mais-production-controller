"""
Domain layer.

Pure, framework-independent building blocks: enums, dataclasses /
Pydantic models, exceptions, and constants. Nothing in this package
may import from `interfaces`, `application`, or `infrastructure` —
those layers depend on `domain`, never the reverse. This keeps the
domain model reusable by the Controller, every Agent, and any future
API or CLI surface without pulling in orchestration or provider
concerns.
"""
