from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

class RecoveryManager:
    """Manages recovery of failed executions"""
    
    def __init__(self, state_manager: StateManager, checkpoint_manager: CheckpointManager):
        self.state_manager = state_manager
        self.checkpoint_manager = checkpoint_manager
        self.logger = logging.getLogger(__name__)
    
    def can_recover(self, execution_id: str) -> bool:
        """Check if an execution can be recovered"""
        state = self.state_manager.get_state(execution_id)
        if not state:
            return False
        
        # Can recover from: FAILED, CANCELLED, PARTIAL_COMPLETED, PAUSED
        recoverable_statuses = [
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.PARTIAL_COMPLETED,
            ExecutionStatus.PAUSED
        ]
        
        return state.status in recoverable_statuses
    
    def recover_execution(self, execution_id: str) -> Dict[str, Any]:
        """Recover an execution from the latest checkpoint"""
        self.logger.info(f"Recovering execution: {execution_id}")
        
        # Check if recovery is possible
        if not self.can_recover(execution_id):
            raise ValueError(f"Execution {execution_id} cannot be recovered")
        
        # Get the latest checkpoint
        checkpoint = self.checkpoint_manager.get_latest_checkpoint(execution_id)
        if not checkpoint:
            # No checkpoint found, try to recover from state
            state = self.state_manager.get_state(execution_id)
            if not state:
                raise ValueError(f"No state or checkpoint found for execution: {execution_id}")
            
            self.logger.warning(f"No checkpoint found, recovering from state for: {execution_id}")
            return self._recover_from_state(execution_id)
        
        self.logger.info(f"Found checkpoint {checkpoint.checkpoint_id} for execution: {execution_id}")
        
        # Restore state from checkpoint
        snapshot = self.checkpoint_manager.restore_from_checkpoint(execution_id)
        
        # Update state with recovered snapshot
        self.state_manager.update_state(execution_id, {
            'status': ExecutionStatus.INITIALIZED,
            'progress': snapshot.get('progress', 0.0),
            'agent_states': snapshot.get('agent_states', {}),
            'results': snapshot.get('results', {}),
            'artifacts': snapshot.get('artifacts', {}),
            'context': snapshot.get('context', {})
        })
        
        # Determine which agents need to be retried
        retry_agents = self._identify_retry_agents(execution_id)
        
        return {
            'execution_id': execution_id,
            'recovered': True,
            'checkpoint_id': checkpoint.checkpoint_id,
            'retry_agents': retry_agents,
            'state': self.state_manager.get_state(execution_id)
        }
    
    def _recover_from_state(self, execution_id: str) -> Dict[str, Any]:
        """Recover from state without checkpoint"""
        state = self.state_manager.get_state(execution_id)
        
        # Reset status
        self.state_manager.update_state(execution_id, {
            'status': ExecutionStatus.INITIALIZED
        })
        
        # Identify which agents need to be retried
        retry_agents = self._identify_retry_agents(execution_id)
        
        return {
            'execution_id': execution_id,
            'recovered': True,
            'checkpoint_id': None,
            'retry_agents': retry_agents,
            'state': state
        }
    
    def _identify_retry_agents(self, execution_id: str) -> List[str]:
        """Identify which agents need to be retried"""
        state = self.state_manager.get_state(execution_id)
        if not state:
            return []
        
        retry_agents = []
        
        for agent_id, agent_state in state.agent_states.items():
            if agent_state.status in [
                AgentStatus.FAILED,
                AgentStatus.TIMEOUT,
                AgentStatus.PENDING
            ]:
                # Check if retry is allowed
                if agent_state.attempts < state.max_retries.get(agent_id, 3):
                    retry_agents.append(agent_id)
        
        self.logger.info(f"Identified {len(retry_agents)} agents for retry: {retry_agents}")
        return retry_agents
    
    def get_recovery_report(self, execution_id: str) -> Dict[str, Any]:
        """Generate a recovery report for an execution"""
        state = self.state_manager.get_state(execution_id)
        if not state:
            return {'error': f'Execution {execution_id} not found'}
        
        checkpoints = self.checkpoint_manager.get_checkpoints(execution_id)
        
        report = {
            'execution_id': execution_id,
            'recoverable': self.can_recover(execution_id),
            'status': state.status,
            'checkpoints_count': len(checkpoints),
            'latest_checkpoint': checkpoints[-1].timestamp if checkpoints else None,
            'progress': state.progress,
            'failed_agents': [
                agent_id for agent_id, agent_state in state.agent_states.items()
                if agent_state.status == AgentStatus.FAILED
            ],
            'pending_agents': [
                agent_id for agent_id, agent_state in state.agent_states.items()
                if agent_state.status == AgentStatus.PENDING
            ],
            'completed_agents': [
                agent_id for agent_id, agent_state in state.agent_states.items()
                if agent_state.status == AgentStatus.COMPLETED
            ],
            'retry_counts': state.retry_counts,
            'failures': [
                {
                    'agent': f.agent_id,
                    'error': f.message,
                    'timestamp': f.timestamp
                } for f in state.failures
            ]
        }
        
        return report