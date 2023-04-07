import base64
import sys
from functools import cached_property

import orjson

from .auth import BaseAuthenticationFlow, EntitlementToken
from .constants import AUTHENTICATION_URL


class VALORANTAPI:
    def __init__(self, auth_flow: BaseAuthenticationFlow, *, region: str = "ap"):
        self.auth_flow = auth_flow
        self.region = region

        self.entitlement_token = EntitlementToken(auth_flow)

    def user_headers(
        self, entitlements_jwt=False, client_version=False, client_platform=False
    ):
        headers = {
            "Authorization": self.auth_flow.token,
        }

        if entitlements_jwt:
            headers["X-Riot-Entitlements-JWT"] = self.entitlement_token.token

        if client_version:
            headers["X-Riot-ClientVersion"] = self.client_version

        if client_platform:
            headers["X-Riot-ClientPlatform"] = self.client_platform

        return headers

    @property
    def production_endpoint(self) -> str:
        return f"https://pd.{self.region}.a.pvp.net"

    @cached_property
    def client_platform(self) -> str:
        is_64bit = sys.maxsize > 2**32

        if sys.platform == "win32":
            os_version = sys.getwindowsversion()
            version = f"{os_version.major}.{os_version.minor}.{os_version.build}.{os_version.platform}.256.{'64Bit' if is_64bit else '32Bit'}"
        else:
            version = "10.0.22621.2.256.64bit"

        return base64.b64encode(
            orjson.dumps(
                {
                    "platformType": "PC",
                    "platformOS": "Windows",
                    "platformOSVersion": version,
                    "platformChipset": "Unknown",
                }
            )
        )

    @cached_property
    def client_version(self) -> str:
        data = self.auth_flow.session.get("https://valorant-api.com/v1/version")
        return data.json()["data"]["riotClientVersion"]

    @cached_property
    def user_id(self):
        return self.auth_flow.session.post(
            AUTHENTICATION_URL + "userinfo",
            headers=self.user_headers(),
        ).json()["sub"]

    def get_penalties(self):
        return self.auth_flow.session.get(
            f"{self.production_endpoint}/restrictions/v3/penalties",
            headers=self.user_headers(entitlements_jwt=True),
        ).json()

    def get_name_service(self, player_ids: "list[str]" = None):
        return self.auth_flow.session.put(
            f"{self.production_endpoint}/name-service/v2/players",
            headers=self.user_headers(),
            json=player_ids or [self.user_id],
        ).json()

    def get_storefront(self, user_id: str = None):

        return self.auth_flow.session.get(
            f"{self.production_endpoint}/store/v2/storefront/{user_id or self.user_id}",
            headers=self.user_headers(entitlements_jwt=True),
        ).json()

    def get_offers(self):
        return self.auth_flow.session.get(
            f"{self.production_endpoint}/store/v1/offers/",
            headers=self.user_headers(entitlements_jwt=True),
        ).json()

    def get_player_loadout(self):
        return self.auth_flow.session.get(
            f"{self.production_endpoint}/personalization/v2/players/{self.user_id}/playerloadout",
            headers=self.user_headers(entitlements_jwt=True),
        ).json()

    def iter_match_history(
        self,
        player_id: str = None,
        start_index: int = 0,
        end_index: "int | None" = None,
    ):

        total = end_index
        current_end = (
            min(start_index + 20, end_index)
            if end_index is not None
            else start_index + 20
        )

        while (total is None) or (start_index < total):

            data = self.auth_flow.session.get(
                f"{self.production_endpoint}/match-history/v1/history/{player_id or self.user_id}",
                params={
                    "startIndex": start_index,
                    "endIndex": current_end,
                },
                headers=self.user_headers(entitlements_jwt=True),
            ).json()

            total = data["Total"] if end_index is None else end_index
            start_index += 20
            current_end = (
                min(start_index + 20, end_index)
                if end_index is not None
                else start_index + 20
            )

            yield from data["History"]

    def get_match_details(self, match_id: str):
        return self.auth_flow.session.get(
            f"{self.production_endpoint}/match-details/v1/matches/{match_id}",
            headers=self.user_headers(entitlements_jwt=True),
        ).json()

    def get_player_mmr(self, player_id: str = None):
        return self.auth_flow.session.get(
            f"{self.production_endpoint}/mmr/v1/players/{player_id or self.user_id}",
            headers=self.user_headers(
                entitlements_jwt=True, client_platform=True, client_version=True
            ),
        ).json()

    def get_player_mmr_updates(self, player_id: str = None):
        return self.auth_flow.session.get(
            f"{self.production_endpoint}/mmr/v1/players/{player_id or self.user_id}/competitiveupdates",
            headers=self.user_headers(
                entitlements_jwt=True, client_platform=True, client_version=True
            ),
        ).json()

    def get_player_contracts(self, player_id: str = None):
        return self.auth_flow.session.get(
            f"{self.production_endpoint}/contracts/v1/contracts/{player_id or self.user_id}",
            headers=self.user_headers(
                entitlements_jwt=True, client_platform=True, client_version=True
            ),
        ).json()

    def get_player_wallet(self, player_id: str = None):
        return self.auth_flow.session.get(
            f"{self.production_endpoint}/store/v1/wallet/{player_id or self.user_id}",
            headers=self.user_headers(entitlements_jwt=True),
        ).json()
