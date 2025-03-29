from sqlmodel import select, create_engine, SQLModel, Session, select


sqlite_file_name = 'database.db'
sqlite_url = f'sqlite:///{sqlite_file_name}'
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_all():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
