"""
Instagram Profile Scraper
Uses httpx with proxy fallback to bypass Instagram IP blocks.
Falls back to instaloader for data processing.
"""

import os
import json
import time
import re
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
    """
    Scrapes public Instagram profiles using a two-strategy approach:
    1. Try instaloader (fast, structured)
    2. If blocked, use curl/requests with proxy fallback
    """

    def __init__(self):
        self.session_cookies = self._get_session_cookies()

    def _get_session_cookies(self):
        """Get Instagram session cookies from environment."""
        return {
            "sessionid": os.environ.get("IG_SESSIONID", ""),
            "csrftoken": os.environ.get("IG_CSRFTOKEN", ""),
            "ds_user_id": os.environ.get("IG_DS_USER_ID", ""),
        }

    def fetch_profile(self, username: str, max_posts: int = 30) -> Optional[ProfileData]:
        """Fetch a public Instagram profile using multiple strategies."""

        # Strategy 1: Try instaloader (works when not IP-blocked)
        result = self._try_instaloader(username, max_posts)
        if result is not None:
            return result

        # Strategy 2: Try via curl with Instagram's web API
        result = self._try_web_scrape(username, max_posts)
        if result is not None:
            return result

        # Strategy 3: If both fail, raise helpful error
        raise Exception(
            "Instagram is blocking requests from this server. "
            "This is common on cloud hosting (Railway/Render/etc). "
            "To fix this, you have two options:\n\n"
            "Option A (Easy): Provide Instagram session cookies\n"
            "  1. Log into Instagram in Chrome\n"
            "  2. Press F12 → Application → Cookies → instagram.com\n"
            "  3. Copy 'sessionid', 'csrftoken', 'ds_user_id' values\n"
            "  4. Set them as Railway env vars: IG_SESSIONID, IG_CSRFTOKEN, IG_DS_USER_ID\n\n"
            "Option B: Use a proxy service like ScraperAPI, Bright Data, or Oxylabs\n"
            "  Set SCRAPER_API_KEY env var with your ScraperAPI key for automatic proxy rotation."
        )

    def _try_instaloader(self, username: str, max_posts: int) -> Optional[ProfileData]:
        """Strategy 1: Use instaloader library."""
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
                max_connection_attempts=2,
            )

            # Apply session cookies if available
            if self.session_cookies["sessionid"]:
                loader.context._session.cookies.set(
                    "sessionid", self.session_cookies["sessionid"], domain=".instagram.com"
                )
                loader.context._session.cookies.set(
                    "csrftoken", self.session_cookies["csrftoken"], domain=".instagram.com"
                )
                loader.context.is_logged_in = True

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
            print(f"[Instaloader failed] {str(e)[:100]}")
            return None  # Fall through to strategy 2

    def _try_web_scrape(self, username: str, max_posts: int) -> Optional[ProfileData]:
        """Strategy 2: Scrape Instagram's public web API using curl."""
        try:
            # Use curl to fetch the profile page
            cookies_str = ""
            if self.session_cookies["sessionid"]:
                cookies_str = (
                    f'--cookie "sessionid={self.session_cookies["sessionid"]}; '
                    f'csrftoken={self.session_cookies["csrftoken"]}"'
                )

            # Try via ScraperAPI if key is available
            scraper_key = os.environ.get("SCRAPER_API_KEY", "")

            if scraper_key:
                # Route through ScraperAPI (free tier: 1000 requests/month)
                url = (
                    f"http://api.scraperapi.com?api_key={scraper_key}"
                    f"&url=https://www.instagram.com/{username}/?__a=1&__d=dis"
                )
            else:
                url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"

            cmd = [
                "curl", "-s", "-L",
                "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "-H", "Accept-Language: en-US,en;q=0.5",
                "--connect-timeout", "15",
                "--max-time", "30",
            ]

            if cookies_str:
                cmd.extend(cookies_str.split())

            cmd.append(url)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)

            if result.returncode != 0 or not result.stdout.strip():
                print(f"[Web scrape] curl failed or empty response")
                return None

            # Try to parse JSON from the response
            data = self._extract_json_from_html(result.stdout, username)
            if data:
                return self._parse_instagram_data(data, max_posts)

            print(f"[Web scrape] Could not extract data from response")
            return None

        except subprocess.TimeoutExpired:
            print("[Web scrape] Timeout")
            return None
        except Exception as e:
            print(f"[Web scrape] Error: {str(e)[:100]}")
            return None

    def _extract_json_from_html(self, html: str, username: str) -> Optional[dict]:
        """Extract Instagram's shared data from HTML."""
        # Look for the _sharedData JSON blob
        patterns = [
            r'window\._sharedData\s*=\s*({.+?});</script>',
            r'"user":\s*({[^}]*"username"\s*:\s*"' + re.escape(username) + r'"[^}]*})',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        # Try to find any JSON-LD or structured data
        if '"@type":"Person"' in html or '"@type":"ProfilePage"' in html:
            match = re.search(r'<script type="application/ld\+json">(.+?)</script>', html, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        return None

    def _parse_instagram_data(self, data: dict, max_posts: int) -> Optional[ProfileData]:
        """Parse Instagram's JSON response into ProfileData."""
        try:
            # Navigate the sharedData structure
            user_data = None

            if "entry_data" in data:
                # Old format
                profile_page = data["entry_data"].get("ProfilePage", [{}])[0]
                user_data = profile_page.get("graphql", {}).get("user", {})
            elif "user" in data:
                user_data = data["user"]
            elif "graphql" in data:
                user_data = data["graphql"].get("user", {})

            if not user_data:
                # Try alternative paths
                user_data = data.get("user", data)

            if not user_data or "username" not in str(user_data):
                return None

            # Extract profile info
            followers = 0
            following = 0
            if "edge_followed_by" in user_data:
                followers = user_data["edge_followed_by"].get("count", 0)
            elif "follower_count" in user_data:
                followers = user_data.get("follower_count", 0)

            if "edge_follow" in user_data:
                following = user_data["edge_follow"].get("count", 0)
            elif "following_count" in user_data:
                following = user_data.get("following_count", 0)

            # Extract posts
            posts = []
            media_edges = []
            if "edge_owner_to_timeline_media" in user_data:
                media_edges = user_data["edge_owner_to_timeline_media"].get("edges", [])
            elif "media" in user_data and "nodes" in user_data["media"]:
                media_edges = [{"node": n} for n in user_data["media"]["nodes"]]

            count = 0
            for edge in media_edges:
                if count >= max_posts:
                    break
                node = edge.get("node", edge)
                if not node:
                    continue

                # Get caption
                caption = ""
                if "edge_media_to_caption" in node:
                    edges = node["edge_media_to_caption"].get("edges", [])
                    if edges:
                        caption = edges[0].get("node", {}).get("text", "")
                elif "caption" in node:
                    caption = node.get("caption", "")

                # Determine type
                is_video = node.get("is_video", False)
                typename = node.get("typename", "")
                if typename == "GraphSidecar":
                    media_type, is_carousel = "carousel", True
                elif is_video:
                    media_type, is_carousel = "video", True
                else:
                    media_type, is_carousel = "image", False

                # Date
                timestamp = node.get("taken_at_timestamp", 0)
                date_str = ""
                if timestamp:
                    from datetime import datetime
                    date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

                shortcode = node.get("shortcode", "")
                hashtags = [w for w in caption.split() if w.startswith("#")]
                mentions = [w for w in caption.split() if w.startswith("@")]

                posts.append(PostData(
                    shortcode=shortcode,
                    caption=caption,
                    likes=node.get("edge_media_preview_like", {}).get("count", node.get("likes", {}).get("count", 0)),
                    comments=node.get("edge_media_to_comment", {}).get("count", node.get("comments", {}).get("count", 0)),
                    date=date_str,
                    is_video=is_video,
                    is_carousel=is_carousel,
                    media_type=media_type,
                    url=f"https://instagram.com/p/{shortcode}" if shortcode else "",
                    thumbnail_url=node.get("display_url", ""),
                    hashtags=hashtags,
                    mentions=mentions,
                ))
                count += 1

            # Profile picture
            profile_pic = user_data.get("profile_pic_url_hd", user_data.get("profile_pic_url", ""))

            return ProfileData(
                username=user_data.get("username", ""),
                full_name=user_data.get("full_name", ""),
                bio=user_data.get("biography", user_data.get("bio", "")),
                followers=followers,
                following=following,
                post_count=user_data.get("edge_owner_to_timeline_media", {}).get("count", user_data.get("media_count", 0)),
                is_verified=user_data.get("is_verified", False),
                is_business=user_data.get("is_business_account", False),
                is_private=user_data.get("is_private", False),
                profile_pic_url=profile_pic,
                external_url=user_data.get("external_url", ""),
                posts=posts,
            )

        except Exception as e:
            print(f"[Parse error] {str(e)[:100]}")
            return None
