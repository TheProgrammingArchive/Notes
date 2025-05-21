import sqlite3

from fastapi import FastAPI, Depends, status, Request, Form
from fastapi.templating import Jinja2Templates
from typing import Union, Annotated
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from fastapi.exceptions import HTTPException
from .models import UserBase, UserDB, Notes, UserCreate, NoteBase, Friend
from .crud import create_all, get_session
from sqlmodel import select, Session
from .security import get_logged_user, OAuth2PasswordRequestForm, authenticate_user, create_access_token, encrypt_pwd, \
    cookie_scheme

app = FastAPI()


@app.on_event('startup')
def startup():
    create_all()


SessionDep = Annotated[Session, Depends(get_session)]
templates = Jinja2Templates(directory="templates")


@app.exception_handler(HTTPException)
def handle_http_exception(request: Request, exc: HTTPException):
    print(exc)
    if exc.detail == "Username already exists or Form was filled in-correctly":
        return templates.TemplateResponse('register.html', {'request': request, 'detail': exc.detail},
                                          status_code=exc.status_code)

    elif exc.detail == 'Could not validate credentials':
        return templates.TemplateResponse('login.html', {'request': request},
                                          status_code=exc.status_code)

    elif exc.detail == 'Username is too long':
        return templates.TemplateResponse('register.html', {'request': request, 'detail': exc.detail})

    elif exc.detail == 'Invalid note id':
        return templates.TemplateResponse('home.html', {'request': request, 'detail': 'Requested note ID is invalid',
                                                        'is_logged': 'TRUE'})

    elif exc.detail == 'Already added as friend' or exc.detail == 'User not found':
        return RedirectResponse('/manage_friends', status_code=303)

    else:
        return templates.TemplateResponse('login.html', {'request': request, 'detail': exc.detail})


def validate_username(username: str, session: SessionDep):
    users = session.exec(select(UserDB)).all()
    for user in users:
        if user.username == username:
            return False

    return True


def get_note_id(note_id: int, user: UserDB) -> (int, Notes):
    if user.notes is None:
        return None

    for k, note in enumerate(user.notes):
        if note.idx == note_id:
            return k, note

    return None



def is_send_allowed(target_user: UserDB, origin_user: UserDB) -> bool:
    allow = False
    for friends in target_user.friends:
        if friends.target_id == origin_user.id:
            allow = True
            break

    return allow



@app.post('/create_user', response_model=UserBase)
def create_user(username: Annotated[str, Form()], encrypted_pwd: Annotated[str, Form()],
                email: Annotated[str, Form()], session: SessionDep):
    if not validate_username(username, session):
        raise HTTPException(detail="Username already exists or Form was filled in-correctly", status_code=404)

    encrypted_pwd = encrypt_pwd(encrypted_pwd)
    user = UserDB.model_validate({'username': username, 'encrypted_pwd': encrypted_pwd,
                                  'email': email})
    session.add(user)
    session.commit()
    session.refresh(user)

    return RedirectResponse(url='/login', status_code=303)


@app.post('/login_')
def login_page(data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    user = authenticate_user(data.username, data.password, session=session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({'sub': user.username})
    redirect_response = RedirectResponse(url='/', status_code=303)
    redirect_response.set_cookie(key='access_token', value=access_token, httponly=True)

    return redirect_response


@app.post('/create_note', response_model=NoteBase)
def create_note(title: Annotated[str, Form()], content: Annotated[Union[str, None], Form()],
                user: Annotated[UserDB, Depends(get_logged_user)], session: SessionDep):
    if user is not None:
        note = {'title': title, 'content': content}

        if len(title) > 50 or (content is not None and len(content) > 1000):
            return RedirectResponse(url='/', status_code=303)

        note = Notes.model_validate(note)
        note.user_id = user.id

        user.notes.append(note)
        session.add(note)
        session.commit()
        session.refresh(note)

        return RedirectResponse(url=f'/notes/{note.idx}', status_code=303)

    raise HTTPException(detail="Not authenticated yet", status_code=404)


@app.get('/view_notes', response_model=list[Notes])
def view_notes(user: Annotated[UserDB, Depends(get_logged_user)]):
    if user is not None:
        return user.notes

    raise HTTPException(detail="User not found", status_code=404)


@app.post('/update_note_/{note_id}')
def update_note_(note_id: int, user: Annotated[UserDB, Depends(get_logged_user)],
                 title: Annotated[str, Form()], content: Annotated[str, Form()], session: SessionDep):
    if user is not None:
        data = get_note_id(note_id, user)
        if data is None:
            raise HTTPException(detail="Invalid note id", status_code=404)

        index, note_update = data
        if title is not None and len(title) <= 50:
            note_update.title = title
        else:
            return RedirectResponse(url='/', status_code=303)

        if note_update.content is not None and len(note_update.content) <= 1000:
            note_update.content = content
        else:
            raise HTTPException(detail="Invalid note, title or content might have been too long", status_code=404)

        session.add(note_update)
        session.commit()
        session.refresh(note_update)

        return RedirectResponse(url=f'/notes/{note_id}', status_code=303)

    raise HTTPException(detail='Could not validate credentials', status_code=404)


# Note sharing
@app.post('/add_friend')
def add_friend(friend_username: Annotated[str, Form()], user: Annotated[UserDB, Depends(get_logged_user)], session: SessionDep):
    friend = session.exec(select(UserDB).where(UserDB.username == friend_username)).first()
    if user is not None and friend is not None and friend is not user:
        relation = Friend(origin_id=user.id, target_id=friend.id, origin_user=user)
        try:
            user.friends.append(relation)
            session.add(relation)
            session.commit()
            session.refresh(relation)

        except Exception:
            raise HTTPException(detail='Already added as friend', status_code=404)

        return RedirectResponse('/add_friend')

    raise HTTPException(detail='User not found', status_code=404)


@app.post('/remove_friend/{friend_username}')
def remove_friend(user: Annotated[UserDB, Depends(get_logged_user)], friend_username: str, session: SessionDep):
    friend_id = session.exec(select(UserDB).where(UserDB.username == friend_username)).first().id
    for friend in user.friends:
        if friend.target_id == friend_id:
            user.friends.remove(friend)
            session.delete(friend)
            session.commit()

            return RedirectResponse('/manage_friends', status_code=303)

    return None


@app.get('/send_note')
def send_note(user: Annotated[UserDB, Depends(get_logged_user)], target: str, note_id: int, session: SessionDep):
    target_user = session.exec(select(UserDB).where(UserDB.username == target)).first()
    if target_user is not None and is_send_allowed(target_user=target_user, origin_user=user):
        note_to_send = get_note_id(note_id, user)

        if note_to_send is None:
            return 'Inaccessible note'

        note_to_send = note_to_send[1]
        copied_note = {'title': note_to_send.title, 'content': note_to_send.content, 'user_id': target_user.id, 'user': target_user, 'shared': user.username}
        copied_note = Notes.model_validate(copied_note)

        target_user.notes.append(copied_note)
        session.add(copied_note)
        session.commit()
        session.refresh(copied_note)

        return RedirectResponse(f'notes/{note_id}')

    return 'You are not allowed to send notes to that user, as you are not part of their friends list'


# App routes
@app.get('/update_note/{note_id}')
def update_note(request: Request, note_id: int, user: Annotated[UserDB, Depends(get_logged_user)]):
    k, note = get_note_id(note_id, user)
    if user:
        return templates.TemplateResponse('update_note.html', {'request': request, 'note': note})

    return None


@app.get('/new_note')
def new_note(request: Request, user: Annotated[UserDB, Depends(get_logged_user)]):
    if user:
        return templates.TemplateResponse('new_note.html', {'request': request})

    return None

@app.get('/remove_note/{note_id}')
def remove_note(note_id: int, user: Annotated[UserDB, Depends(get_logged_user)], session: SessionDep):
    data = get_note_id(note_id, user)

    if data is not None:
        index, note_delete = data
        user.notes.pop(index)
        session.delete(note_delete)
        session.commit()
        return RedirectResponse(url='/')

    raise HTTPException(detail='Invalid note id', status_code=404)


@app.get('/notes/{note_id}')
def get_note(request: Request, note_id: int, user: Annotated[UserDB, Depends(get_logged_user)]):
    note = None
    for notes in user.notes:
        if notes.idx == note_id:
            note = notes
            break

    if note is None:
        raise HTTPException(detail="Invalid note id", status_code=404)

    return templates.TemplateResponse('note.html', {'request': request, 'note': note})


@app.get('/login')
def login(request: Request, token: Annotated[str, Depends(cookie_scheme)], session: SessionDep):
    try:
        get_logged_user(token, session)
        return RedirectResponse(url='/')

    except HTTPException:
        return templates.TemplateResponse('login.html', {'request': request})


@app.get('/register')
def register(request: Request, token: Annotated[str, Depends(cookie_scheme)], session: SessionDep):
    try:
        get_logged_user(token, session)
        return RedirectResponse(url='/')

    except HTTPException:
        return templates.TemplateResponse('register.html', {'request': request})


@app.get('/logout')
def logout():
    response = RedirectResponse('/login')
    response.delete_cookie(key='access_token')
    return response


@app.get('/', response_model=list[Notes])
def home_page(request: Request, user: Annotated[UserDB, Depends(get_logged_user)]):
    return templates.TemplateResponse('home.html', {'request': request, 'notes': user.notes, 'is_logged': 'TRUE'})


@app.get('/manage_friends')
def manage_friends(request: Request, user: Annotated[UserDB, Depends(get_logged_user)], session: SessionDep):
    friends = []
    for friend in user.friends:
        friend_details = session.exec(select(UserDB).where(UserDB.id == friend.target_id)).first()
        friends.append({'username': friend_details.username, 'email': friend_details.email})


    return templates.TemplateResponse('friends.html', {'request': request, 'friends': friends})


# Testing methods
@app.get('/view_friends', response_model=list[Friend])
def view_friends(user: Annotated[UserDB, Depends(get_logged_user)]):
    return user.friends


@app.get('/view_all/', response_model=list[UserDB])
def view_all(session: SessionDep):
    items = session.exec(select(UserDB)).all()
    return items
