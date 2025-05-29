from pydantic import BaseModel

class SeqeraResource(BaseModel):
    """Base class for all Seqera Platform resources"""
    class Config:
        extra = "ignore"
        populate_by_alias = True
