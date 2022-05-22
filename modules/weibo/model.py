from pydantic import BaseModel


class WeiboProfile(BaseModel):
    id: str
    name: str
    total: int

    @property
    def contain_id(self) -> str:
        return f"107603{self.id}"
