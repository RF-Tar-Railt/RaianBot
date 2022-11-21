from pydantic import BaseModel, Field


class Config(BaseModel):
    max: int = Field(default=200)
    """信赖最大值"""


SignConfig = Config
