import os
from typing import AsyncIterator, Dict, List, Optional, overload

import aiohttp
import requests

from ..models.podcast import Podcast, PodcastEpisode
from ..models.user import IlPostUser, IlPostUserMetadata, IlPostUserSubscription
from ..utils import build_url
from ..utils.logging import setup_logging
from .config import settings
from .exceptions import PodcastException

LOG = setup_logging(__name__)


def read_subscription_cache() -> Optional[IlPostUserMetadata]:
    """Read the subscription cache from the file."""
    # Make sure the directory exists
    settings.ILPOST_SUBSCRIPTION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.ILPOST_SUBSCRIPTION_CACHE_FILE, "r") as f:
        return IlPostUserMetadata.model_validate_json(f.read())


def write_subscription_cache(subscription_cache: IlPostUserMetadata):
    """Write the subscription cache to the file."""
    # Make sure the directory exists
    settings.ILPOST_SUBSCRIPTION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.ILPOST_SUBSCRIPTION_CACHE_FILE, "w") as f:
        f.write(subscription_cache.model_dump_json(indent=4))


class IlPostApi:
    """Client for interacting with Il Post API.

    Provides methods to authenticate and retrieve podcast information.
    """

    BASE_URL = settings.ILPOST_API_BASE_URL
    ROUTE_PODCASTS = settings.ILPOST_API_ROUTE_PODCASTS
    ROUTE_USERS = settings.ILPOST_API_ROUTE_USERS

    def __init__(self):
        self._subscription_cache: Optional[IlPostUserMetadata] = None
        self._podcasts: Dict[str, Podcast] = {}
        self.user: Optional[IlPostUser] = None

    def __str__(self) -> str:
        return f"IlPostApi(token=****, subscribed={self.subscribed})"

    @property
    def subscription(self) -> IlPostUserSubscription | None:
        """Get the subscription cache."""
        return (
            self._subscription_cache.subscription if self._subscription_cache else None
        )

    @property
    def is_expired(self) -> bool:
        """Check if the subscription is expired."""
        return self.subscription.is_expired if self.subscription else True

    @property
    async def podcasts(self) -> Dict[str, Podcast]:
        """Get the podcasts cache."""
        if not self._podcasts or len(self._podcasts) == 0:
            podcasts = await self.get_podcasts()
            for podcast in podcasts:
                self._podcasts[podcast.slug] = podcast
        return self._podcasts

    async def get_podcasts(self, top_n: Optional[int] = None) -> List[Podcast]:
        """
        Get the podcasts from the API.
        """
        podcasts = [p async for p in self.recursive_podcast_get(hits=top_n)]
        return list(podcasts)

    def login(self):
        """
        Authenticate with the API and fetch the subscription data.
        """
        try:
            self._subscription_cache = read_subscription_cache()
            if self._subscription_cache.subscription is None:
                raise PodcastException("No subscription data found in cache")
            elif self._subscription_cache.subscription.is_expired:
                os.remove(settings.ILPOST_SUBSCRIPTION_CACHE_FILE_NAME)
                raise PodcastException("Cached subscription expired")
            LOG.info("Found valid subscription cache, using it.")
        except (FileNotFoundError, ValueError, PodcastException):
            LOG.info("No valid subscription cache found, logging in.")
            response = requests.post(
                build_url(
                    self.BASE_URL,
                    self.ROUTE_USERS,
                    "auth",
                    "login",
                ),
                json={
                    "username": settings.ILPOST_USERNAME.get_secret_value(),
                    "password": settings.ILPOST_PASSWORD.get_secret_value(),
                },
            )
            try:
                response.raise_for_status()
                data = response.json()
                self.user = IlPostUser.model_validate(data)
                self._subscription_cache = self.user.profile.meta
                LOG.info("Logged in successfully.")
                write_subscription_cache(self._subscription_cache)
            except (requests.HTTPError, ValueError) as e:
                raise PodcastException(
                    "Failed to fetch subscription data from API"
                ) from e

        if self.is_expired:
            LOG.warning("Subscription expired. Only free content will be accessible.")
        else:
            msg = "Subscription is active"
            if self.subscription.end_date:
                msg += (
                    f" until {self.subscription.end_date.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            elif self.subscription.next_payment:
                msg += f" until {self.subscription.next_payment.strftime('%Y-%m-%d %H:%M:%S')}"
            LOG.info(msg)

    @property
    def auth_token(self) -> str:
        """
        Get the authentication token for the API.
        """
        if self.user is None or self._subscription_cache is None:
            self.login()
        return self._subscription_cache.token.get_secret_value()

    @overload
    async def recursive_podcast_get(
        self,
        podcast: None = None,
        page: int = 1,
        counter: int = 0,
        hits: Optional[int] = None,
    ) -> AsyncIterator[Podcast]:
        """Get all podcasts from the API."""
        ...

    @overload
    async def recursive_podcast_get(
        self,
        podcast: str,
        page: int = 1,
        counter: int = 0,
        hits: Optional[int] = None,
    ) -> AsyncIterator[PodcastEpisode]:
        """Get all episodes for a given podcast from the API."""
        ...

    async def recursive_podcast_get(
        self,
        podcast: Optional[str] = None,
        page: int = 1,
        counter: int = 0,
        hits: Optional[int] = None,
    ) -> AsyncIterator[Podcast | PodcastEpisode]:
        """
        Recursive function to get all podcasts from the API.
        """
        url = build_url(self.BASE_URL, self.ROUTE_PODCASTS, podcast)
        ret_class = Podcast if podcast is None else PodcastEpisode
        page_size = hits or 200

        # Set the headers for the request
        async with aiohttp.ClientSession(headers={"token": self.auth_token}) as session:
            async with session.get(
                url, params={"hits": page_size, "pg": page}
            ) as response:
                if response.status != 200:
                    raise PodcastException(
                        f"Failed to fetch data from API: {response.status} {response.reason}",
                        response.status,
                    )
                try:
                    response_data = await response.json()
                    head = response_data["head"]["data"]
                    data = response_data["data"]
                    total_items = head["total"]

                    for item in data:
                        yield ret_class.model_validate(item)
                        counter += 1

                        # Stop if we've reached the requested hit limit
                        if hits is not None and counter >= hits:
                            return

                    # If there are more episodes to fetch and we haven't reached the limit
                    if counter < total_items and (hits is None or counter < hits):
                        async for episode in self.recursive_podcast_get(
                            podcast=podcast,
                            page=page + 1,
                            counter=counter,
                            hits=hits,
                        ):
                            yield episode
                except (KeyError, ValueError) as e:
                    raise PodcastException("Failed to parse response from API") from e
