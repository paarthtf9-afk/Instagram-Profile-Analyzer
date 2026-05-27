"""
Instagram Profile Scraper
Uses Instaloader with fallback to requests-based scraping for better reliability.
"""

import instaloader
from dataclasses import dataclass, field
from typing import Optional
import time
import os
import json
import re


@dataclass
class PostData:
    shortcode: str
    caption: str
    likes: int
    comments: int
    date: str
    is_video: bool
    is_carousel: bool
    media_type: str
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
            max_connection_attempts=2,
        )
        self._try_login()

    def _try_login(self):
        """Try to load session from environment variables."""
        ig_sessionid = os.environ.get("IG_SESSIONID", "")
        ig_csrf = os.environ.get("IG_CSRFTOKEN", "")
        ig_ds_user = os.environ.get("IG_DS_USER_ID", "")

        if ig_sessionid and ig_csrf:
            try:
                self.loader.context._session.cookies.set("sessionid", ig_sessionid, domain=".instagram.com")
                self.loader.context._session.cookies.set("csrftoken", ig_csrf, domain=".instagram.com")
                if ig_ds_user:
                    self.loader.context._session.cookies.set("ds_user_id", ig_ds_user, domain=".instagram.com")
                self.loader.context.is_logged_in = True
                print("[Scraper] Using session cookies from env")
                return
            except Exception as e:
                print(f"[Scraper] Session cookie setup failed: {e}")

        print("[Scraper] No session — scraping as anonymous")

    def fetch_profile(self, username: str, max_posts: int = 30) -> Optional[ProfileData]:
        """Fetch a public Instagram profile and recent posts."""
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)

            posts = []
            count = 0
            for post in profile.get_posts():
                if count >= max_posts:
                    break

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
                time.sleep(0.5)

            return ProfileData(
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

        except instaloader.exceptions.ProfileNotExistsException:
            return None
        except instaloader.exceptions.ConnectionException as e:
            error_str = str(e)
            if "403" in error_str or "login" in error_str.lower():
                raise Exception(
                    "Instagram is blocking this request from the server. "
                    "To fix: set IG_SESSIONID, IG_CSRFTOKEN, IG_DS_USER_ID environment variables in Railway. "
                    "Get these from your browser cookies at instagram.com (F12 → Application → Cookies)."
                )
            raise Exception(f"Connection error: {error_str}")
        except Exception as e:
            error_str = str(e)
            if "403" in error_str:
                raise Exception(
                    "Instagram blocked the request (403). Server IPs are often blocked. "
                    "Set IG_SESSIONID, IG_CSRFTOKEN, IG_DS_USER_ID in Railway environment variables."
                )
            if "not exist" in error_str.lower() or "unable to find" in error_str.lower():
                return None
            raise Exception(f"Scraping error: {error_str}")
