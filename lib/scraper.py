"""
Instagram Profile Scraper
Uses Instaloader to fetch public profile data and recent posts.
Handles Instagram rate-limiting and blocks via session-based auth.
"""

import instaloader
from dataclasses import dataclass, field
from typing import Optional
import time
import os
import requests


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
            max_connection_attempts=3,
        )
        self._try_login()

    def _try_login(self):
        """Try to load session from environment or session file."""
        session_file = os.path.join(os.path.dirname(__file__), "..", "session.json")
        
        # Check for Instagram session cookies in env
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

        # Try loading from session file
        if os.path.exists(session_file):
            try:
                self.loader.load_session_from_file("viscom", session_file)
                print("[Scraper] Loaded session from file")
                return
            except Exception as e:
                print(f"[Scraper] Session file load failed: {e}")

        print("[Scraper] No session — scraping as anonymous (may be blocked by Instagram)")

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
                time.sleep(0.5)  # Rate limiting

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
            if "403" in str(e) or "login" in str(e).lower():
                raise Exception(
                    "Instagram is blocking this request. This usually happens when scraping from a server IP. "
                    "To fix this, set environment variables IG_SESSIONID, IG_CSRFTOKEN, and IG_DS_USER_ID "
                    "with your Instagram login session cookies. See the README for instructions."
                )
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg:
                raise Exception(
                    "Instagram blocked the request (403). Server IPs are often blocked by Instagram. "
                    "Solution: Set IG_SESSIONID, IG_CSRFTOKEN, IG_DS_USER_ID environment variables in Railway. "
                    "You can get these from your browser's cookies after logging into Instagram."
                )
            raise Exception(f"Scraping error: {error_msg}")
