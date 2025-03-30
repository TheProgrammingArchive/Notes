from sqlmodel import SQLModel, Field, Relationship, Column, JSON, ForeignKey
from typing import Union, Optional

class NoteBase(SQLModel):
    title: Union[str, None] = Field(max_length=100, index=True, default=None)
    content: Union[str, None] = Field(max_length=1000)


class Notes(NoteBase, table=True):
    idx: Union[int, None] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="userdb.id")
    user: Optional["UserDB"] = Relationship(back_populates="notes")


class NoteUpdate(NoteBase):
    title: Union[str, None] = None
    content: Union[str, None] = None


class UserBase(SQLModel):
    username: str = Field(max_length=50, index=True)
    full_name: Union[str, None] = Field(default=None)
    age: Union[int, None] = Field(default=None, index=True)


class UserDB(UserBase, table=True):
    encrypted_pwd: str = Field(default=None)
    id: Union[int, None] = Field(default=None, primary_key=True)

    notes: Union[None, list[Notes]] = Relationship(back_populates="user")

class UserCreate(UserBase):
    encrypted_pwd: str = Field()
