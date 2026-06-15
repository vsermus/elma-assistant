from pydantic import BaseModel
from typing import List, Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserInfo(BaseModel):
    username: str
    is_admin: bool

class ObjectInfo(BaseModel):
    id: str
    name: str
    address: str

class ObjectSearchResult(BaseModel):
    objects: List[ObjectInfo]

class CorpusInfo(BaseModel):
    name: str

class CorpusList(BaseModel):
    korpuses: List[str]

class GenerateRequest(BaseModel):
    object_id: str
    korpuses: Optional[List[str]] = None
    section: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class GenerateResponse(BaseModel):
    filename: str
    object_name: str
    object_id: str
    korpuses: List[str]
    vitrage_count: int
    period: str
