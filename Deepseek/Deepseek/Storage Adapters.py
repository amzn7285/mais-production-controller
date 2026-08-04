from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import json
import os
import sqlite3
from datetime import datetime

class StorageAdapter(ABC):
    """Abstract interface for state storage backends"""
    
    @abstractmethod
    def save_state(self, execution_id: str, state: Dict[str, Any]) -> None:
        """Persist execution state"""
        pass
    
    @abstractmethod
    def load_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Load execution state"""
        pass
    
    @abstractmethod
    def delete_state(self, execution_id: str) -> None:
        """Delete execution state"""
        pass
    
    @abstractmethod
    def list_states(self) -> List[str]:
        """List all execution IDs"""
        pass

class FileStorageAdapter(StorageAdapter):
    """File-based state storage for development/simple deployments"""
    
    def __init__(self, storage_dir: str = "./execution_states"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def _get_file_path(self, execution_id: str) -> str:
        return os.path.join(self.storage_dir, f"{execution_id}.json")
    
    def save_state(self, execution_id: str, state: Dict[str, Any]) -> None:
        file_path = self._get_file_path(execution_id)
        with open(file_path, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        file_path = self._get_file_path(execution_id)
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def delete_state(self, execution_id: str) -> None:
        file_path = self._get_file_path(execution_id)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    def list_states(self) -> List[str]:
        files = os.listdir(self.storage_dir)
        return [f.replace('.json', '') for f in files if f.endswith('.json')]

class SQLiteStorageAdapter(StorageAdapter):
    """SQLite-based state storage for production deployments"""
    
    def __init__(self, db_path: str = "./execution_states.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_states (
                execution_id TEXT PRIMARY KEY,
                state JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                workflow_id TEXT,
                status TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_status 
            ON execution_states(workflow_id, status)
        """)
        conn.commit()
        conn.close()
    
    def save_state(self, execution_id: str, state: Dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO execution_states 
            (execution_id, state, updated_at, workflow_id, status)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
        """, (
            execution_id,
            json.dumps(state),
            state.get('workflow_id'),
            state.get('status')
        ))
        conn.commit()
        conn.close()
    
    def load_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT state FROM execution_states WHERE execution_id = ?",
            (execution_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def delete_state(self, execution_id: str) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM execution_states WHERE execution_id = ?",
            (execution_id,)
        )
        conn.commit()
        conn.close()
    
    def list_states(self) -> List[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT execution_id FROM execution_states")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

### 2.2 State Manager

```python
class StateManager:
    """Manages persistent execution state with checkpoint support"""
    
    def __init__(self, storage_adapter: Optional[StorageAdapter] = None):
        self.storage = storage_adapter or FileStorageAdapter()
        self._cache: Dict[str, ExecutionState] = {}
        self._lock = threading.Lock()
        self._checkpoint_interval = 30  # seconds between checkpoints
        self._last_checkpoint_time: Dict[str, datetime] = {}
    
    def create_state(self, execution_id: str, workflow_id: str, master_json: Dict[str, Any]) -> ExecutionState:
        """Initialize a new execution state"""
        state = ExecutionState(execution_id, workflow_id, master_json)
        self._cache[execution_id] = state
        self._save_state(execution_id)
        return state
    
    def get_state(self, execution_id: str) -> Optional[ExecutionState]:
        """Retrieve execution state (cached or from storage)"""
        with self._lock:
            if execution_id in self._cache:
                return self._cache[execution_id]
            
            stored = self.storage.load_state(execution_id)
            if stored:
                state = self._deserialize_state(stored)
                self._cache[execution_id] = state
                return state
            return None
    
    def update_state(self, execution_id: str, updates: Dict[str, Any]) -> ExecutionState:
        """Update execution state with checkpointing"""
        state = self.get_state(execution_id)
        if not state:
            raise ValueError(f"Execution state not found: {execution_id}")
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        state.updated_at = datetime.utcnow().isoformat()
        
        # Auto-checkpoint based on interval
        should_checkpoint = self._should_checkpoint(execution_id)
        if should_checkpoint:
            self._save_state(execution_id)
            state.last_checkpoint = datetime.utcnow().isoformat()
        
        return state
    
    def update_agent_state(self, execution_id: str, agent_id: str, updates: Dict[str, Any]) -> None:
        """Update individual agent state"""
        state = self.get_state(execution_id)
        if not state:
            raise ValueError(f"Execution state not found: {execution_id}")
        
        if agent_id not in state.agent_states:
            # Infer agent type from execution plan if available
            agent_type = self._get_agent_type(execution_id, agent_id)
            state.agent_states[agent_id] = AgentState(agent_id, agent_type)
        
        for key, value in updates.items():
            if hasattr(state.agent_states[agent_id], key):
                setattr(state.agent_states[agent_id], key, value)
        
        state.updated_at = datetime.utcnow().isoformat()
        self._save_state(execution_id)
    
    def checkpoint(self, execution_id: str) -> bool:
        """Force a checkpoint of the current state"""
        state = self.get_state(execution_id)
        if not state:
            return False
        
        self._save_state(execution_id)
        state.last_checkpoint = datetime.utcnow().isoformat()
        return True
    
    def delete_state(self, execution_id: str) -> None:
        """Delete execution state (after completion or cleanup)"""
        with self._lock:
            if execution_id in self._cache:
                del self._cache[execution_id]
            self.storage.delete_state(execution_id)
    
    def _save_state(self, execution_id: str) -> None:
        """Internal method to persist state"""
        state = self._cache.get(execution_id)
        if state:
            serialized = self._serialize_state(state)
            self.storage.save_state(execution_id, serialized)
    
    def _should_checkpoint(self, execution_id: str) -> bool:
        """Determine if checkpoint is needed based on interval"""
        now = datetime.utcnow()
        last = self._last_checkpoint_time.get(execution_id)
        if not last:
            self._last_checkpoint_time[execution_id] = now
            return True
        
        elapsed = (now - last).total_seconds()
        return elapsed >= self._checkpoint_interval
    
    def _serialize_state(self, state: ExecutionState) -> Dict[str, Any]:
        """Convert ExecutionState to serializable dict"""
        return {
            'execution_id': state.execution_id,
            'workflow_id': state.workflow_id,
            'status': state.status.value if hasattr(state.status, 'value') else state.status,
            'created_at': state.created_at,
            'updated_at': state.updated_at,
            'completed_at': state.completed_at,
            'version': state.version,
            'execution_plan': state.execution_plan,
            'current_phase': state.current_phase,
            'progress': state.progress,
            'agent_states': {
                k: self._serialize_agent_state(v) 
                for k, v in state.agent_states.items()
            },
            'results': {
                k: self._serialize_agent_result(v) 
                for k, v in state.results.items()
            },
            'artifacts': {
                k: self._serialize_artifact(v) 
                for k, v in state.artifacts.items()
            },
            'failures': [
                self._serialize_failure_record(f) 
                for f in state.failures
            ],
            'last_checkpoint': state.last_checkpoint,
            'retry_counts': state.retry_counts,
            'max_retries': state.max_retries,
            'provider_status': state.provider_status,
            'context': state.context,
            'isolation_group': state.isolation_group,
            'isolation_slot': state.isolation_slot
        }
    
    def _deserialize_state(self, data: Dict[str, Any]) -> ExecutionState:
        """Deserialize ExecutionState from dict"""
        state = ExecutionState(
            data['execution_id'],
            data['workflow_id'],
            data.get('master_json', {})
        )
        state.status = ExecutionStatus(data['status'])
        state.created_at = data.get('created_at', datetime.utcnow().isoformat())
        state.updated_at = data.get('updated_at', datetime.utcnow().isoformat())
        state.completed_at = data.get('completed_at')
        state.version = data.get('version', '1.0')
        state.execution_plan = data.get('execution_plan')
        state.current_phase = data.get('current_phase')
        state.progress = data.get('progress', 0.0)
        state.agent_states = {
            k: self._deserialize_agent_state(k, v) 
            for k, v in data.get('agent_states', {}).items()
        }
        state.results = {
            k: self._deserialize_agent_result(k, v) 
            for k, v in data.get('results', {}).items()
        }
        state.artifacts = {
            k: self._deserialize_artifact(k, v) 
            for k, v in data.get('artifacts', {}).items()
        }
        state.failures = [
            self._deserialize_failure_record(f) 
            for f in data.get('failures', [])
        ]
        state.last_checkpoint = data.get('last_checkpoint')
        state.retry_counts = data.get('retry_counts', {})
        state.max_retries = data.get('max_retries', {})
        state.provider_status = data.get('provider_status', {})
        state.context = data.get('context', {})
        state.isolation_group = data.get('isolation_group')
        state.isolation_slot = data.get('isolation_slot')
        return state
    
    def _serialize_agent_state(self, agent_state: AgentState) -> Dict[str, Any]:
        """Serialize AgentState to dict"""
        return {
            'agent_id': agent_state.agent_id,
            'agent_type': agent_state.agent_type,
            'status': agent_state.status.value if hasattr(agent_state.status, 'value') else agent_state.status,
            'started_at': agent_state.started_at,
            'completed_at': agent_state.completed_at,
            'attempts': agent_state.attempts,
            'last_attempt_at': agent_state.last_attempt_at,
            'next_retry_at': agent_state.next_retry_at,
            'provider_used': agent_state.provider_used,
            'input_checksum': agent_state.input_checksum,
            'output_checksum': agent_state.output_checksum,
            'dependencies': agent_state.dependencies,
            'dependents': agent_state.dependents,
            'failure_reason': agent_state.failure_reason,
            'progress': agent_state.progress,
            'timeout_seconds': agent_state.timeout_seconds,
            'retry_strategy': agent_state.retry_strategy
        }
    
    def _deserialize_agent_state(self, agent_id: str, data: Dict[str, Any]) -> AgentState:
        """Deserialize AgentState from dict"""
        agent_state = AgentState(agent_id, data.get('agent_type', 'unknown'))
        agent_state.status = AgentStatus(data['status'])
        agent_state.started_at = data.get('started_at')
        agent_state.completed_at = data.get('completed_at')
        agent_state.attempts = data.get('attempts', 0)
        agent_state.last_attempt_at = data.get('last_attempt_at')
        agent_state.next_retry_at = data.get('next_retry_at')
        agent_state.provider_used = data.get('provider_used')
        agent_state.input_checksum = data.get('input_checksum')
        agent_state.output_checksum = data.get('output_checksum')
        agent_state.dependencies = data.get('dependencies', [])
        agent_state.dependents = data.get('dependents', [])
        agent_state.failure_reason = data.get('failure_reason')
        agent_state.progress = data.get('progress', 0.0)
        agent_state.timeout_seconds = data.get('timeout_seconds', 300)
        agent_state.retry_strategy = data.get('retry_strategy', {})
        return agent_state
    
    def _serialize_agent_result(self, result: AgentResult) -> Dict[str, Any]:
        """Serialize AgentResult to dict"""
        return {
            'agent_id': result.agent_id,
            'success': result.success,
            'output': result.output,
            'artifacts': [self._serialize_artifact(a) for a in result.artifacts],
            'metrics': result.metrics,
            'duration_ms': result.duration_ms,
            'provider': result.provider,
            'model_used': result.model_used,
            'cost': result.cost,
            'metadata': result.metadata
        }
    
    def _deserialize_agent_result(self, agent_id: str, data: Dict[str, Any]) -> AgentResult:
        """Deserialize AgentResult from dict"""
        result = AgentResult(agent_id)
        result.success = data.get('success', False)
        result.output = data.get('output')
        result.artifacts = [
            self._deserialize_artifact(a) 
            for a in data.get('artifacts', [])
        ]
        result.metrics = data.get('metrics', {})
        result.duration_ms = data.get('duration_ms')
        result.provider = data.get('provider')
        result.model_used = data.get('model_used')
        result.cost = data.get('cost')
        result.metadata = data.get('metadata', {})
        return result
    
    def _serialize_artifact(self, artifact: Artifact) -> Dict[str, Any]:
        """Serialize Artifact to dict"""
        return {
            'artifact_id': artifact.artifact_id,
            'artifact_type': artifact.artifact_type,
            'location': artifact.location,
            'checksum': artifact.checksum,
            'size_bytes': artifact.size_bytes,
            'mime_type': artifact.mime_type,
            'metadata': artifact.metadata,
            'created_at': artifact.created_at
        }
    
    def _deserialize_artifact(self, data: Dict[str, Any]) -> Artifact:
        """Deserialize Artifact from dict"""
        artifact = Artifact(
            data['artifact_id'],
            data['artifact_type'],
            data['location']
        )
        artifact.checksum = data.get('checksum')
        artifact.size_bytes = data.get('size_bytes')
        artifact.mime_type = data.get('mime_type')
        artifact.metadata = data.get('metadata', {})
        artifact.created_at = data.get('created_at', datetime.utcnow().isoformat())
        return artifact
    
    def _serialize_failure_record(self, failure: FailureRecord) -> Dict[str, Any]:
        """Serialize FailureRecord to dict"""
        return {
            'agent_id': failure.agent_id,
            'error_type': failure.error_type,
            'message': failure.message,
            'timestamp': failure.timestamp,
            'stack_trace': failure.stack_trace,
            'retry_count': failure.retry_count,
            'provider': failure.provider,
            'context': failure.context
        }
    
    def _deserialize_failure_record(self, data: Dict[str, Any]) -> FailureRecord:
        """Deserialize FailureRecord from dict"""
        failure = FailureRecord(
            data['agent_id'],
            data['error_type'],
            data['message']
        )
        failure.timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        failure.stack_trace = data.get('stack_trace')
        failure.retry_count = data.get('retry_count', 0)
        failure.provider = data.get('provider')
        failure.context = data.get('context', {})
        return failure
    
    def _get_agent_type(self, execution_id: str, agent_id: str) -> str:
        """Infer agent type from execution plan"""
        state = self.get_state(execution_id)
        if state and state.execution_plan:
            # Look up agent type in plan
            for phase in state.execution_plan.get('phases', []):
                for agent_config in phase.get('agents', []):
                    if agent_config.get('id') == agent_id:
                        return agent_config.get('type', 'unknown')
        return 'unknown'