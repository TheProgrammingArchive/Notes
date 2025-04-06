from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone
from typing import Annotated, Union
from fastapi import Depends, FastAPI, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordBearer, APIKeyCookie, OAuth2PasswordRequestForm
from crud import Session, get_session, select
from models import UserDB
from decouple import config

SECRET_KEY = config('SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SessionDep = Annotated[Session, Depends(get_session)]


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
cookie_scheme = APIKeyCookie(name='access_token', auto_error=False)

def verify_pwd(text_pwd: str, encrypted_pwd: str):
    return pwd_context.verify(text_pwd, encrypted_pwd)


def encrypt_pwd(text_pwd: str):
    return pwd_context.encrypt(text_pwd)


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, ALGORITHM)
    return encoded_jwt


def get_usr_from_db(username, session: SessionDep):
    user = session.exec(select(UserDB).where(UserDB.username == username)).first()
    return user


def authenticate_user(username: str, password: str, session: SessionDep):
    user = get_usr_from_db(username, session)
    # print(password, verify_pwd(password, user.encrypted_pwd))
    if not user or not verify_pwd(password, user.encrypted_pwd):
        raise HTTPException(detail="Invalid username or password", status_code=404)

    return user


def get_logged_user(token: Annotated[str, Depends(cookie_scheme)], session: SessionDep):
    print(token)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
        usr = payload.get('sub')
        if usr is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = get_usr_from_db(usr, session)
    if user is None:
        raise credentials_exception

    return user
