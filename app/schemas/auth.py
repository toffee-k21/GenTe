# app/schemas/auth.py

from pydantic import BaseModel, EmailStr


class UserRegisterSchema(BaseModel):

    email: EmailStr
    password: str


class UserLoginSchema(BaseModel):

    email: EmailStr
    password: str


class TokenSchema(BaseModel):

    access_token: str
    token_type: str = "bearer"
    email: str