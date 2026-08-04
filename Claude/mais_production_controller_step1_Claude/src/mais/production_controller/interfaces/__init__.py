"""
Interfaces layer (ports, in Clean Architecture terms).

Abstract base classes only — no implementation logic. Every method
here is either `@abstractmethod` or a concrete helper that composes
other abstract calls (still with no business logic of its own).

Concrete adapters (a specific TTS provider, a specific state-store
backend, the real Controller implementation) live in
`infrastructure` and `application` in later steps and depend on
these interfaces — these interfaces never depend on them. This is
what makes the architecture provider-agnostic and DI-ready: anything
depending on "an `IProvider`" or "an `IStateStore`" can be handed any
conforming implementation at construction time.
"""
