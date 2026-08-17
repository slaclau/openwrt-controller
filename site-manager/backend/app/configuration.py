from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class OidcProviderConfig(BaseModel):
    name: str = Field()
    slug: str = Field()
    client_id: str = Field()
    client_secret: str = Field()
    auth_url: HttpUrl | None = Field(default=None)
    token_url: HttpUrl | None = Field(default=None)
    logo_url: HttpUrl | None = Field(default=None)
    wellknown_url: HttpUrl | None = Field(default=None)
    scope: str = Field(default="")


class OidcProvider(BaseModel):
    name: str = Field()
    slug: str = Field()
    logo_url: HttpUrl | None = Field(default=None)


class AuthConfig(BaseModel):
    providers: list[OidcProviderConfig] = Field(default=[])


class FrontendConfig(BaseModel):
    url: HttpUrl = Field(default="http://localhost:8000")


class Config(BaseSettings):
    model_config = SettingsConfigDict(yaml_file="config.yml")

    auth: AuthConfig | None = Field(default_factory=AuthConfig)
    frontend: FrontendConfig | None = Field(default_factory=FrontendConfig)
    database_url: str | None = Field(default=None)

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
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )
