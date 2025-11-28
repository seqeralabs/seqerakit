from pydantic import BaseModel, ConfigDict

class SeqeraResource(BaseModel):
    """Base class for all Seqera Platform resources"""
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        use_enum_values=True
    )

    def dump_dict(self) -> dict:
        """For dumping - includes all fields even if None"""
        return self.model_dump(by_alias=True, exclude_none=False)

    def input_dict(self) -> dict:
        """For input processing - excludes None values"""
        return self.model_dump(by_alias=True, exclude_none=True)
