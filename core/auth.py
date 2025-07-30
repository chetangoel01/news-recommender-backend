from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from core.db import get_db
from core.models import User
from core.schemas import TokenData
import os
import requests
from jose import jwt, JWTError
from jose.utils import base64url_decode

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Password hashing
# Configure bcrypt to handle version compatibility issues
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='passlib')

pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__ident="2b"
)

# HTTP Bearer token scheme
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type_from_payload: str = payload.get("type")
        
        if username is None or token_type_from_payload != token_type:
            return None
        
        token_data = TokenData(username=username)
        return token_data
    except JWTError:
        return None

def verify_google_id_token(id_token: str, audience: str) -> Optional[dict]:
    """Verify Google ID token and return payload if valid."""
    try:
        # Get Google's public keys
        resp = requests.get("https://www.googleapis.com/oauth2/v3/certs")
        jwks = resp.json()
        unverified_header = jwt.get_unverified_header(id_token)
        key = None
        for k in jwks["keys"]:
            if k["kid"] == unverified_header["kid"]:
                key = k
                break
        if not key:
            return None
        # Build public key
        public_key = jwt.construct_rsa_public_key(key)
        payload = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=audience
        )
        return payload
    except Exception:
        return None

def verify_apple_id_token(id_token: str, audience: str) -> Optional[dict]:
    """Verify Apple ID token and return payload if valid."""
    try:
        # Get Apple's public keys
        resp = requests.get("https://appleid.apple.com/auth/keys")
        jwks = resp.json()
        unverified_header = jwt.get_unverified_header(id_token)
        key = None
        for k in jwks["keys"]:
            if k["kid"] == unverified_header["kid"]:
                key = k
                break
        if not key:
            return None
        # Build public key
        public_key = jwt.construct_rsa_public_key(key)
        payload = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=audience
        )
        return payload
    except Exception:
        return None

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    if not username:
        return None
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user_data: dict) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(user_data["password"])
    
    # Set default preferences if not provided
    default_preferences = {
        "categories": user_data.get("preferences", {}).get("categories", ["technology"]),
        "language": user_data.get("preferences", {}).get("language", "en"),
        "content_type": user_data.get("preferences", {}).get("content_type", "mixed"),
        "notification_settings": {
            "push_enabled": True,
            "email_digest": True,
            "breaking_news": True
        }
    }
    
    db_user = User(
        username=user_data["username"],
        email=user_data["email"],
        display_name=user_data.get("display_name"),
        password_hash=hashed_password,
        preferences=default_preferences
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        token_data = verify_token(token, "access")
        if token_data is None or token_data.username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    
    # Update last active timestamp
    if hasattr(user, 'last_active'):
        user.last_active = datetime.now(timezone.utc)
        db.commit()
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to get the current active user."""
    # Note: User status checking removed to work with Supabase auth.users schema
    return current_user 