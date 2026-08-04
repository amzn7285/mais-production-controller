from enum import Enum, auto
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import uuid

class ExecutionStatus(Enum):
    """Pipeline execution states"""
    PENDING = "pending"
    INITIALIZED = "initialized"
    VALIDATED = "validated"
    PLANNED = "planned"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL_COMPLETED = "partial_completed"

class AgentStatus(Enum):
    """Individual agent execution states"""
    PENDING = "pending"
    VALIDATING = "validating"
    CONFIGURING = "configuring"
    EXECUTING = "executing"
    VALIDATING_OUTPUT = "validating_output"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class ExecutionState:
    """Persistent execution state for checkpointing and recovery"""
    
    def __init__(self, execution_id: str, workflow_id: str, master_json: Dict[str, Any]):
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.master_json = master_json
        self.status = ExecutionStatus.PENDING
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at
        self.completed_at: Optional[str] = None
        
        # Execution metadata
        self.version = "1.0"
        self.execution_plan: Optional[Dict[str, Any]] = None
        self.current_phase: Optional[int] = None
        self.progress: float = 0.0
        
        # Agent states
        self.agent_states: Dict[str, AgentState] = {}
        
        # Results storage
        self.results: Dict[str, AgentResult] = {}
        self.artifacts: Dict[str, Artifact] = {}
        
        # Failure information
        self.failures: List[FailureRecord] = []
        self.last_checkpoint: Optional[str] = None
        
        # Retry information
        self.retry_counts: Dict[str, int] = {}
        self.max_retries: Dict[str, int] = {}
        
        # Provider status
        self.provider_status: Dict[str, ProviderStatus] = {}
        
        # Context data
        self.context: Dict[str, Any] = {}
        
        # Isolation information
        self.isolation_group: Optional[str] = None
        self.isolation_slot: Optional[int] = None

class AgentState:
    """State for a specific agent in the execution"""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.status = AgentStatus.PENDING
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.attempts: int = 0
        self.last_attempt_at: Optional[str] = None
        self.next_retry_at: Optional[str] = None
        self.provider_used: Optional[str] = None
        self.input_checksum: Optional[str] = None
        self.output_checksum: Optional[str] = None
        self.dependencies: List[str] = []
        self.dependents: List[str] = []
        self.failure_reason: Optional[str] = None
        self.progress: float = 0.0
        self.timeout_seconds: int = 300
        self.retry_strategy: Dict[str, Any] = {}

class AgentResult:
    """Result from an agent execution"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.success: bool = False
        self.output: Optional[Dict[str, Any]] = None
        self.artifacts: List[Artifact] = []
        self.metrics: Dict[str, Any] = {}
        self.duration_ms: Optional[int] = None
        self.provider: Optional[str] = None
        self.model_used: Optional[str] = None
        self.cost: Optional[float] = None
        self.metadata: Dict[str, Any] = {}

class Artifact:
    """Asset artifact produced by an agent"""
    
    def __init__(self, artifact_id: str, artifact_type: str, location: str):
        self.artifact_id = artifact_id
        self.artifact_type = artifact_type  # image, audio, video, json, etc.
        self.location = location
        self.checksum: Optional[str] = None
        self.size_bytes: Optional[int] = None
        self.mime_type: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.created_at = datetime.utcnow().isoformat()

class FailureRecord:
    """Record of a failure event"""
    
    def __init__(self, agent_id: str, error_type: str, message: str):
        self.agent_id = agent_id
        self.error_type = error_type
        self.message = message
        self.timestamp = datetime.utcnow().isoformat()
        self.stack_trace: Optional[str] = None
        self.retry_count: int = 0
        self.provider: Optional[str] = None
        self.context: Dict[str, Any] = {}

class ProviderStatus:
    """Health and performance status of a provider"""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.healthy: bool = True
        self.last_check_at = datetime.utcnow().isoformat()
        self.success_count: int = 0
        self.failure_count: int = 0
        self.circuit_open: bool = False
        self.circuit_open_until: Optional[str] = None
        self.latency_p95_ms: Optional[int] = None
        self.current_concurrent: int = 0
        self.max_concurrent: int = 10
        self.last_error: Optional[str] = None
        self.request_count: int = 0