import os
from datetime import datetime, timedelta, timezone

import dotenv
import httpx
import humanize

from VALORANT import VALORANTAPI
from VALORANT.auth import UserCredentialFlow

dotenv.load_dotenv()

# Configuration load

USERNAME = os.getenv("VAL_USERNAME")
PASSWORD = os.getenv("VAL_PASSWORD")
REGION = os.getenv("VAL_REGION")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

assert USERNAME, "VAL_USERNAME is not set"
assert PASSWORD, "VAL_PASSWORD is not set"
assert REGION, "VAL_REGION is not set"
assert DISCORD_WEBHOOK, "DISCORD_WEBHOOK is not set"

# Declaring constants

HTTP_404_IMAGE = "https://http.cat/404"
WEBHOOK_USERNAME = "Jett"
WEBHOOK_AVATAR_URL = "https://images6.alphacoders.com/121/1211496.png"
SKIN_ITEM_UUID = "e7c63390-eda7-46e0-bb7a-a6abdacd2433"

# Declaring constants that are not strings

currencies = {
    "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741": "VP",
}
now = datetime.now(timezone.utc)
base_embed = {
    "timestamp": now.isoformat(),
    "color": 0xEB459E,
}

session = httpx.Client(
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    }
)
auth = UserCredentialFlow(
    session,
    USERNAME,
    PASSWORD,
)
api = VALORANTAPI(auth, region=REGION)

# Loading data and their utility functions

skins_data = session.get(
    "https://valorant-api.com/v1/weapons/skinlevels/",
).json()["data"]
bundles_data = session.get("https://valorant-api.com/v1/bundles/").json()["data"]


def get_item(item_uuid: str, items: list):
    for item in items:
        if item["uuid"] == item_uuid:
            return item

    return {}


def get_skin(skin_uuid: str):
    return get_item(skin_uuid, skins_data)


def get_bundle(bundle_uuid: str):
    return get_item(bundle_uuid, bundles_data)


def get_currency_string(cost: dict):
    return ", ".join(
        f"`{price}` **{currencies[currency]}**" for currency, price in cost.items()
    )


def get_expires(expires_in: datetime, now: datetime = now):
    return f"Expires {humanize.naturaltime(expires_in, when=now)} ({now.strftime('%Y-%m-%d %H:%M:%S')} {now.tzname()} time)"


store = api.get_storefront()
embeds = []


skins_panel = store["SkinsPanelLayout"]["SingleItemStoreOffers"]


if skins_panel:

    embed = base_embed.copy()

    embed["title"] = "DAILY SHOP"

    skins = ()

    for skin in skins_panel:
        data = get_skin(skin["OfferID"])
        cost = skin["Cost"]

        skins += (
            "- "
            f"[{data['displayName']}]({data['displayIcon'] or HTTP_404_IMAGE}), cost: {get_currency_string(cost)}",
        )

    embed["description"] = "\n".join(skins)

    embeds.append(embed)

bundle_panel = store["FeaturedBundle"]

if bundle_panel:

    for bundle in store["FeaturedBundle"]["Bundles"]:

        embed = base_embed.copy()

        data = get_bundle(bundle["DataAssetID"])

        expires_in = datetime.now(timezone.utc) + timedelta(
            seconds=bundle["DurationRemainingInSeconds"]
        )

        if bundle["TotalDiscountedCost"]:
            price_string = f"{get_currency_string(bundle['TotalDiscountedCost'])} ~~{get_currency_string(bundle['TotalBaseCost'])}~~ (-**{bundle['TotalDiscountPercent'] * 100}**%)"
        else:
            price_string = get_currency_string(bundle["TotalBaseCost"])

        embed["title"] = f"BUNDLE // {data['displayName']}"
        embed["fields"] = [
            {
                "name": "Cost",
                "value": price_string,
                "inline": True,
            }
        ]
        embed["image"] = {"url": data["displayIcon"] or HTTP_404_IMAGE}
        embed["thumbnail"] = {"url": data["verticalPromoImage"] or HTTP_404_IMAGE}

        skins = (
            "> *Please note that the following listing is exclusive of anything other than skins in the bundle.*\n",
        )

        for item in bundle["Items"]:
            # We're only going to care about skins

            if item["Item"]["ItemTypeID"] != SKIN_ITEM_UUID:
                continue

            cost = {item["CurrencyID"]: item["BasePrice"]}

            data = get_skin(item["Item"]["ItemID"])

            skins += (
                "- "
                f"[{data['displayName']}]({data['displayIcon'] or HTTP_404_IMAGE}), individual cost: {get_currency_string(cost)}",
            )

        embed["description"] = "\n".join(skins)

        embed["footer"] = {
            "text": get_expires(
                expires_in,
            )
        }

        embeds.append(embed)

night_market = store["BonusStore"]

if night_market:
    offers = night_market["BonusStoreOffers"]
    expires_in = datetime.now(timezone.utc) + timedelta(
        seconds=night_market["BonusStoreRemainingDurationInSeconds"]
    )

    embed = base_embed.copy()

    embed["title"] = "NIGHT MARKET"

    skins = ()

    for offer in offers:
        skin_offer = offer["Offer"]
        data = get_skin(skin_offer["OfferID"])

        if offer["DiscountCosts"]:
            price_string = f"{get_currency_string(offer['DiscountCosts'])} ~~{get_currency_string(skin_offer['Cost'])}~~ (-**{offer['DiscountPercent']}**%)"
        else:
            price_string = get_currency_string(offer["Cost"])

        full_string = f"[{data['displayName']}]({data['displayIcon'] or HTTP_404_IMAGE}), cost: {price_string}"

        if not offer["IsSeen"]:
            full_string = f"||{full_string}||"

        skins += ("- " + full_string,)

    embed["description"] = "\n".join(skins)
    embed["footer"] = {"text": get_expires(expires_in)}
    embeds.append(embed)

if embeds:

    name_service = api.get_name_service()[0]
    loadout = api.get_player_loadout()

    embed = base_embed.copy()

    embed["title"] = f"{name_service['GameName']}#{name_service['TagLine']}"
    embed["image"] = {
        "url": f'https://media.valorant-api.com/playercards/{loadout["Identity"]["PlayerCardID"]}/wideart.png'
    }

    embeds.insert(0, embed)

    session.post(
        DISCORD_WEBHOOK,
        json={
            "embeds": embeds,
            "username": WEBHOOK_USERNAME,
            "avatar_url": WEBHOOK_AVATAR_URL,
        },
    )
