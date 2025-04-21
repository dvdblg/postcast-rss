from typing import Optional

import requests

from ..models.user import IlPostUser, IlPostUserMetadata
from ..utils import build_url
from .config import settings
from .exceptions import PodcastException


def get_auth_token(subscription_cache: Optional[IlPostUserMetadata]) -> str:
    """
    Get the authentication token for the API.
    """
    if subscription_cache is None or subscription_cache.subscription.is_expired:
        # Simulate fetching subscription data
        response = requests.post(
            build_url(
                settings.ILPOST_API_BASE_URL,
                settings.ILPOST_API_ROUTE_USERS,
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
            user = IlPostUser.model_validate(data)
            subscription_cache = user.profile.meta
        except (requests.HTTPError, ValueError) as e:
            raise PodcastException("Failed to fetch subscription data from API") from e
    return subscription_cache.token
