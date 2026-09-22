class JevError(Exception):
    """Base class for expected Jev errors."""


class ConfigurationError(JevError):
    """Configuration is missing or invalid."""


class RequestValidationError(JevError):
    """A caller supplied an invalid decision request."""


class ProviderError(JevError):
    """A provider could not produce a valid decision."""


class ProviderTimeout(ProviderError):
    """A provider did not answer within its configured timeout."""


class InvalidProviderResponse(ProviderError):
    """A provider answered, but its response failed the decision contract."""


class UnsupportedChoice(InvalidProviderResponse):
    """A provider returned a choice outside the explicit candidate set."""
