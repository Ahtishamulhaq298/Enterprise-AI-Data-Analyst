"""Authentication & user-management controller (RBAC)."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RoleUpdate, Token, UserCreate, UserOut

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=201,
             summary="Register a new user (defaults to viewer role)")
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, full_name=payload.full_name,
                hashed_password=hash_password(payload.password),
                role=payload.role if payload.role != UserRole.ADMIN else UserRole.VIEWER)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token, summary="Login with JSON body")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")
    return Token(access_token=create_access_token(user.email, user.role.value),
                 role=user.role)


@router.post("/token", response_model=Token,
             summary="OAuth2 form login (used by the Swagger Authorize button)")
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return Token(access_token=create_access_token(user.email, user.role.value),
                 role=user.role)


@router.get("/me", response_model=UserOut, summary="Current user profile")
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserOut], summary="List users (admin only)")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(User).order_by(User.id).all()


@router.patch("/users/{user_id}/role", response_model=UserOut,
              summary="Change a user's role (admin only)")
def update_role(user_id: int, payload: RoleUpdate, db: Session = Depends(get_db),
                _: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/deactivate", response_model=UserOut,
              summary="Deactivate a user (admin only)")
def deactivate(user_id: int, db: Session = Depends(get_db),
               _: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user