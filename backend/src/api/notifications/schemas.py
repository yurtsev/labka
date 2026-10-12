from pydantic import BaseModel


class UnreadCountResponse(BaseModel):
    unread_count: int


class ReadAllResponse(BaseModel):
    marked: int
    unread_count: int
