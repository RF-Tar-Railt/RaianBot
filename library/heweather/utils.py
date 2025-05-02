from time import time

from jwt import encode

from .model import ConfigError, QWeatherConfig


def get_jwt_token(config: QWeatherConfig):
    if not (config.jwt_sub and config.jwt_kid and config.jwt_private_key):
        raise ConfigError(
            "请检查是否遗漏了 QWEATHER_JWT_SUB " "QWEATHER_JWT_KID QWEATHER_JWT_PRIVATE_KEY " "中的其中一项"
        )

    payload = {
        "iat": int(time()) - 30,
        "exp": int(time()) + 900,
        "sub": config.jwt_sub,
    }
    headers = {
        "kid": config.jwt_kid,
        "alg": "EdDSA",
    }

    encoded_jwt = encode(
        payload,
        key=config.jwt_private_key,
        algorithm="EdDSA",
        headers=headers,
    )
    return encoded_jwt
