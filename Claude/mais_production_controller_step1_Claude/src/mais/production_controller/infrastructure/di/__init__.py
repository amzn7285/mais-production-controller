"""
Dependency injection.

Contains the service-container port (`container.py`) that concrete
composition roots use to register and resolve interface
implementations. No concrete wiring happens in Step 1 — that occurs
once real agents, providers, and a state-store adapter exist.
"""
