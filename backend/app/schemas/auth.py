from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=1)


class UserProfile(BaseModel):
    user_id: int
    username: str
    full_name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
