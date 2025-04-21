import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from functools import cached_property
from typing import Annotated, List, Optional

from pydantic import AfterValidator, BaseModel, HttpUrl, computed_field
from pydantic_extra_types.color import Color

from ..core.config import settings
from ..utils import unescape

UnescapedString = Annotated[str, AfterValidator(unescape)]


class PodcastMetadata(BaseModel):
    gift: bool
    gift_all: bool
    pushnotification: bool
    chronological: int
    order: int
    robot: str
    sponsored: bool
    cyclicality: str
    evidenza: str
    cyclicalitytype: str
    background_color: Color


class Podcast(BaseModel):
    """IlPost Podcast model."""

    id: int
    author: str
    description: str
    title: str
    image: HttpUrl
    image_web: HttpUrl
    object: str
    count: Optional[int] = None
    slug: str
    meta: PodcastMetadata
    access_level: str

    def __eq__(self, other: "Podcast") -> bool:
        """Compare two podcasts by their ID."""
        if not isinstance(other, Podcast):
            return NotImplemented
        return self.slug == other.slug


class PodcastEpisode(BaseModel):
    """IlPost Podcast episode model."""

    id: int
    author: str
    title: UnescapedString
    # click: Optional[str] = None
    summary: Optional[str] = None
    content_html: str
    image: HttpUrl
    image_web: HttpUrl
    object: str
    milliseconds: int
    minutes: int
    special: bool
    share_url: HttpUrl
    slug: str
    full_slug: str
    url: HttpUrl
    episode_raw_url: HttpUrl
    date: datetime
    # timestamp: Optional[int] = None
    access_level: str
    parent: Podcast

    @computed_field
    @property
    def guid(self) -> str:
        """Return the episode GUID."""
        return str(uuid.uuid5(uuid.NAMESPACE_URL, str(self.id)))

    @computed_field
    @property
    def number(self) -> Optional[int | str]:
        slug_parts = self.slug.split("-")
        if slug_parts[0] == "ep":
            return int(slug_parts[1])
        elif slug_parts[:2] == ["morning", "weekend"]:
            return "Weekend"
        else:
            return None

    @computed_field
    @cached_property
    def seconds(self) -> int:
        """Return the duration in seconds."""
        td = timedelta(milliseconds=self.milliseconds)

        # Convert timedelta to total seconds
        total_seconds = int(td.total_seconds())
        return total_seconds

    @computed_field
    @cached_property
    def duration(self) -> str:
        """Return the duration in HH:MM:SS format."""

        # Calculate hours, minutes, and seconds
        hours = self.seconds // 3600
        minutes = (self.seconds % 3600) // 60
        seconds = self.seconds % 60

        formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return formatted_time

    def to_rss_item(self) -> ET.Element:
        """Convert the episode to an RSS item."""
        item = ET.Element("item")
        ET.SubElement(item, "title").text = self.title
        ET.SubElement(item, "description").text = self.content_html or ""
        ET.SubElement(item, "itunes:summary").text = self.content_html or ""

        # Publication date in RSS format
        if self.date:
            ET.SubElement(item, "pubDate").text = self.date.strftime(
                "%a, %d %b %Y %H:%M:%S %z"
            )

        ET.SubElement(item, "guid", isPermaLink="false").text = self.guid
        ET.SubElement(item, "itunes:duration").text = self.duration or "00:00:00"

        # Add enclosure if audio URL is available
        if self.url:
            ET.SubElement(
                item,
                "enclosure",
                url=str(self.episode_raw_url),
                type="audio/mpeg",
                length="0",
            )

        # Add link to episode
        if self.url:
            ET.SubElement(item, "link").text = str(self.url)

        return item


class PodcastFeed(Podcast):
    """IlPost Podcast to represent an RSS feed."""

    episodes: List[PodcastEpisode] = []

    @property
    def sorted_episodes(self) -> List[PodcastEpisode]:
        """Return the episodes sorted by date. (newest first)."""
        return sorted(self.episodes, key=lambda e: e.date, reverse=True)

    def add_episode(self, episode: PodcastEpisode):
        """Add an episode to the feed."""
        self.episodes.append(episode)

    def to_rss(self) -> ET.Element:
        """Convert the podcast feed to an RSS XML element."""
        rss = ET.Element(
            "rss",
            version="2.0",
            **{
                "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
                "xmlns:content": "http://purl.org/rss/1.0/modules/content/",
                "xmlns:atom": "http://www.w3.org/2005/Atom",
            },
        )
        channel = ET.SubElement(rss, "channel")

        # Add a self-reference atom:link for podcatchers
        ET.SubElement(
            channel,
            "atom:link",
            href=str(self.image),
            rel="self",
            type="application/rss+xml",
        )

        # Add podcast metadata
        ET.SubElement(channel, "title").text = self.title
        ET.SubElement(channel, "link").text = str(self.image)
        ET.SubElement(channel, "description").text = self.description
        ET.SubElement(channel, "language").text = settings.FEED_LANGUAGE
        ET.SubElement(channel, "itunes:author").text = self.author
        ET.SubElement(channel, "itunes:subtitle").text = self.description
        ET.SubElement(channel, "itunes:summary").text = self.description
        ET.SubElement(channel, "itunes:explicit").text = "no"
        ET.SubElement(channel, "itunes:image", href=str(self.image))

        # Add each episode to the channel
        for episode in self.sorted_episodes:
            channel.append(episode.to_rss_item())

        return rss

    def to_rss_string(self) -> str:
        """Convert the podcast feed to an RSS XML string."""
        rss = self.to_rss()

        # Generate prettified XML string with declaration
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        ET.indent(rss, space="\t", level=0)
        rss_string = xml_declaration + ET.tostring(
            rss, encoding="unicode", method="xml"
        )
        return rss_string
