import enum

from pydantic import BaseModel, HttpUrl, computed_field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from sqlmodel import Field


class Protocol(enum.StrEnum):
    HTTP = "http"
    HTTPS = "https"


class SiteManager(BaseModel):
    host: str = Field(default="openwrt-controller.fastapicloud.dev")
    port: int = Field(default=443)
    protocol: Protocol = Field(default=Protocol.HTTPS)

    @computed_field
    @property
    def base_url(self) -> HttpUrl:
        return f"{self.protocol}://{self.host}:{self.port}"


class Configuration(BaseSettings):
    model_config = SettingsConfigDict(yaml_file="config.yml")

    site_manager: SiteManager = Field(default_factory=SiteManager)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )
