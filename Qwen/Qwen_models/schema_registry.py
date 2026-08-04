"""JSON Schema registry and generator for all MAIS contracts.

The Pydantic models are the single source of truth. This module derives
versioned JSON Schema documents from them so external producers/consumers can
validate payloads without importing Python. Run as a script to emit files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from . import constants as C
from .config import ProviderConfig, RetryPolicy, RuntimeConfig
from .execution import (
    AgentTask,
    ExecutionContext,
    ExecutionPlan,
    ExecutionState,
    ExecutionStage,
)
from .manifest import ProductionManifest
from .master_production import (
    MasterProduction,
    ProductionConfiguration,
    ProductionMetadata,
    ValidationCheck,
    ValidationResults,
)
from .observability import JobStatus, LogEntry, TaskCounts
from .results import AgentResult, Artifact, Checksum, ErrorInfo, Metrics

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

# name -> (model, contract version)
CONTRACTS: dict[str, tuple[type[BaseModel], str]] = {
    "master_production": (MasterProduction, C.MASTER_PRODUCTION_SCHEMA_VERSION),
    "production_configuration": (ProductionConfiguration, C.MASTER_PRODUCTION_SCHEMA_VERSION),
    "validation_results": (ValidationResults, C.MASTER_PRODUCTION_SCHEMA_VERSION),
    "validation_check": (ValidationCheck, C.MASTER_PRODUCTION_SCHEMA_VERSION),
    "production_metadata": (ProductionMetadata, C.MASTER_PRODUCTION_SCHEMA_VERSION),
    "execution_plan": (ExecutionPlan, C.EXECUTION_PLAN_SCHEMA_VERSION),
    "execution_stage": (ExecutionStage, C.EXECUTION_PLAN_SCHEMA_VERSION),
    "agent_task": (AgentTask, C.EXECUTION_PLAN_SCHEMA_VERSION),
    "execution_state": (ExecutionState, C.EXECUTION_PLAN_SCHEMA_VERSION),
    "execution_context": (ExecutionContext, C.EXECUTION_PLAN_SCHEMA_VERSION),
    "agent_result": (AgentResult, C.AGENT_RESULT_SCHEMA_VERSION),
    "artifact": (Artifact, C.AGENT_RESULT_SCHEMA_VERSION),
    "metrics": (Metrics, C.AGENT_RESULT_SCHEMA_VERSION),
    "error_info": (ErrorInfo, C.AGENT_RESULT_SCHEMA_VERSION),
    "checksum": (Checksum, C.AGENT_RESULT_SCHEMA_VERSION),
    "production_manifest": (ProductionManifest, C.PRODUCTION_MANIFEST_SCHEMA_VERSION),
    "retry_policy": (RetryPolicy, C.RUNTIME_CONFIG_SCHEMA_VERSION),
    "provider_config": (ProviderConfig, C.RUNTIME_CONFIG_SCHEMA_VERSION),
    "runtime_config": (RuntimeConfig, C.RUNTIME_CONFIG_SCHEMA_VERSION),
    "log_entry": (LogEntry, C.MAIS_CONTRACTS_VERSION),
    "job_status": (JobStatus, C.MAIS_CONTRACTS_VERSION),
    "task_counts": (TaskCounts, C.MAIS_CONTRACTS_VERSION),
}


def build_json_schema(name: str) -> dict[str, Any]:
    """Build a versioned JSON Schema document for a named contract."""
    if name not in CONTRACTS:
        raise KeyError(f"Unknown contract name: {name!r}")

    model, version = CONTRACTS[name]
    schema = model.model_json_schema(mode="validation", by_alias=True)
    schema["$schema"] = JSON_SCHEMA_DIALECT
    schema.setdefault("title", model.__name__)
    schema["x-mais-contract"] = name
    schema["x-mais-contract-version"] = version
    return schema


def generate_json_schemas(output_dir: str | Path) -> list[Path]:
    """Write all contract schemas to `output_dir` and return the written paths."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for name, (_model, version) in CONTRACTS.items():
        schema = build_json_schema(name)
        path = out / f"{name}.v{version}.schema.json"
        path.write_text(
            json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


if __name__ == "__main__":  # pragma: no cover
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "schemas"
    for written_path in generate_json_schemas(target):
        print(written_path)