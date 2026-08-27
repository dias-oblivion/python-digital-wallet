"""Pydantic da BORDA: só entra e sai daqui. O service recebe e devolve tipos de domínio."""

from pydantic import BaseModel, EmailStr, Field, SecretStr

from models.token import TokenPair
from services.auth import MIN_PASSWORD_LENGTH


class RegisterRequest(BaseModel):
    email: EmailStr
    # min_length vem da constante do service: a borda dá 422 amigável, e a regra continua
    # valendo independente de quem chama — sem risco de os dois limites divergirem
    password: SecretStr = Field(min_length=MIN_PASSWORD_LENGTH)
    full_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenResponse":
        return cls(access_token=pair.access_token, refresh_token=pair.refresh_token)
