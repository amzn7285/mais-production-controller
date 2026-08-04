from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import threading

class Checkpoint:
    """Represents a single checkpoint"""
    
    def __init__(self, checkpoint_id: str, execution_id: str, snapshot: Dict[str, Any]):
        self.checkpoint_id = checkpoint_id
        self.execution_id = execution_id
        self.snapshot = snapshot
        self.timestamp = datetime.utcnow().isoformat()
        self.metadata: Dict[str, Any] = {}

class CheckpointManager:
    """Manages checkpoints for execution recovery"""
    
    def __init__(self, storage_dir: str = "./checkpoints"):
        self.storage_dir = storage_dir
        self._checkpoints: Dict[str, List[Checkpoint]] = {}
        self._lock = threading.Lock()
        self._max_checkpoints_per_execution = 10
        self._checkpoint_interval_seconds = 30
        self._last_checkpoint_time: Dict[str, datetime] = {}
        os.makedirs(storage_dir, exist_ok=True)
    
    def create_checkpoint(self, 
                         execution_id: str, 
                         state: Dict[str, Any],
                         metadata: Optional[Dict[str, Any]] = None) -> Checkpoint:
        """Create a new checkpoint"""
        with self._lock:
            checkpoint_id = f"{execution_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            checkpoint = Checkpoint(checkpoint_id, execution_id, state)
            
            if metadata:
                checkpoint.metadata.update(metadata)
            
            # Initialize list if needed
            if execution_id not in self._checkpoints:
                self._checkpoints[execution_id] = []
            
            # Add checkpoint
            self._checkpoints[execution_id].append(checkpoint)
            
            # Limit number of checkpoints
            if len(self._checkpoints[execution_id]) > self._max_checkpoints_per_execution:
                # Remove oldest checkpoint
                self._checkpoints[execution_id].pop(0)
            
            # Save to disk
            self._save_checkpoint(checkpoint)
            
            # Update last checkpoint time
            self._last_checkpoint_time[execution_id] = datetime.utcnow()
            
            return checkpoint
    
    def get_latest_checkpoint(self, execution_id: str) -> Optional[Checkpoint]:
        """Get the latest checkpoint for an execution"""
        with self._lock:
            checkpoints = self._checkpoints.get(execution_id, [])
            if not checkpoints:
                # Try to load from disk
                self._load_checkpoints_from_disk(execution_id)
                checkpoints = self._checkpoints.get(execution_id, [])
            
            if checkpoints:
                return checkpoints[-1]
            return None
    
    def get_checkpoints(self, execution_id: str, limit: Optional[int] = None) -> List[Checkpoint]:
        """Get all checkpoints for an execution"""
        with self._lock:
            checkpoints = self._checkpoints.get(execution_id, [])
            if not checkpoints:
                self._load_checkpoints_from_disk(execution_id)
                checkpoints = self._checkpoints.get(execution_id, [])
            
            if limit:
                return checkpoints[-limit:]
            return checkpoints
    
    def restore_from_checkpoint(self, execution_id: str, checkpoint_id: Optional[str] = None) -> Dict[str, Any]:
        """Restore execution state from a checkpoint"""
        if checkpoint_id:
            # Find specific checkpoint
            checkpoints = self.get_checkpoints(execution_id)
            for cp in checkpoints:
                if cp.checkpoint_id == checkpoint_id:
                    return cp.snapshot
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        else:
            # Use latest checkpoint
            checkpoint = self.get_latest_checkpoint(execution_id)
            if checkpoint:
                return checkpoint.snapshot
            raise ValueError(f"No checkpoints found for execution: {execution_id}")
    
    def delete_checkpoints(self, execution_id: str, older_than: Optional[datetime] = None) -> None:
        """Delete checkpoints for an execution"""
        with self._lock:
            if execution_id not in self._checkpoints:
                return
            
            if older_than:
                # Delete checkpoints older than specified time
                self._checkpoints[execution_id] = [
                    cp for cp in self._checkpoints[execution_id]
                    if datetime.fromisoformat(cp.timestamp) > older_than
                ]
            else:
                # Delete all checkpoints
                self._checkpoints[execution_id] = []
                
                # Delete from disk
                execution_dir = os.path.join(self.storage_dir, execution_id)
                if os.path.exists(execution_dir):
                    for file in os.listdir(execution_dir):
                        if file.endswith('.json'):
                            os.remove(os.path.join(execution_dir, file))
                    os.rmdir(execution_dir)
    
    def should_checkpoint(self, execution_id: str) -> bool:
        """Determine if a checkpoint should be created"""
        if execution_id not in self._last_checkpoint_time:
            return True
        
        elapsed = (datetime.utcnow() - self._last_checkpoint_time[execution_id]).total_seconds()
        return elapsed >= self._checkpoint_interval_seconds
    
    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save a checkpoint to disk"""
        execution_dir = os.path.join(self.storage_dir, checkpoint.execution_id)
        os.makedirs(execution_dir, exist_ok=True)
        
        file_path = os.path.join(execution_dir, f"{checkpoint.checkpoint_id}.json")
        
        # Prepare data for serialization
        data = {
            'checkpoint_id': checkpoint.checkpoint_id,
            'execution_id': checkpoint.execution_id,
            'snapshot': checkpoint.snapshot,
            'timestamp': checkpoint.timestamp,
            'metadata': checkpoint.metadata
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_checkpoints_from_disk(self, execution_id: str) -> None:
        """Load checkpoints from disk for an execution"""
        execution_dir = os.path.join(self.storage_dir, execution_id)
        if not os.path.exists(execution_dir):
            return
        
        checkpoints = []
        files = sorted([f for f in os.listdir(execution_dir) if f.endswith('.json')])
        
        for file in files:
            file_path = os.path.join(execution_dir, file)
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                checkpoint = Checkpoint(
                    data['checkpoint_id'],
                    data['execution_id'],
                    data['snapshot']
                )
                checkpoint.timestamp = data['timestamp']
                checkpoint.metadata = data.get('metadata', {})
                checkpoints.append(checkpoint)
            except Exception as e:
                # Log error but continue
                print(f"Error loading checkpoint {file}: {e}")
        
        # Sort by timestamp
        checkpoints.sort(key=lambda x: x.timestamp)
        self._checkpoints[execution_id] = checkpoints