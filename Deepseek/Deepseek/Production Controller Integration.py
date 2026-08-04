class ProductionController:
    """Main Production Controller with reliability layer integration"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize reliability components
        self.state_manager = StateManager()
        self.checkpoint_manager = CheckpointManager()
        self.retry_manager = RetryManager()
        self.recovery_manager = RecoveryManager(self.state_manager, self.checkpoint_manager)
        self.failure_isolation = FailureIsolationManager()
        
        # Load configuration
        self._load_reliability_config(config)
        
        self.logger = logging.getLogger(__name__)
    
    def _load_reliability_config(self, config: Dict[str, Any]) -> None:
        """Load reliability configuration"""
        reliability_config = config.get('reliability', {})
        
        # Load retry strategies
        retry_config = reliability_config.get('retry_policies', {})
        for agent_type, policy in retry_config.items():
            if policy.get('strategy') == 'exponential':
                strategy = ExponentialBackoffStrategy(
                    max_delay_seconds=policy.get('max_delay_seconds', 60.0),
                    jitter=policy.get('jitter', True)
                )
                self.retry_manager.register_agent_strategy(agent_type, strategy)
            elif policy.get('strategy') == 'fixed':
                strategy = FixedDelayStrategy(
                    delay_seconds=policy.get('delay_seconds', 5.0),
                    max_retries=policy.get('max_attempts', 3)
                )
                self.retry_manager.register_agent_strategy(agent_type, strategy)
        
        # Load timeout configuration
        self.timeouts = reliability_config.get('timeouts', {})
        
        # Load failure isolation configuration
        isolation_config = reliability_config.get('failure_isolation', {})
        domain_groups = isolation_config.get('domain_groups', {})
        for domain_id, agents in domain_groups.items():
            for agent_id in agents:
                self.failure_isolation.register_agent(agent_id, domain_id)
        
        # Load circuit breaker configuration
        circuit_config = reliability_config.get('circuit_breakers', {})
        for provider, config in circuit_config.items():
            # Circuit breaker registration would happen in provider client
            pass
    
    def execute_agent(self, agent_id: str, agent_type: str, execution_func: Callable) -> Dict[str, Any]:
        """Execute an agent with full reliability layer"""
        state = self.state_manager.get_state(agent_id)
        
        try:
            # Check if agent is isolated
            if self.failure_isolation.is_agent_isolated(agent_id):
                raise Exception(f"Agent {agent_id} is in isolated domain")
            
            # Check global isolation
            if self.failure_isolation.is_globally_isolated():
                raise Exception("Global isolation triggered")
            
            # Get timeout
            timeout = self.timeouts.get(agent_type, self.timeouts.get('default', 300))
            
            # Execute with retry
            result = self.retry_manager.execute_with_retry(
                agent_id=agent_id,
                agent_type=agent_type,
                executor=execution_func,
                max_retries=state.max_retries.get(agent_id, 3),
                on_failure=lambda agent, attempt, error: self._handle_failure(agent, attempt, error),
                on_retry=lambda agent, attempt, error: self._handle_retry(agent, attempt, error)
            )
            
            if result == RetryStatus.SUCCESS:
                self._handle_success(agent_id)
            else:
                self._handle_failure(agent_id, state.agent_states[agent_id].attempts, None)
            
            return {'agent_id': agent_id, 'status': result.value}
            
        except Exception as e:
            self._handle_failure(agent_id, 0, e)
            raise
    
    def _handle_failure(self, agent_id: str, attempt: int, error: Optional[Exception]) -> None:
        """Handle agent failure"""
        # Record failure for isolation
        self.failure_isolation.record_failure(agent_id, error)
        
        # Create failure record
        failure = FailureRecord(
            agent_id=agent_id,
            error_type=type(error).__name__ if error else 'UnknownError',
            message=str(error) if error else 'Unknown error'
        )
        
        # Update state
        state = self.state_manager.get_state(agent_id)
        if state:
            state.failures.append(failure)
            state.retry_counts[agent_id] = attempt
            
            self.state_manager.update_agent_state(agent_id, {
                'status': AgentStatus.FAILED,
                'failure_reason': str(error) if error else 'Unknown error',
                'attempts': attempt
            })
        
        # Checkpoint on failure
        self.checkpoint_manager.create_checkpoint(
            execution_id=agent_id,
            state=state.__dict__ if state else {},
            metadata={'failure': str(error) if error else 'Unknown error'}
        )
    
    def _handle_success(self, agent_id: str) -> None:
        """Handle agent success"""
        self.state_manager.update_agent_state(agent_id, {
            'status': AgentStatus.COMPLETED
        })
        
        # Checkpoint on success
        self.checkpoint_manager.create_checkpoint(
            execution_id=agent_id,
            state=self.state_manager.get_state(agent_id).__dict__,
            metadata={'status': 'success'}
        )
    
    def _handle_retry(self, agent_id: str, attempt: int, error: Exception) -> None:
        """Handle retry"""
        self.state_manager.update_agent_state(agent_id, {
            'status': AgentStatus.RETRYING,
            'attempts': attempt,
            'failure_reason': str(error)
        })
    
    def checkpoint_execution(self, execution_id: str) -> None:
        """Create a checkpoint for the entire execution"""
        state = self.state_manager.get_state(execution_id)
        if state:
            self.checkpoint_manager.create_checkpoint(
                execution_id=execution_id,
                state=state.__dict__,
                metadata={'phase': state.current_phase, 'progress': state.progress}
            )
    
    def recover_execution(self, execution_id: str) -> Dict[str, Any]:
        """Recover a failed execution"""
        recovery_result = self.recovery_manager.recover_execution(execution_id)
        
        # Log recovery
        self.logger.info(f"Recovered execution {execution_id}: {recovery_result}")
        
        return recovery_result