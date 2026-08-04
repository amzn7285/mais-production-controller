from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading

class IsolationLevel(Enum):
    """Isolation levels for failure containment"""
    NONE = "none"  # No isolation
    THREAD = "thread"  # Isolate by thread
    PROCESS = "process"  # Isolate by process
    CONTAINER = "container"  # Isolate by container

class FailureDomain:
    """Represents a failure domain for isolation"""
    
    def __init__(self, domain_id: str, isolation_level: IsolationLevel = IsolationLevel.PROCESS):
        self.domain_id = domain_id
        self.isolation_level = isolation_level
        self.agents: List[str] = []
        self.max_failures_before_shutdown = 3
        self.failure_count = 0
        self.last_failure_at: Optional[datetime] = None
        self.healthy = True
        self.created_at = datetime.utcnow().isoformat()

class FailureIsolationManager:
    """Manages failure isolation and containment"""
    
    def __init__(self):
        self._domains: Dict[str, FailureDomain] = {}
        self._agent_domain_map: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._max_failures_per_agent = 3
        self._global_failure_threshold = 10
        self._global_failure_count = 0
        self._isolated = False
    
    def register_agent(self, agent_id: str, domain_id: str, isolation_level: Optional[IsolationLevel] = None) -> None:
        """Register an agent in a failure domain"""
        with self._lock:
            # Create domain if it doesn't exist
            if domain_id not in self._domains:
                isolation = isolation_level or IsolationLevel.PROCESS
                self._domains[domain_id] = FailureDomain(domain_id, isolation)
            
            # Add agent to domain
            domain = self._domains[domain_id]
            if agent_id not in domain.agents:
                domain.agents.append(agent_id)
                self._agent_domain_map[agent_id] = domain_id
    
    def record_failure(self, agent_id: str, error: Exception) -> bool:
        """Record a failure and determine if isolation is needed"""
        with self._lock:
            # Record global failure
            self._global_failure_count += 1
            
            # Get agent's domain
            domain_id = self._agent_domain_map.get(agent_id)
            if not domain_id:
                return False
            
            domain = self._domains.get(domain_id)
            if not domain:
                return False
            
            # Record domain failure
            domain.failure_count += 1
            domain.last_failure_at = datetime.utcnow()
            
            # Check if domain should be isolated
            if domain.failure_count >= domain.max_failures_before_shutdown:
                domain.healthy = False
                self.logger.warning(f"Domain {domain_id} isolated due to {domain.failure_count} failures")
                return True
            
            # Check global isolation
            if self._global_failure_count >= self._global_failure_threshold:
                self._isolated = True
                self.logger.warning(f"Global isolation triggered with {self._global_failure_count} failures")
                return True
            
            return False
    
    def get_agent_domain(self, agent_id: str) -> Optional[FailureDomain]:
        """Get the failure domain for an agent"""
        domain_id = self._agent_domain_map.get(agent_id)
        if domain_id:
            return self._domains.get(domain_id)
        return None
    
    def is_agent_isolated(self, agent_id: str) -> bool:
        """Check if an agent is in an isolated domain"""
        domain = self.get_agent_domain(agent_id)
        if domain:
            return not domain.healthy
        return False
    
    def is_globally_isolated(self) -> bool:
        """Check if global isolation is active"""
        return self._isolated
    
    def get_domain_health(self, domain_id: str) -> Dict[str, Any]:
        """Get health status of a domain"""
        domain = self._domains.get(domain_id)
        if not domain:
            return {'error': 'Domain not found'}
        
        return {
            'domain_id': domain.domain_id,
            'healthy': domain.healthy,
            'agent_count': len(domain.agents),
            'failure_count': domain.failure_count,
            'isolation_level': domain.isolation_level.value,
            'last_failure_at': domain.last_failure_at
        }
    
    def reset_domain(self, domain_id: str) -> None:
        """Reset a failure domain"""
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain:
                domain.failure_count = 0
                domain.healthy = True
                domain.last_failure_at = None
    
    def reset_all(self) -> None:
        """Reset all failure domains"""
        with self._lock:
            for domain in self._domains.values():
                domain.failure_count = 0
                domain.healthy = True
                domain.last_failure_at = None
            
            self._global_failure_count = 0
            self._isolated = False
    
    def get_isolated_agents(self) -> List[str]:
        """Get all agents in isolated domains"""
        isolated = []
        for agent_id, domain_id in self._agent_domain_map.items():
            domain = self._domains.get(domain_id)
            if domain and not domain.healthy:
                isolated.append(agent_id)
        return isolated