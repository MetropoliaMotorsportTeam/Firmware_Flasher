import tomllib
from dataclasses import dataclass, fields


@dataclass
class FlashConfig:
    backend: str | None
    port: str | None
    baud: int | None
    retries: int | None
    timeout_ms: int | None
    firmware_path: str | None


def load_config_file(path: str) -> FlashConfig:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return FlashConfig(**{field.name: data.get(field.name) for field in fields(FlashConfig)})


def merge_configs(file_config: FlashConfig, cli_config: FlashConfig) -> FlashConfig:
    merged = {}
    for field in fields(FlashConfig):
        cli_value = getattr(cli_config, field.name)
        file_value = getattr(file_config, field.name)
        merged[field.name] = cli_value if cli_value is not None else file_value
    return FlashConfig(**merged)
