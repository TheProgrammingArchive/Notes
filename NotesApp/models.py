from sqlmodel import SQLModel, Field, Relationship, Column, JSON, ForeignKey
from typing import Union, Optional
import datetime


class NoteBase(SQLModel):
    title: Union[str, None] = Field(max_length=100, index=True, default=None)
    content: Union[str, None] = Field(max_length=1000)


class Notes(NoteBase, table=True):
    idx: Union[int, None] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="userdb.id")
    user: Optional["UserDB"] = Relationship(back_populates="notes")

    created_at: Union[str, None] = Field(default_factory=lambda: datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p'))


class Friend(SQLModel, table=True):
    origin_id: Optional[int] = Field(default=None, foreign_key="userdb.id", primary_key=True)
    target_id: Optional[int] = Field(default=None, primary_key=True)
    origin_user: Optional["UserDB"] = Relationship(back_populates="friends")


class UserBase(SQLModel):
    username: str = Field(max_length=50, index=True)
    email: Union[str, None] = Field(default=None)


class UserDB(UserBase, table=True):
    encrypted_pwd: str = Field(default=None)
    id: Union[int, None] = Field(default=None, primary_key=True)
    friends: Union[None, list[Friend]] = Relationship(back_populates="origin_user")

    notes: Union[None, list[Notes]] = Relationship(back_populates="user")


class UserCreate(UserBase):
    encrypted_pwd: str = Field()
