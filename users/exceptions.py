class UserServiceException(Exception):
    """Base exception for user service errors"""
    pass

class EmailSendingError(UserServiceException):
    """Raised when email sending fails"""
    pass

class UserRegistrationError(UserServiceException):
    """Raised when user registration fails"""
    pass

class EmailVerificationError(UserServiceException):
    """Raised when email verification fails"""
    pass

class InvalidTokenError(EmailVerificationError):
    """Raised when verification token is invalid"""
    pass

class UserNotFoundError(UserServiceException):
    """Raised when user is not found"""
    pass
