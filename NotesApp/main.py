from fastapi import FastAPI, Depends, status, Request, Form
from fastapi.templating import Jinja2Templates
from typing import Union, Annotated
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from models import UserBase, UserDB, Notes, UserCreate, NoteBase, NoteUpdate
from crud import create_all, get_session
from sqlmodel import select, Session
from security import get_logged_user, OAuth2PasswordRequestForm, authenticate_user, create_access_token, encrypt_pwd

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
        return templates.TemplateResponse('login.html', {'request': request,
                                                         'detail': 'You need to be logged in to access that page'},
                                          status_code=exc.status_code)

    elif exc.detail == 'Invalid Note':
        return RedirectResponse(url='/')

    else:
        return templates.TemplateResponse('login.html', {'request': request, 'detail': exc.detail})


def validate_username(username: str, session: SessionDep):
    users = session.exec(select(UserDB)).all()
    for user in users:
        if user.username == username:
            return False

    return True


@app.post('/create_user', response_model=UserBase)
def create_user(username: Annotated[str, Form()], encrypted_pwd: Annotated[str, Form()], age: Annotated[int, Form()],
                full_name: Annotated[str, Form()], session: SessionDep):
    if not validate_username(username, session):
        raise HTTPException(detail="Username already exists or Form was filled in-correctly", status_code=404)

    encrypted_pwd = encrypt_pwd(encrypted_pwd)
    user = UserDB.model_validate({'username': username, 'encrypted_pwd': encrypted_pwd,
                                  'age': age, 'full_name': full_name})
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


@app.get('/view_all/', response_model=list[UserDB])
def view_all(session: SessionDep):
    items = session.exec(select(UserDB)).all()
    return items


@app.post('/new_note')
def create_note(note: NoteBase, user: Annotated[UserDB, Depends(get_logged_user)], session: SessionDep):
    print(user.full_name)
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


# App routes

@app.get('/remove_note/{note_id}')
def remove_note(note_id: int, user: Annotated[UserDB, Depends(get_logged_user)], session: SessionDep):
    note_delete, index = None, -1
    for k, note in enumerate(user.notes):
        if note.idx == note_id:
            note_delete = note
            index = k
            break

    if note_delete is not None:
        user.notes.pop(index)
        session.delete(note_delete)
        session.commit()
        return RedirectResponse(url='/')

    raise HTTPException(detail='Could not find note to delete', status_code=404)


@app.get('/notes/{note_id}')
def get_note(request: Request, note_id: int, user: Annotated[UserDB, Depends(get_logged_user)]):
    note = None
    for notes in user.notes:
        if notes.idx == note_id:
            note = notes
            break

    if note is None:
        raise HTTPException(detail="Invalid Note", status_code=404)

    return templates.TemplateResponse('note.html', {'request': request, 'note': note})


@app.get('/login')
def login_test(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})


@app.get('/register')
def register(request: Request):
    return templates.TemplateResponse('register.html', {'request': request})


@app.get('/logout')
def logout():
    response = RedirectResponse('/login')
    response.delete_cookie(key='access_token')
    return response


@app.get('/', response_model=list[Notes])
def home_page(request: Request, user: Annotated[UserDB, Depends(get_logged_user)]):
    return templates.TemplateResponse('home.html', {'request': request, 'notes': user.notes, 'is_logged': 'TRUE'})
