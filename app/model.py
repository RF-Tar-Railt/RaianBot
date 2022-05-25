from typing import List, Dict, Any
from pydantic import BaseModel, Field


class GroupProfile(BaseModel):
    id: int
    disabled: List[str] = Field(default_factory=list)
    in_blacklist: bool = Field(default=False)
    additional: Dict[str, Any] = Field(default_factory=dict)
    # weibo_followers: List[str]


class UserProfile(BaseModel):
    id: int
    trust: int = Field(default=0)
    interact_count: int = Field(default=0)
    additional: Dict[str, Any] = Field(default_factory=dict)
    # draw_info: List[Union[str, int]]
