from fastapi import FastAPI, Query, Path, Form, Depends, status, Request
from fastapi.templating import Jinja2Templates
from typing import Union, Annotated
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from models import UserBase, UserDB, Notes, UserCreate, NoteBase, NoteUpdate
from crud import create_all, get_session
from sqlmodel import select, Session
from security import get_logged_user, OAuth2PasswordRequestForm, authenticate_user, Token, create_access_token, \
    encrypt_pwd

app = FastAPI()


@app.on_event('startup')
def startup():
    create_all()


SessionDep = Annotated[Session, Depends(get_session)]
templates = Jinja2Templates(directory="templates")


def validate_username(username: str, session: SessionDep):
    users = session.exec(select(UserDB)).all()
    for user in users:
        if user.username == username:
            return False

    return True


@app.post('/create_user/', response_model=UserBase)
def create_user(user: UserCreate, session: SessionDep):
    if not validate_username(user.username, session):
        raise HTTPException(detail="Username Exists", status_code=404)

    user.encrypted_pwd = encrypt_pwd(user.encrypted_pwd)
    user = UserDB.model_validate(user)
    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@app.post('/login')
def login_page(data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    user = authenticate_user(data.username, data.password, session=session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({'sub': user.username})
    # return get_logged_user(Token(token_content=access_token, token_type='bearer').token_content, session)
    return Token(access_token=access_token, token_type='bearer')


@app.get('/view_all/', response_model=list[UserDB])
def view_all(session: SessionDep):
    items = session.exec(select(UserDB)).all()
    return items


@app.post('/new_note')
def create_note(note: NoteBase, user: Annotated[UserDB, Depends(get_logged_user)], session: SessionDep):
    if user is not None:
        note = Notes.model_validate(note)
        note.user_id = user.id
        user.notes.append(note)
        session.add(note)
        session.commit()
        session.refresh(note)
        return note

    raise HTTPException(detail="User not found", status_code=404)


@app.get('/view_notes', response_model=list[NoteBase])
def view_notes(user: Annotated[UserDB, Depends(get_logged_user)]):
    if user is not None:
        return user.notes

    raise HTTPException(detail="User not found", status_code=404)


@app.patch('/update_note/{note_id}')
def update_note(note_id: int, user: Annotated[UserDB, Depends(get_logged_user)], note_u: NoteUpdate,
                session: SessionDep):
    notes = user.notes
    try:
        note_update = None
        for note in notes:
            if note.idx == note_id:
                note_update = note
                break

        if note_u.title is not None:
            note_update.title = note_u.title

        if note_u.content is not None:
            note_update.content = note_u.content

        session.add(note_update)
        session.commit()
        session.refresh(note_update)

        return note_update

    except AttributeError:
        raise HTTPException(detail="Invalid note id", status_code=404)


@app.delete('/remove_note/{note_id}')
def remove_note(note_id: int, user: Annotated[UserDB, Depends(get_logged_user)], session: SessionDep):
    try:
        note_delete = None
        for note in user.notes:
            if note.idx == note_id:
                note_delete = note
                break

        session.delete(note_delete)
        session.commit()
        return {'successful_delete': True}

    except Exception as e:
        raise HTTPException(detail='Invalid note id', status_code=404)


# App routes
@app.get('/lgin')
def login_test(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})


@app.get('/')
def home_page(request: Request):
    return templates.TemplateResponse('home.html', {'request': request})
