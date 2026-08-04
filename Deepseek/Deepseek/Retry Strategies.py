from abc import ABC, abstractmethod
import math
import random
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class RetryStrategy(ABC):
    """Abstract base class for retry strategies"""
    
    @abstractmethod
    def calculate_delay(self, attempt: int, base_delay_seconds: float = 1.0) -> float:
        """Calculate delay in seconds for a given attempt"""
        pass
    
    @abstractmethod
    def should_retry(self, attempt: int, max_retries: int, error_type: Optional[str] = None) -> bool:
        """Determine if retry should be attempted"""
        pass
    
    @abstractmethod
    def get_next_retry_time(self, attempt: int, base_delay_seconds: float) -> datetime:
        """Get the absolute time for the next retry"""
        pass

class ExponentialBackoffStrategy(RetryStrategy):
    """Exponential backoff with jitter"""
    
    def __init__(self, max_delay_seconds: float = 300.0, jitter: bool = True):
        self.max_delay = max_delay_seconds
        self.jitter = jitter
    
    def calculate_delay(self, attempt: int, base_delay_seconds: float = 1.0) -> float:
        """Calculate exponential backoff with optional jitter"""
        # 2^attempt * base_delay
        delay = (2 ** attempt) * base_delay_seconds
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add random jitter +/- 10%
            jitter_amount = delay * 0.1
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.1, delay)  # Ensure positive delay
        
        return delay
    
    def should_retry(self, attempt: int, max_retries: int, error_type: Optional[str] = None) -> bool:
        """Standard retry logic for exponential backoff"""
        if attempt >= max_retries:
            return False
        
        # Certain error types might be non-retryable
        non_retryable_errors = ['ValidationError', 'ConfigurationError', 'InvalidInputError']
        if error_type in non_retryable_errors:
            return False
        
        return True
    
    def get_next_retry_time(self, attempt: int, base_delay_seconds: float) -> datetime:
        """Calculate absolute time for next retry"""
        delay = self.calculate_delay(attempt, base_delay_seconds)
        return datetime.utcnow() + timedelta(seconds=delay)

class FixedDelayStrategy(RetryStrategy):
    """Fixed delay between retries"""
    
    def __init__(self, delay_seconds: float = 5.0, max_retries: int = 3):
        self.delay = delay_seconds
        self.max_retries = max_retries
    
    def calculate_delay(self, attempt: int, base_delay_seconds: float = 1.0) -> float:
        return self.delay
    
    def should_retry(self, attempt: int, max_retries: int, error_type: Optional[str] = None) -> bool:
        return attempt < max_retries
    
    def get_next_retry_time(self, attempt: int, base_delay_seconds: float) -> datetime:
        return datetime.utcnow() + timedelta(seconds=self.delay)

class CircuitBreakerStrategy(RetryStrategy):
    """Circuit breaker pattern with exponential backoff"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.failure_count: Dict[str, int] = {}
        self.last_failure_time: Dict[str, datetime] = {}
        self.circuit_state: Dict[str, str] = {}  # 'closed', 'open', 'half_open'
    
    def should_retry(self, attempt: int, max_retries: int, error_type: Optional[str] = None) -> bool:
        # Check circuit breaker state
        if self.is_circuit_open():
            return False
        return attempt < max_retries
    
    def is_circuit_open(self, provider: Optional[str] = None) -> bool:
        """Check if circuit is open for a provider"""
        key = provider or 'default'
        
        if self.circuit_state.get(key) == 'open':
            # Check if recovery timeout has elapsed
            last_failure = self.last_failure_time.get(key)
            if last_failure:
                elapsed = (datetime.utcnow() - last_failure).total_seconds()
                if elapsed >= self.recovery_timeout:
                    # Move to half-open state
                    self.circuit_state[key] = 'half_open'
                    return False
            return True
        
        return False
    
    def record_failure(self, provider: Optional[str] = None) -> None:
        """Record a failure for a provider"""
        key = provider or 'default'
        self.failure_count[key] = self.failure_count.get(key, 0) + 1
        self.last_failure_time[key] = datetime.utcnow()
        
        if self.failure_count[key] >= self.failure_threshold:
            self.circuit_state[key] = 'open'
    
    def record_success(self, provider: Optional[str] = None) -> None:
        """Record a success for a provider"""
        key = provider or 'default'
        self.failure_count[key] = 0
        self.circuit_state[key] = 'closed'
    
    def calculate_delay(self, attempt: int, base_delay_seconds: float = 1.0) -> float:
        # Use exponential backoff within circuit breaker
        delay = (2 ** attempt) * base_delay_seconds
        return min(delay, 60.0)
    
    def get_next_retry_time(self, attempt: int, base_delay_seconds: float) -> datetime:
        delay = self.calculate_delay(attempt, base_delay_seconds)
        return datetime.utcnow() + timedelta(seconds=delay)

### 3.2 Retry Manager

```python
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
import threading
import time
import logging

class RetryStatus(Enum):
    """Status of a retry operation"""
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    CIRCUIT_OPEN = "circuit_open"
    NON_RETRYABLE_ERROR = "non_retryable_error"

class RetryManager:
    """Manages retry logic for agents with multiple strategies"""
    
    def __init__(self, 
                 default_strategy: Optional[RetryStrategy] = None,
                 max_attempts: int = 3,
                 base_delay: float = 1.0):
        self.default_strategy = default_strategy or ExponentialBackoffStrategy()
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self._strategies: Dict[str, RetryStrategy] = {}
        self._circuit_breaker = CircuitBreakerStrategy()
        self._execution_attempts: Dict[str, Dict[str, int]] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def register_agent_strategy(self, agent_type: str, strategy: RetryStrategy) -> None:
        """Register a specific retry strategy for an agent type"""
        self._strategies[agent_type] = strategy
    
    def get_strategy(self, agent_type: str) -> RetryStrategy:
        """Get the retry strategy for an agent type"""
        return self._strategies.get(agent_type, self.default_strategy)
    
    def should_retry(self, 
                     agent_id: str, 
                     agent_type: str,
                     attempt: int,
                     error_type: Optional[str] = None,
                     max_retries: Optional[int] = None) -> bool:
        """Determine if a retry should be attempted"""
        if max_retries is None:
            max_retries = self.max_attempts
        
        # Check if we've exhausted retries
        if attempt >= max_retries:
            self.logger.info(f"Agent {agent_id} exceeded max retries: {attempt}/{max_retries}")
            return False
        
        # Get the appropriate strategy
        strategy = self.get_strategy(agent_type)
        
        # Check circuit breaker
        provider = self._get_provider(agent_id)
        if self._circuit_breaker.is_circuit_open(provider):
            self.logger.warning(f"Circuit open for provider {provider}, not retrying {agent_id}")
            return False
        
        # Check strategy-specific retry logic
        should_retry = strategy.should_retry(attempt, max_retries, error_type)
        
        if not should_retry:
            self.logger.debug(f"Strategy says no retry for {agent_id} (attempt {attempt}, error: {error_type})")
        else:
            self.logger.debug(f"Retry allowed for {agent_id} (attempt {attempt}, error: {error_type})")
        
        return should_retry
    
    def execute_with_retry(self,
                          agent_id: str,
                          agent_type: str,
                          executor: Callable,
                          max_retries: Optional[int] = None,
                          strategy: Optional[RetryStrategy] = None,
                          on_failure: Optional[Callable] = None,
                          on_retry: Optional[Callable] = None) -> RetryStatus:
        """Execute a function with retry logic"""
        if max_retries is None:
            max_retries = self.max_attempts
        
        strategy = strategy or self.get_strategy(agent_type)
        attempt = 0
        last_error = None
        
        while attempt <= max_retries:
            try:
                # Execute the function
                result = executor()
                
                # Record success for circuit breaker
                provider = self._get_provider(agent_id)
                self._circuit_breaker.record_success(provider)
                
                return RetryStatus.SUCCESS
                
            except Exception as e:
                last_error = e
                attempt += 1
                
                # Determine if we should retry
                error_type = type(e).__name__
                
                # Record failure for circuit breaker
                provider = self._get_provider(agent_id)
                self._circuit_breaker.record_failure(provider)
                
                # Check if we should retry
                if not self.should_retry(agent_id, agent_type, attempt, error_type, max_retries):
                    if attempt >= max_retries:
                        return RetryStatus.MAX_RETRIES_EXCEEDED
                    if self._circuit_breaker.is_circuit_open(provider):
                        return RetryStatus.CIRCUIT_OPEN
                    return RetryStatus.NON_RETRYABLE_ERROR
                
                # Call on_retry callback if provided
                if on_retry:
                    on_retry(agent_id, attempt, e)
                
                # Calculate delay and wait
                delay = strategy.calculate_delay(attempt, self.base_delay)
                self.logger.info(f"Retrying {agent_id} in {delay:.2f}s (attempt {attempt}/{max_retries})")
                
                # Wait with ability to cancel
                if not self._wait_with_timeout(delay, agent_id):
                    return RetryStatus.CANCELLED
        
        return RetryStatus.MAX_RETRIES_EXCEEDED
    
    def _wait_with_timeout(self, delay_seconds: float, agent_id: str) -> bool:
        """Wait with cancellation support"""
        # Use threading event for cancellation support
        event = threading.Event()
        cancelled = event.wait(delay_seconds)
        return not cancelled
    
    def _get_provider(self, agent_id: str) -> Optional[str]:
        """Extract provider from agent_id or context"""
        # This would be implemented to look up the provider used by this agent
        # For now, return None (default provider)
        return None
    
    def get_retry_counts(self, agent_id: str) -> Dict[str, int]:
        """Get retry statistics for an agent"""
        return self._execution_attempts.get(agent_id, {})
    
    def reset_statistics(self) -> None:
        """Reset all retry statistics"""
        with self._lock:
            self._execution_attempts.clear()
            self._circuit_breaker = CircuitBreakerStrategy()