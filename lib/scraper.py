"""
Instagram Profile Scraper
Uses instaloader with authenticated session to bypass Instagram blocks.
"""

import os
import json
import time
import subprocess
from dataclasses import dataclass, field
from typing import Optional


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
        self.session_cookies = {
            "sessionid": os.environ.get("IG_SESSIONID", ""),
            "csrftoken": os.environ.get("IG_CSRFTOKEN", ""),
            "ds_user_id": os.environ.get("IG_DS_USER_ID", ""),
        }

    def fetch_profile(self, username: str, max_posts: int = 30) -> Optional[ProfileData]:
        """Fetch a public Instagram profile using instaloader."""

        try:
            import instaloader

            loader = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
                max_connection_attempts=3,
            )

            # Apply session cookies
            if self.session_cookies["sessionid"] and self.session_cookies["csrftoken"]:
                session = loader.context._session
                session.cookies.set("sessionid", self.session_cookies["sessionid"], domain=".instagram.com")
                session.cookies.set("csrftoken", self.session_cookies["csrftoken"], domain=".instagram.com")
                if self.session_cookies["ds_user_id"]:
                    session.cookies.set("ds_user_id", self.session_cookies["ds_user_id"], domain=".instagram.com")
                loader.context.is_logged_in = True
                print("[Scraper] Using authenticated session")
            else:
                print("[Scraper] No session cookies — trying anonymous (may fail)")

            profile = instaloader.Profile.from_username(loader.context, username)

            posts = []
            count = 0
            for post in profile.get_posts():
                if count >= max_posts:
                    break

                if post.typename == "GraphSidecar":
                    media_type, is_video, is_carousel = "carousel", False, True
                elif post.is_video:
                    media_type, is_video, is_carousel = "video", True, False
                else:
                    media_type, is_video, is_carousel = "image", False, False

                caption_text = post.caption or ""
                hashtags = [w for w in caption_text.split() if w.startswith("#")]
                mentions = [w for w in caption_text.split() if w.startswith("@")]

                posts.append(PostData(
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
                ))
                count += 1
                time.sleep(0.3)

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
        except Exception as e:
            error_str = str(e)
            # Check if it's an IP block
            is_blocked = any(phrase in error_str.lower() for phrase in [
                "403", "login", "redirect", "blocked", "unauthorized",
                "please wait", "challenge", "checkpoint"
            ])

            if is_blocked or not self.session_cookies["sessionid"]:
                raise Exception(
                    "INSTAGRAM_BLOCKED: Instagram is blocking this server's IP address.\n\n"
                    "This is a common issue on cloud platforms (Railway, Render, etc.).\n\n"
                    "TO FIX — Set these 3 environment variables in Railway:\n\n"
                    "  IG_SESSIONID  — from your Instagram browser cookies\n"
                    "  IG_CSRFTOKEN  — from your Instagram browser cookies\n"
                    "  IG_DS_USER_ID — from your Instagram browser cookies\n\n"
                    "How to get them (30 seconds):\n"
                    "  1. Open Chrome → instagram.com → log in\n"
                    "  2. Press F12 → Application tab → Cookies → https://www.instagram.com\n"
                    "  3. Find and copy: sessionid, csrftoken, ds_user_id\n"
                    "  4. Go to Railway → Project → Variables → add them\n"
                    "  5. Redeploy\n\n"
                    "Alternatively, use a free ScraperAPI account at scraperapi.com\n"
                    "and set SCRAPER_API_KEY environment variable."
                )

            if "not exist" in error_str.lower():
                return None

            raise Exception(f"Scraping error: {error_str}")
