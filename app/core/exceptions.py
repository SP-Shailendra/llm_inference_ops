"""
Custom exceptions for the platform.
"""


class InferencePlatformException(Exception):
    """Base platform exception."""


class ProfileNotFoundException(InferencePlatformException):
    pass


class DuplicateProfileException(InferencePlatformException):
    pass


class InvalidProfileException(InferencePlatformException):
    pass


class RoutingException(InferencePlatformException):
    pass


class CacheException(InferencePlatformException):
    pass


class BudgetExceededException(InferencePlatformException):
    pass


class PolicyViolationException(InferencePlatformException):
    pass


class ProviderUnavailableException(InferencePlatformException):
    pass


class ModelUnavailableException(InferencePlatformException):
    pass


class GovernanceException(InferencePlatformException):
    pass