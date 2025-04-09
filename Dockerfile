FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./NotesApp /code/NotesApp

WORKDIR /code/NotesApp

CMD ["fastapi", "run", "main.py", "--port", "80"]