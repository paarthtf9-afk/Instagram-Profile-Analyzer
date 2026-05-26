"""
Instagram Profile Scraper
Uses Instaloader to fetch public profile data and recent posts.
"""

import instaloader
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class PostData:
    shortcode: str
    caption: str
    likes: int
    comments: int
    date: str
    is_video: bool
    is_carousel: bool
    media_type: str  # "image", "video", "carousel"
    url: str
    thumbnail_url: str = ""
    hashtags: list = field(default_factory=list)
    mentions: list = field(default_factory=list)


@dataclass
class ProfileData:
    username: str
    full_name: str
    bio: str
    followers: int
    following: int
    post_count: int
    is_verified: bool
    is_business: bool
    is_private: bool
    profile_pic_url: str
    external_url: str
    posts: list = field(default_factory=list)


class InstagramScraper:
    def __init__(self):
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
        )

    def fetch_profile(self, username: str, max_posts: int = 30) -> Optional[ProfileData]:
        """Fetch a public Instagram profile and recent posts."""
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)

            posts = []
            count = 0
            for post in profile.get_posts():
                if count >= max_posts:
                    break

                # Determine media type
                if post.typename == "GraphSidecar":
                    media_type = "carousel"
                    is_carousel = True
                    is_video = False
                elif post.is_video:
                    media_type = "video"
                    is_video = True
                    is_carousel = False
                else:
                    media_type = "image"
                    is_video = False
                    is_carousel = False

                # Extract hashtags and mentions from caption
                caption_text = post.caption or ""
                hashtags = [w for w in caption_text.split() if w.startswith("#")]
                mentions = [w for w in caption_text.split() if w.startswith("@")]

                post_data = PostData(
                    shortcode=post.shortcode,
                    caption=caption_text,
                    likes=post.likes,
                    comments=post.comments,
                    date=post.date_utc.strftime("%Y-%m-%d %H:%M"),
                    is_video=is_video,
                    is_carousel=is_carousel,
                    media_type=media_type,
                    url=f"https://instagram.com/p/{post.shortcode}",
                    thumbnail_url=post.url,
                    hashtags=hashtags,
                    mentions=mentions,
                )
                posts.append(post_data)
                count += 1
                time.sleep(0.3)  # Rate limiting

            profile_data = ProfileData(
                username=profile.username,
                full_name=profile.full_name or "",
                bio=profile.biography or "",
                followers=profile.followers,
                following=profile.followees,
                post_count=profile.mediacount,
                is_verified=profile.is_verified,
                is_business=profile.is_business_account,
                is_private=profile.is_private,
                profile_pic_url=profile.profile_pic_url,
                external_url=profile.external_url or "",
                posts=posts,
            )
            return profile_data

        except instaloader.exceptions.ProfileNotExistsException:
            return None
        except instaloader.exceptions.ConnectionException as e:
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Scraping error: {str(e)}")
