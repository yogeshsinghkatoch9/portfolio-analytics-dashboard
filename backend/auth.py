"""
Authentication Utilities for VisionWealth
Handles JWT tokens, password hashing, user authentication, and authorization.
Provides secure password management and role-based access control.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.orm import Session
from pydantic import ValidationError
import os
import secrets
import logging
from enum import Enum

from db import get_db
from models import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========================================
# CONFIGURATION
# ========================================

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))  # 7 days
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))  # 30 days

# Password Configuration
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# Security warnings
if SECRET_KEY == "your-secret-key-change-in-production":
    logger.warning(
        "⚠️  Using default SECRET_KEY! Set SECRET_KEY environment variable in production!"
    )


# ========================================
# PASSWORD HASHING
# ========================================

# Password hashing context with bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Cost factor (higher = more secure but slower)
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
    
    Returns:
        True if password matches
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password meets security requirements.
    
    Args:
        password: Password to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    
    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"Password must be at most {MAX_PASSWORD_LENGTH} characters"
    
    # Check for at least one uppercase letter
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for at least one lowercase letter
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for at least one digit
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    # Check for at least one special character
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"
    
    return True, None


# ========================================
# JWT TOKEN MANAGEMENT
# ========================================

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login",
    auto_error=False  # Don't auto-error on missing token
)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in token (should include 'sub' for user identifier)
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.debug(f"Created access token for user: {data.get('sub')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Data to encode in token
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug(f"Created refresh token for user: {data.get('sub')}")
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token to decode
    
    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != "access":
            logger.warning("Invalid token type")
            return None
        
        return payload
    
    except jwt.ExpiredSignatureError:
        logger.debug("Token has expired")
        return None
    except JWTError as e:
        logger.debug(f"JWT decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {e}")
        return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a refresh token.
    
    Args:
        token: Refresh token to decode
    
    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != "refresh":
            logger.warning("Invalid token type for refresh")
            return None
        
        return payload
    
    except jwt.ExpiredSignatureError:
        logger.debug("Refresh token has expired")
        return None
    except JWTError as e:
        logger.debug(f"Refresh token decode error: {e}")
        return None


# ========================================
# USER AUTHENTICATION
# ========================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Args:
        token: JWT access token
        db: Database session
    
    Returns:
        Authenticated User object
    
    Raises:
        HTTPException: If authentication fails
    
    Usage:
```python
        @app.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}
```
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    # Extract user identifier
    email: str = payload.get("sub")
    if email is None:
        logger.warning("Token missing 'sub' claim")
        raise credentials_exception
    
    # Get user from database
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if user is None:
            logger.warning(f"User not found: {email}")
            raise credentials_exception
        
        logger.debug(f"Authenticated user: {email}")
        return user
    
    except Exception as e:
        logger.error(f"Database error during authentication: {e}")
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current active user.
    
    Adds additional check for user active status.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Active User object
    
    Raises:
        HTTPException: If user is inactive
    """
    if hasattr(current_user, 'is_active') and not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return current_user


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to optionally get authenticated user.
    
    Returns None if no token provided or invalid.
    Useful for endpoints that work with or without authentication.
    
    Args:
        token: Optional JWT token
        db: Database session
    
    Returns:
        User object or None
    """
    if not token:
        return None
    
    try:
        payload = decode_access_token(token)
        if not payload:
            return None
        
        email = payload.get("sub")
        if not email:
            return None
        
        user = db.query(User).filter(User.email == email).first()
        return user
    
    except Exception:
        return None


# ========================================
# ROLE-BASED ACCESS CONTROL
# ========================================

def require_role(required_roles: List[str]):
    """
    Dependency factory to require specific role(s).
    
    Args:
        required_roles: List of allowed roles
    
    Returns:
        Dependency function
    
    Usage:
```python
        @app.get("/admin")
        def admin_route(user: User = Depends(require_role(["admin"]))):
            return {"message": "Admin access granted"}
```
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if not hasattr(current_user, 'role'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no role assigned"
            )
        
        user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        
        if user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        
        logger.debug(f"User {current_user.email} authorized with role: {user_role}")
        return current_user
    
    return role_checker


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to require admin role.
    
    Convenience function for admin-only endpoints.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User object if admin
    
    Raises:
        HTTPException: If user is not admin
    """
    if not hasattr(current_user, 'role'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no role assigned"
        )
    
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


# ========================================
# AUTHENTICATION HELPERS
# ========================================

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.
    
    Args:
        db: Database session
        email: User email
        password: Plain text password
    
    Returns:
        User object if authentication successful, None otherwise
    """
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            logger.info(f"Authentication failed: user not found - {email}")
            return None
        
        if not verify_password(password, user.hashed_password):
            logger.info(f"Authentication failed: invalid password - {email}")
            return None
        
        logger.info(f"User authenticated successfully: {email}")
        return user
    
    except Exception as e:
        logger.error(f"Error during authentication: {e}")
        return None


def create_tokens_for_user(user: User) -> Dict[str, Any]:
    """
    Create access and refresh tokens for a user.
    
    Args:
        user: User object
    
    Returns:
        Dictionary with access_token and refresh_token
    """
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value if hasattr(user.role, 'value') else str(user.role)}
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.email}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    }


def refresh_access_token(refresh_token: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Create new access token from refresh token.
    
    Args:
        refresh_token: Valid refresh token
        db: Database session
    
    Returns:
        Dictionary with new access_token or None if invalid
    """
    payload = decode_refresh_token(refresh_token)
    
    if not payload:
        return None
    
    email = payload.get("sub")
    if not email:
        return None
    
    # Verify user still exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    
    # Create new access token
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value if hasattr(user.role, 'value') else str(user.role)}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


# ========================================
# RATE LIMITING HELPER
# ========================================

def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    
    Handles proxy headers (X-Forwarded-For, X-Real-IP).
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Client IP address
    """
    # Check proxy headers
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client
    return request.client.host if request.client else "unknown"


# ========================================
# EXPORTS
# ========================================

__all__ = [
    # Password management
    'verify_password',
    'get_password_hash',
    'validate_password_strength',
    
    # Token management
    'create_access_token',
    'create_refresh_token',
    'decode_access_token',
    'decode_refresh_token',
    
    # Authentication dependencies
    'get_current_user',
    'get_current_active_user',
    'get_optional_user',
    'oauth2_scheme',
    
    # Authorization
    'require_role',
    'require_admin',
    
    # Helpers
    'authenticate_user',
    'create_tokens_for_user',
    'refresh_access_token',
    'get_client_ip',
    
    # Configuration
    'SECRET_KEY',
    'ALGORITHM',
    'ACCESS_TOKEN_EXPIRE_MINUTES',
    'REFRESH_TOKEN_EXPIRE_DAYS',
]
