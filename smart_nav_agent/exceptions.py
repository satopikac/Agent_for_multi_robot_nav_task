class ConfigError(Exception):
    """Raised when configuration is invalid."""


class SemanticMapError(Exception):
    """Raised when semantic map loading/matching fails."""


class LLMError(Exception):
    """Raised when LLM request/response fails."""


class TaskPlanningError(Exception):
    """Raised when task planning fails."""

