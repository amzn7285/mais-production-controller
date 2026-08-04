# Media AI Studio (MAIS) – Production Controller Review

**Scope:** Production Controller only.
**Assumptions:** Folder structure, interfaces, models, scheduler, and state manager all exist.
**Reviewer:** Enterprise Software Reviewer
**Date:** 2026-08-04
**Posture:** Production-readiness review. Do not redesign.

---

## 1. Executive Summary

A Production Controller in a system like MAIS is the most critical component in the entire pipeline. It is the only piece that holds every other piece together, has a global view of state, and sits at the boundary between the outside world and your workers. It must be **boring, deterministic, observable, and resilient**.

The architecture intent (stateless orchestration, single source of truth, dependency graph) is correct. The risks are concentrated in four areas where Production Controllers most often fail in production:

1. **Concurrency** — the controller will be asked to run many productions at once, and the design does not yet say what "many" means or what protects the system from itself.
2. **Backpressure and resource bounds** — without explicit upper bounds on in-flight work, queue depth, and per-run memory, the first traffic spike will take the service down.
3. **Failure isolation** — one flaky provider or one malformed Master JSON must not be able to corrupt controller state, leak memory, or block other productions.
4. **Operational visibility** — without an explicit state machine, structured logs, and metrics, the team will be debugging blind at 2 a.m.

The recommendations below are graded for production readiness, not for greenfield idealism. Every 🟢 is something I would not let a service into production without.

---

## 2. Strengths of the Current Design

| # | Strength | Why it matters in production |
|---|----------|------------------------------|
| S1 | Controller is orchestration-only, no AI generation | Keeps the failure surface tiny; no provider keys or rate limits touch the controller. |
| S2 | Stateless controller reading from a State Manager | Horizontal scaling, blue/green deploys, crash recovery become trivial. |
| S3 | Single source of truth — Master Production JSON | One validation point; no hidden state inside agents that contradicts upstream. |
| S4 | Scheduler and State Manager are separate concerns | Each evolves and scales on its own axis. |
| S5 | Dependency-graph-based execution | Natural fit for parallelism and replay. |
| S6 | Provider-agnostic via interfaces | Controller stays clean while the adapter layer absorbs change. |
| S7 | Retry and aggregation are stated responsibilities | Both are non-negotiable; having them listed is the right start. |

---

## 3. Architectural Smells

| # | Smell | Where it bites |
|---|-------|----------------|
| AS1 | "Stateless" claimed, but execution state likely held in memory between agent calls | Memory leak across long pipelines; restart loses in-flight work. |
| AS2 | Implicit state machine — states derived from "which agents responded" rather than an explicit FSM | Race conditions, invalid transitions, impossible-to-reason-about retries. |
| AS3 | Scheduler and Controller in the same process / call chain | Slow agents block controller throughput. |
| AS4 | No upper bound on in-flight work — controller schedules as fast as users submit | First traffic spike exhausts memory and provider quotas. |
| AS5 | Synchronous aggregation — controller awaits every agent before returning | The controller's request timeout becomes the user's timeout. |
| AS6 | No idempotency at controller entry | Duplicate submissions produce duplicate agent invocations and duplicate cost. |
| AS7 | No distinction between "user submit" and "background run" | HTTP request lifecycle leaks into a long-running pipeline. |
| AS8 | Configuration loaded at startup only | Tuning `retry.yaml` requires a restart. |
| AS9 | No version on the Master Production JSON schema | A schema change silently breaks in-flight productions. |
| AS10 | Errors logged as strings | Loses the structured signal needed to alert, page, or count error classes. |
| AS11 | Tight coupling between controller and agent implementation language | Locks out polyglot agents for no good reason. |
| AS12 | No explicit "happy path" duration budget | No way to know when a regression is real. |

---

## 4. Missing Components

| # | Component | Severity |
|---|-----------|----------|
| M1 | Explicit State Machine (RECEIVED → VALIDATING → PLANNING → DISPATCHED → RUNNING → MERGING → QC → PUBLISHING → COMPLETED / FAILED / CANCELLED) | 🔴 Critical |
| M2 | Idempotency Layer at controller entry — `hash(MasterJSON)`, TTL 24h | 🔴 Critical |
| M3 | Resource Governor — max concurrent productions, max in-flight agents per production, per-provider cap | 🔴 Critical |
| M4 | Backpressure / Bounded Queues with shedding policy | 🔴 Critical |
| M5 | Cancellation / Abort API propagating to in-flight agents | 🔴 Critical |
| M6 | Per-agent Timeout (configurable) and per-wave Timeout (hard ceiling) | 🔴 Critical |
| M7 | Circuit Breaker per provider (open after N failures, half-open after cooldown) | 🔴 Critical |
| M8 | Dead-Letter handling — surfaced in the run report, never lost | 🔴 Critical |
| M9 | Schema Versioning of the Master Production JSON | 🟡 High |
| M10 | Async Submission API — `202 Accepted` + `production_id` | 🟡 High |
| M11 | `/livez` and `/readyz` health endpoints | 🟡 High |
| M12 | Graceful Shutdown on SIGTERM | 🟡 High |
| M13 | Metrics — counters, histograms, gauges | 🟡 High |
| M14 | Distributed Tracing — OpenTelemetry spans controller → scheduler → agent | 🟡 High |
| M15 | Audit Log — every state transition is one row, immutable | 🟡 High |
| M16 | Replay — re-run a failed production with the same inputs | 🟢 Future |
| M17 | Webhook on completion | 🟢 Future |
| M18 | Multi-tenancy / namespace isolation | 🟢 Future |
| M19 | Hot reload of configuration | 🟢 Future |
| M20 | A/B / canary routing of agents to new providers | 🟢 Future |

---

## 5. Hidden Risks

- **R1. Controller is the synchronization point.** Every module's failure mode eventually shows up here. Strict per-agent timeouts and async dispatch.
- **R2. "Stateless" in theory, stateful in practice.** If the controller holds the ExecutionPlan in memory between agent callbacks, restart loses them. Checkpoint every transition, not just the final result.
- **R3. Poison message — malformed Master JSON.** Repeated crashes if the controller keeps retrying. Validate once, return 400, never retry.
- **R4. Cascading timeout.** HTTP request timeout 30s but pipeline 5 minutes → caller retries → duplicate runs. Use async submission with `production_id`.
- **R5. Provider-driven DoS.** Empty body or 50 MB response exhausts memory. Explicit size limits on every external response.
- **R6. Clock skew.** Controller local clock + State Manager local clock = ambiguous ordering. Use monotonic sequence numbers per `production_id`.
- **R7. Scheduler starvation.** Long video jobs block short jobs. Separate priority queues.
- **R8. Secrets in logs.** Master JSON may contain OAuth tokens / PII. Log a redacted, versioned summary, never the raw payload.
- **R9. Restart ambiguity.** State Manager says `RUNNING`, controller restarts — resume, fail, or reject? Must be specified.
- **R10. Partial publish.** Merge succeeds, Publisher fails at 80% → next retry may duplicate. Use idempotency key at publisher (Instagram container ID is good).

---

## 6. Performance Bottlenecks

| # | Bottleneck | Impact | Mitigation |
|---|------------|--------|------------|
| P1 | Sequential dispatch in Wave 1 | First Reel is dominated by slowest agent | Dispatch Wave 1 concurrently via the scheduler |
| P2 | Synchronous aggregation at every wave | Controller thread blocked for whole wave | Async callbacks; state transition notifies controller |
| P3 | Reading Master JSON from storage every transition | IO bottleneck at 100+ concurrent | Cache parsed plan in memory, TTL-based invalidation |
| P4 | Full-state logging per transition | Disk IO and log volume | Emit diffs; final state is a join in the audit log |
| P5 | N+1 State Manager queries (one read/write per agent) | Latency dominates | Batch reads and writes |
| P6 | Synchronous retries with backoff inside the controller | Threads stuck | Push retries into the scheduler; controller hands off and frees |
| P7 | Per-request DB connection | Pool exhaustion | Shared pool sized to peak concurrency |
| P8 | Unbounded `pending` maps | Slow memory leak | Bounded by `max_concurrent_productions` + TTL |
| P9 | Large JSON parsing on every read | CPU spikes | Parse once at submit, version the schema |
| P10 | No connection pooling to providers | TCP handshake per call | Reuse HTTP clients with keepalive |

### Suggested performance budget for the first Reel

- Submit → first agent dispatched: < 500 ms p95
- Wave 1 (Voice ‖ Image ‖ Metadata) wall clock: < 60 s p95
- Wave 2 (Video, Thumbnail) wall clock: < 90 s p95
- Merge + QC: < 30 s p95
- Publish: < 30 s p95
- End-to-end: < 4 min p95 on a single worker
- Controller steady-state memory: < 200 MB at 50 concurrent productions
- Controller CPU at 50 concurrent: < 2 cores

---

## 7. Thread Safety

| # | Concern | Risk | Mitigation |
|---|---------|------|------------|
| T1 | Mutable shared state (in-memory map of `production_id → ExecutionPlan`) | Concurrent reads/writes corrupt the map | Thread-safe structure, or push the map into the State Manager |
| T2 | Double-dispatch on duplicate `production_id` | Two agent invocations, double cost | Idempotency check under a lock at controller entry |
| T3 | Time-of-check / time-of-use on `state.status` | One thread moved to `CANCELLING`, another reads `RUNNING` | Compare-and-swap or single mutex per `production_id` |
| T4 | Background tasks orphaned when request thread returns | Memory leak + abandoned work | Hand off to a background worker; never tie agent lifecycles to request lifecycles |
| T5 | Counter / metric races | Lost increments | Atomic counters |
| T6 | Connection pool checkouts under contention | Pool exhaustion manifests as hangs | Pool sized to `2 × max_concurrent × agents_per_wave`; reject fast when exhausted |
| T7 | Lazy singletons initialized by multiple threads | Multiple clients created | Eager init at startup, or double-checked locking |
| T8 | Thread pool exhaustion under retry storms | New productions stop | Bulkhead: separate pool for retries vs new work |

---

## 8. Async Safety

| # | Concern | Risk | Mitigation |
|---|---------|------|------------|
| A1 | Blocking call in the event loop (sync DB, sync HTTP, `time.sleep`) | Stops the entire loop | All IO must be async; wrap sync calls with `asyncio.to_thread` only as a last resort, and instrument them |
| A2 | `await` in a hot loop without backpressure | Unbounded tasks, memory blow-up | `asyncio.Semaphore` per resource, or bounded `asyncio.Queue` |
| A3 | Fire-and-forget tasks (`asyncio.create_task` without storing the reference) | Task GC'd mid-flight, silent data loss | Strong reference set of in-flight tasks; await on graceful shutdown |
| A4 | Cancellation not propagated to children | Agent keeps running after user cancels | Propagate `CancelledError` / `context.WithCancel` to all children |
| A5 | Exception swallowed in `gather(..., return_exceptions=True)` | Partial failure hidden | Inspect every result; explicit per-task status |
| A6 | CPU-bound step on the event loop (large JSON validation) | Stops all scheduling | Run in a thread pool |
| A7 | Re-entrancy of the state transition handler | Deadlock | Per-`production_id` lock around the whole transition; non-reentrant |
| A8 | Mixing asyncio and threading primitives | Hangs or deadlocks | Use `asyncio.Event` consistently within the event loop |

---

## 9. Memory Usage

| # | Concern | Risk | Mitigation |
|---|---------|------|------------|
| MEM1 | Unbounded `pending_productions` map | OOM after days of operation | LRU with hard cap (e.g. 10 000 entries) + TTL |
| MEM2 | Per-call allocations not released | Slow leak | Weak refs, explicit `del` on plan completion, profile with `tracemalloc` / `pprof` |
| MEM3 | Large provider responses held in memory | Spike on burst | Stream to artifact store; do not buffer full response in the controller |
| MEM4 | Logs buffered before flush | Lost logs on crash | Structured logger flushes per line; no `StringIO` buffer |
| MEM5 | Object pools / clients not reused | GC pressure | One HTTP client, one DB pool per process; reuse across requests |
| MEM6 | Memory not measured in production | Leak invisible until OOM | Export `process_resident_memory_bytes` and `gc_time` as metrics |
| MEM7 | Backpressure absent on incoming HTTP | Slow consumer → slow producer → memory grows | Size limit on body; reject early |
| MEM8 | History/audit log in process memory | Grows unbounded | Audit log lives in State Manager / external store, not in the controller process |

### Memory budget for v1

- Idle controller: < 80 MB
- Per production in-flight: < 5 MB (controller's share only; media is streamed to artifact store)
- Steady state at 50 concurrent: < 200 MB
- Hard ceiling: fail fast at 500 MB, emit alert, shed new work

---

## 10. Error Handling

| # | Concern | Recommendation |
|---|---------|----------------|
| E1 | Distinguish error classes | Validation → 400 (no retry). Transient (5xx, 429, timeout) → retryable. Logic error → dead-letter after N retries. |
| E2 | Never swallow exceptions silently | Every catch must rethrow, return a structured error, or write a `dead` state transition. |
| E3 | Avoid bare `except Exception` | Catches `KeyboardInterrupt`, `MemoryError`. |
| E4 | Errors must carry context | `production_id`, `agent`, `attempt`, `provider`, `model`, `latency_ms`, `error_class`, `retryable`. |
| E5 | Per-error retry policy | Network → exp backoff. Rate limit → respect `Retry-After`. Provider 4xx → no retry. |
| E6 | Total wall-clock budget | Cap total time per agent (e.g. 5 min) and per production (e.g. 30 min). |
| E7 | Error budget alerting | Page on `error_rate > 5% over 5 min`. |
| E8 | Errors in cleanup | If writing final state to State Manager fails, log to local fallback file; never lose the final outcome. |
| E9 | Provider errors normalized | Provider Adapter returns a uniform `ProviderError`; controller never sees SDK-specific exceptions. |
| E10 | "At least once" + idempotency | The right delivery semantics when combined with idempotency keys. |

---

## 11. Security

| # | Concern | Recommendation |
|---|---------|----------------|
| SEC1 | Auth at the submit endpoint | API key minimum; OAuth2 / JWT short TTL preferred. |
| SEC2 | Authz | Caller must have `production:create` scope; admin for replay / cancel. |
| SEC3 | Input size limit | Reject Master JSON > 256 KB at the edge. |
| SEC4 | Input depth / complexity limit | Prevent JSON-bomb DoS. |
| SEC5 | Secrets | Env / Vault only; never in request body, never logged. |
| SEC6 | PII in logs | Master JSON may contain user topic text; redact or hash before logging. |
| SEC7 | TLS everywhere | `https://` at the public edge; `https://` or mTLS internally. |
| SEC8 | Rate limit per caller | Token bucket per API key; reject with 429 when exceeded. |
| SEC9 | SSRF | If controller ever fetches a user URL, validate against an allowlist. |
| SEC10 | Dependency CVE scanning | `pip-audit` / `npm audit` in CI on every build. |
| SEC11 | Audit log integrity | Append-only; hash-chaining if compliance requires it. |
| SEC12 | Least privilege | Controller's DB user can only read/write its own tables; no DDL, no cross-tenant reads. |
| SEC13 | Webhook signature verification | HMAC; verify on receiver. |
| SEC14 | No provider keys in controller process | Keys live in the Provider Adapter's secret store. |
| SEC15 | Replay protection | Idempotency keys have a TTL; same key twice in 24h is one production. |

---

## 12. Production Readiness Checklist (Gate Criteria)

The controller should not be declared production-ready until every item below is green.

| Area | Criterion |
|------|-----------|
| State | Explicit FSM with ≥ 9 named states, transition table, unit tests. |
| State | Every transition checkpointed to State Manager before the next begins. |
| Concurrency | Tested at 50 concurrent productions, no leaks, no deadlocks, no races. |
| Concurrency | Load test report (p50 / p95 / p99 latency, error rate, throughput) attached. |
| Reliability | Kill the controller mid-run, restart, verify resume. |
| Reliability | Inject provider 5xx, verify circuit breaker opens and recovers. |
| Reliability | Inject malformed input, verify 400 fast, no retry. |
| Observability | Every state transition emits a structured log line with `production_id`, `agent`, `state`, `latency_ms`. |
| Observability | Metrics: `productions_started_total`, `productions_completed_total`, `productions_failed_total`, `productions_in_flight`, `agent_duration_seconds`, `provider_errors_total{provider,class}`, `queue_depth`. |
| Observability | Distributed tracing: one trace per `production_id`, spans per agent. |
| Security | Auth required; size limit enforced; secrets not in logs; CVE scan clean. |
| Operations | `/livez` and `/readyz` work; graceful shutdown drains in-flight work. |
| Operations | Runbook for the top 5 error classes exists. |
| Operations | On-call alerting wired (error rate, queue depth, memory). |

---

## 13. Maintainability

| # | Concern | Recommendation |
|---|---------|----------------|
| MNT1 | No tests | Unit tests per transition, integration tests for the full pipeline, chaos tests (kill, inject failures). |
| MNT2 | Magic numbers in code | All thresholds in config, not code. |
| MNT3 | No ADRs | One-page ADR per non-obvious choice. |
| MNT4 | Untyped boundaries | Pydantic / dataclasses / generated types for the Agent Contract. |
| MNT5 | Single huge `controller.py` | Split: `state.py`, `dispatch.py`, `aggregate.py`, `retry.py`, `circuit_breaker.py`, `metrics.py`. |
| MNT6 | No dependency injection | Constructor injection; no DI container needed. |
| MNT7 | No version field on internal messages | Add `schema_version` to every internal message. |
| MNT8 | No feature flags | Test new behavior in production without a deploy. |

---

## 14. Recommendations

### 🟢 Must Have Before First Production Deploy

| # | Recommendation | Reason | Benefit | Complexity |
|---|----------------|--------|---------|-----------|
| RC1 | Explicit State Machine with 9 named states and a transition table | Implicit state from "which agents responded" causes invalid transitions and untraceable bugs | Predictable behavior, easier testing, foundation for retry/cancel | Medium |
| RC2 | Async submission (`202 Accepted` + `production_id`) | Sync submission times out long before pipeline finishes; causes duplicate runs | Stable caller contract, no cascading timeouts | Low |
| RC3 | Idempotency at controller entry (`hash(MasterJSON)`, TTL 24h) | Duplicate submissions cause duplicate cost | Safe retries, predictable spend | Low |
| RC4 | Resource Governor — max concurrent productions, max in-flight agents per production, per-provider cap | Without bounds, the first burst takes the service down | Stability under load | Medium |
| RC5 | Per-agent and per-wave timeouts, hard ceiling on total production time | Without ceilings, a hung agent blocks forever | Bounded latency, predictable retries | Low |
| RC6 | Circuit breaker per provider | Flapping providers should not block the pipeline | Resilience | Medium |
| RC7 | Dead-letter handling for exhausted retries — surfaced in the run report | Otherwise failures silently disappear | Operability | Low |
| RC8 | Cancellation API — user can stop a production; cancel propagates to in-flight agents | Otherwise stuck runs are unkillable | Operator control | Medium |
| RC9 | Checkpoint after every state transition, not only at the end | Restart loses all in-flight work otherwise | Crash safety | Low |
| RC10 | Health endpoints (`/livez`, `/readyz`) | K8s / load balancer needs them; otherwise rolling deploys break | Operability | Low |
| RC11 | Graceful shutdown on SIGTERM | Killing in-flight work loses user submissions | Clean deploys, no lost work | Low |
| RC12 | Structured JSON logging with `production_id` correlation | String logs are unsearchable | Debuggability | Low |
| RC13 | Metrics export (Prometheus-compatible) | "Is the controller healthy?" is unanswerable without metrics | Observability | Low |
| RC14 | Distributed tracing (OpenTelemetry) | One slow agent in a wave of 5 is invisible without spans | End-to-end latency analysis | Medium |
| RC15 | Auth + size limit + rate limit at the submit endpoint | Open controller = open wallet | Security baseline | Low-Medium |
| RC16 | Schema versioning of the Master Production JSON; controller refuses unknown versions | Silent breakage of in-flight productions on schema change | Backwards compatibility | Low |
| RC17 | Per-call memory budget with hard cap and fast-shed policy | Memory leak is the #1 controller failure mode in production | Stability | Low |
| RC18 | State transition uses compare-and-swap (or single mutex per `production_id`) | Prevents double-dispatch on concurrent retries | Correctness | Low |
| RC19 | HTTP client / DB pool initialized once at startup, reused | Per-request init is a 10× performance bug | Performance | Low |
| RC20 | Async safety: all IO async, all CPU-bound work off the event loop, all child tasks referenced | The most common async footguns | Correctness | Medium |
| RC21 | Production Readiness Checklist (§12) signed off | Gate discipline prevents the "it works in dev" trap | Confidence | Process |
| RC22 | Load test report at target concurrency attached to the launch | Without a number, "it scales" is a wish | Evidence | Medium |

### 🔵 Future Enhancements

| # | Recommendation | Reason | Benefit | Complexity |
|---|----------------|--------|---------|-----------|
| RC23 | Hot reload of configuration (`agents.yaml`, `providers.yaml`, `retry.yaml`) | Avoids restarts for tuning | Operability | Medium |
| RC24 | Replay API — re-run a failed production with the same inputs | Shortens recovery | Operability | Medium |
| RC25 | Webhook on completion with HMAC signature | Avoids polling | UX | Low |
| RC26 | Multi-tenancy / namespace isolation with per-tenant quotas | Required when MAIS becomes a platform | SaaS readiness | High |
| RC27 | A/B / canary routing of agents to new providers | Safe rollouts | Velocity | Medium |
| RC28 | Saga / compensating actions for publish (e.g. delete Instagram container if upload fails) | Avoids orphan uploads | Correctness | Medium |
| RC29 | Per-tenant secret store (Vault integration) | Required for multi-tenant | Security | Medium |
| RC30 | Hash-chained audit log for tamper-evidence | Compliance | Trust | Medium |
| RC31 | Workflow orchestrator migration to Prefect OSS / Dagster OSS for declarative DAGs, caching, retries | n8n is not the right orchestrator long-term for declarative pipelines | Maintainability, observability | High |
| RC32 | Cross-region replication of the State Manager for HA | Single-region = single point of failure | Availability | High |

---

## 15. Enterprise Best Practices — One-Page Summary

1. **Make the state machine explicit.** If you can draw it on a whiteboard, you can test it.
2. **Checkpoint every transition, not just the final result.** Restart-safety is the cheapest reliability you'll ever buy.
3. **Bound everything.** Concurrent productions, in-flight agents, per-provider rate, memory per run, wall-clock per run, log size, queue depth.
4. **Fail fast, fail loud, fail structured.** Bad input → 400, never retry. Good input but provider 5xx → retry with backoff, then circuit-break. Every error has a class, a count, and an alert.
5. **Be async end-to-end.** If anything in the controller blocks the event loop, your p99 is already broken.
6. **Authenticate, authorize, rate-limit, size-limit at the edge.** The controller should never trust its caller.
7. **Observe or die.** Structured logs, metrics, traces, and an audit log — all four, not just one.
8. **No secrets in code, in config files, in logs, or in the request body.** The only place a key lives is the secret store.
9. **Idempotency is not optional.** Without it, retries multiply cost.
10. **Cancel is a feature.** If the user can't stop a runaway production, the system is not production-ready.

---

*End of Production Controller review.*
