from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ...core.bridge import IlPostApi
from ...core.config import settings
from ...models.podcast import Podcast, PodcastEpisode, PodcastFeed
from ...utils.logging import setup_logging

LOG = setup_logging(__name__)

BASE_URL = settings.ILPOST_API_BASE_URL
ROUTE_PODCASTS = settings.ILPOST_API_ROUTE_PODCASTS

ilpost_api: IlPostApi = None


@asynccontextmanager
async def lifespan(router: APIRouter):
    """
    Lifespan context manager for the router.
    """
    global ilpost_api, async_engine

    # Initialize the ilpost API client
    ilpost_api = IlPostApi()
    LOG.info("IlPost API client initialized")
    ilpost_api.login()

    yield
    # Cleanup code can be added here if needed


router = APIRouter(
    prefix="/podcasts",
    tags=["podcasts"],
    lifespan=lifespan,
)


@router.get("/")
async def list_podcasts(
    top_n: Optional[int] = None,
) -> List[Podcast]:
    """
    List all podcasts
    """
    try:
        # Check if the subscription is expired
        if ilpost_api.is_expired:
            raise HTTPException(status_code=401, detail="Subscription expired")

        podcasts = await ilpost_api.get_podcasts(top_n=top_n)
        if len(podcasts) == 0:
            raise HTTPException(status_code=404, detail="No podcasts found")

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{slug}")
async def list_episodes(slug: str, top_n: Optional[int] = None) -> List[PodcastEpisode]:
    """
    List all episodes for a given podcast
    """
    try:
        # Check if the podcast exists
        podcasts = await ilpost_api.podcasts
        podcast_info = podcasts.get(slug, None)
        if podcast_info is None:
            raise HTTPException(status_code=404, detail="Podcast not found")

        episodes = []
        async for episode in ilpost_api.recursive_podcast_get(podcast=slug, hits=top_n):
            episodes.append(episode)

        return episodes

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{slug}/latest")
async def get_latest_episodes(
    slug: str,
) -> PodcastEpisode:
    """
    Get the latest episodes for a given podcast
    """
    try:
        # Check if the podcast exists
        podcasts = await ilpost_api.podcasts
        podcast_info = podcasts.get(slug, None)
        if podcast_info is None:
            raise HTTPException(status_code=404, detail="Podcast not found")

        latest_episode = await anext(
            ilpost_api.recursive_podcast_get(podcast=slug, hits=1)
        )
        return latest_episode

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{slug}/rss")
async def get_rss_feed(
    slug: str,
    complete: bool = False,
) -> Response:
    """
    This endpoint builds and returns the RSS feed for a given podcast.
    """
    # First get podcast info
    podcasts = await ilpost_api.podcasts
    podcast_info = podcasts.get(slug, None)

    if podcast_info is None:
        raise HTTPException(status_code=404, detail="Podcast not found")

    feed = PodcastFeed.model_validate(podcast_info.model_dump())

    # Get episodes
    async for episode in ilpost_api.recursive_podcast_get(
        podcast=slug, hits=None if complete else 20
    ):
        feed.add_episode(episode)

    if len(feed.episodes) == 0:
        raise HTTPException(status_code=404, detail="No episodes found")

    return Response(content=feed.to_rss_string(), media_type="application/rss+xml")


@router.get("/{slug}/rss-complete")
async def get_rss_feed_complete(
    slug: str,
) -> Response:
    """
    This endpoint builds and returns the RSS feed for a given podcast.
    """
    # First get podcast info
    podcasts = await ilpost_api.podcasts
    podcast_info = podcasts.get(slug, None)

    if podcast_info is None:
        raise HTTPException(status_code=404, detail="Podcast not found")

    feed = PodcastFeed.model_validate(podcast_info.model_dump())

    # Get episodes
    async for episode in ilpost_api.recursive_podcast_get(podcast=slug, hits=None):
        feed.add_episode(episode)

    if len(feed.episodes) == 0:
        raise HTTPException(status_code=404, detail="No episodes found")

    return Response(content=feed.to_rss_string(), media_type="application/rss+xml")
