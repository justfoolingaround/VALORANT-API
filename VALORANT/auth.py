import re
import time

from .constants import (
    AUTHENTICATION_ENDPOINT,
    AUTHENTICATION_URL,
    ENTITLEMENTS_AUTHENTICATION_URL,
)

AUTHENTICATION_RESPONSE_REGEX = re.compile(
    r"access_token=(?P<access_token>.+?)&scope=(?P<scope>.+?)&iss=(?P<iss>.+?)&id_token=(?P<id_token>.+?)&token_type=(?P<token_type>.+?)&session_state=(?P<session_state>.+?)&expires_in=(?P<expires_in>\d+)"
)


class BaseAuthenticationFlow:
    def load(self) -> None:
        raise NotImplementedError()

    @property
    def has_expired(self) -> bool:
        raise NotImplementedError()

    @property
    def token(self) -> str:
        raise NotImplementedError()


class UserCredentialFlow(BaseAuthenticationFlow):
    def __init__(self, session, username, password):

        self.session = session
        self.username = username
        self.password = password

        self.payload = {}

    def load(self):

        if not self.has_expired:
            return

        headers = {
            "Referer": AUTHENTICATION_URL + "login",
        }

        self.session.post(
            AUTHENTICATION_ENDPOINT,
            json={
                "client_id": "play-valorant-web-prod",
                "nonce": "1",
                "redirect_uri": "https://playvalorant.com/opt_in",
                "response_type": "token id_token",
            },
            headers=headers,
        )

        auth_response = self.session.put(
            AUTHENTICATION_ENDPOINT,
            json={
                "type": "auth",
                "username": self.username,
                "password": self.password,
            },
            headers=headers,
        )

        authentication_url = (
            auth_response.json().get("response", {}).get("parameters", {}).get("uri")
        )

        created_at = time.time()
        match = AUTHENTICATION_RESPONSE_REGEX.search(authentication_url)

        payload = {**match.groupdict(), "created_at": created_at}

        self.payload = payload

        return

    @property
    def has_expired(self):
        return time.time() - self.payload.get("created_at", 0) > int(
            self.payload.get("expires_in", 0)
        )

    @property
    def token(self):
        self.load()
        return f'{self.payload.get("token_type")} {self.payload.get("access_token")}'


class EntitlementToken:
    def __init__(self, auth: BaseAuthenticationFlow):

        self.auth = auth
        self.payload = {}

    def load(self):

        if not self.payload:
            self.payload = self.auth.session.post(
                ENTITLEMENTS_AUTHENTICATION_URL + "api/token/v1",
                headers={"Authorization": self.auth.token},
                json={},
            ).json()

    @property
    def token(self):
        self.load()
        return self.payload.get("entitlements_token")
