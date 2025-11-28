from pydantic import BaseModel, ConfigDict
from typing import List


class SeqeraResource(BaseModel):
    """Base class for all Seqera Platform resources"""

    model_config = ConfigDict(
        extra="ignore", populate_by_name=True, use_enum_values=True
    )

    def dump_dict(self) -> dict:
        """For dumping - includes all fields even if None"""
        return self.model_dump(by_alias=True, exclude_none=False)

    def input_dict(self) -> dict:
        """For input processing - excludes None values"""
        return self.model_dump(by_alias=True, exclude_none=True)

    def to_cli_args(self) -> List[str]:
        """
        Convert Pydantic model to CLI arguments list.

        Returns a list of CLI arguments in the format:
        ["--field-name", "value", "--flag", ...]

        Override this method in subclasses for custom CLI argument generation
        (e.g., for positional args or special handling).
        """
        args = []
        data = self.input_dict()

        for key, value in data.items():
            if isinstance(value, bool):
                # Only add boolean flags if True
                if value:
                    args.append(f"--{key}")
            elif isinstance(value, list):
                # Handle list values (e.g., instance-types: ["t3.large", "t3.xlarge"])
                # Convert to comma-separated string
                args.extend([f"--{key}", ",".join(str(v) for v in value)])
            elif value is not None:
                # Standard key-value pair
                args.extend([f"--{key}", str(value)])

        return args
