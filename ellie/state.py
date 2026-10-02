import logging
from enum import Enum, auto
from typing import Callable, List

logger = logging.getLogger(__name__)

class State(Enum):
    SLEEPING = auto()
    LISTENING = auto()
    THINKING = auto()
    ACTING = auto()
    SPEAKING = auto()
    CONFIRMING = auto()
    ERROR = auto()

class StateManager:
    """Manages the state transitions for the Ellie voice assistant."""

    def __init__(self):
        self._current_state = State.SLEEPING
        self._callbacks: List[Callable[[State, State], None]] = []
        
        # Define valid transitions from each state
        self._valid_transitions = {
            State.SLEEPING: {State.LISTENING},
            State.LISTENING: {State.THINKING, State.SLEEPING, State.ERROR},
            State.THINKING: {State.ACTING, State.SPEAKING, State.SLEEPING, State.ERROR},
            State.ACTING: {State.SPEAKING, State.CONFIRMING, State.ERROR},
            State.SPEAKING: {State.SLEEPING, State.LISTENING},
            State.CONFIRMING: {State.ACTING, State.SLEEPING},
            State.ERROR: {State.SLEEPING}
        }

    @property
    def current_state(self) -> State:
        """Returns the current state."""
        return self._current_state

    @property
    def is_active(self) -> bool:
        """Returns True if the assistant is not SLEEPING."""
        return self._current_state != State.SLEEPING

    def transition(self, new_state: State) -> bool:
        """
        Transition to a new state if valid.
        
        Args:
            new_state (State): The state to transition to.
            
        Returns:
            bool: True if transition was successful, False otherwise.
        """
        if new_state in self._valid_transitions.get(self._current_state, set()):
            old_state = self._current_state
            self._current_state = new_state
            logger.info(f"State transition: {old_state.name} -> {new_state.name}")
            self._notify_callbacks(old_state, new_state)
            return True
        else:
            logger.warning(f"Invalid state transition attempted: {self._current_state.name} -> {new_state.name}")
            return False

    def reset(self) -> None:
        """Forces the state machine back to SLEEPING."""
        old_state = self._current_state
        self._current_state = State.SLEEPING
        logger.info(f"State reset: {old_state.name} -> {State.SLEEPING.name}")
        self._notify_callbacks(old_state, State.SLEEPING)

    def on_state_change(self, callback: Callable[[State, State], None]) -> None:
        """Registers a callback for state changes."""
        self._callbacks.append(callback)

    def _notify_callbacks(self, old_state: State, new_state: State) -> None:
        """Notifies all registered callbacks of a state change."""
        for callback in self._callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
