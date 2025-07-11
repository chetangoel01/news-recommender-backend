from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from core.db import get_db
from core.auth import (
    authenticate_user, 
    create_user, 
    create_access_token, 
    create_refresh_token,
    verify_token,
    get_user_by_username,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from core.schemas import (
    UserRegister,
    UserLogin,
    TokenRefresh,
    UserRegisterResponse,
    UserLoginResponse,
    TokenRefreshResponse,
    UserProfile,
    ErrorResponse
)

router = APIRouter(tags=["authentication"])

@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    Creates user account, generates initial preference embedding, and returns access tokens.
    """
    try:
        # Convert Pydantic model to dict for processing
        user_dict = user_data.dict()
        
        # Create the user
        db_user = create_user(db, user_dict)
        
        # Create access and refresh tokens
        access_token = create_access_token(
            data={"sub": db_user.username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token = create_refresh_token(data={"sub": db_user.username})
        
        return UserRegisterResponse(
            user_id=db_user.id,
            email=db_user.email,
            username=db_user.username,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
        )
        
    except IntegrityError as e:
        db.rollback()
        if "username" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        elif "email" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=UserLoginResponse)
async def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return access tokens.
    """
    # Authenticate the user
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Note: User status checking removed to work with Supabase auth.users schema
    
    # Create access and refresh tokens
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return UserLoginResponse(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        user_profile=UserProfile(
            username=user.username,
            display_name=user.display_name,
            profile_image=user.profile_image
        )
    )

@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.
    """
    # Verify the refresh token
    token_payload = verify_token(token_data.refresh_token, "refresh")
    if not token_payload or not token_payload.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get the user
    user = get_user_by_username(db, token_payload.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Note: User status checking removed to work with Supabase auth.users schema
    
    # Create new access token
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return TokenRefreshResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    ) 