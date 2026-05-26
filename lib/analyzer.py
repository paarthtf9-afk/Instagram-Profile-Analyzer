"""
Instagram Content Analyzer
Processes scraped profile data into actionable insights.
"""

import re
from collections import Counter
from datetime import datetime
from lib.scraper import ProfileData, PostData


class ContentAnalyzer:
    def __init__(self, profile: ProfileData):
        self.profile = profile
        self.posts = profile.posts

    def full_analysis(self) -> dict:
        """Run all analyses and return a complete report."""
        if not self.posts:
            return {"error": "No posts found for analysis."}

        return {
            "profile": self._profile_summary(),
            "engagement": self._engagement_analysis(),
            "content_types": self._content_type_analysis(),
            "hashtags": self._hashtag_analysis(),
            "posting_patterns": self._posting_pattern_analysis(),
            "caption_analysis": self._caption_analysis(),
            "top_bottom_posts": self._top_bottom_posts(),
            "recommendations": self._generate_recommendations(),
        }

    def _profile_summary(self) -> dict:
        return {
            "username": self.profile.username,
            "full_name": self.profile.full_name,
            "bio": self.profile.bio,
            "followers": self.profile.followers,
            "following": self.profile.following,
            "post_count": self.profile.post_count,
            "is_verified": self.profile.is_verified,
            "is_business": self.profile.is_business,
            "profile_pic_url": self.profile.profile_pic_url,
            "external_url": self.profile.external_url,
            "analyzed_posts": len(self.posts),
            "follow_ratio": round(self.profile.followers / max(self.profile.following, 1), 2),
        }

    def _engagement_analysis(self) -> dict:
        total_likes = sum(p.likes for p in self.posts)
        total_comments = sum(p.comments for p in self.posts)
        avg_likes = round(total_likes / len(self.posts), 1)
        avg_comments = round(total_comments / len(self.posts), 1)
        engagement_rate = round(
            ((total_likes + total_comments) / len(self.posts))
            / max(self.profile.followers, 1)
            * 100,
            3,
        )

        # Engagement trend (first half vs second half)
        mid = len(self.posts) // 2
        if mid > 0:
            first_half = self.posts[mid:]  # older posts
            second_half = self.posts[:mid]  # newer posts
            first_eng = sum(p.likes + p.comments for p in first_half) / len(first_half)
            second_eng = sum(p.likes + p.comments for p in second_half) / len(second_half)
            if second_eng > first_eng * 1.1:
                trend = "📈 Growing"
            elif second_eng < first_eng * 0.9:
                trend = "📉 Declining"
            else:
                trend = "➡️ Stable"
        else:
            trend = "N/A"

        # Engagement rate benchmark
        if engagement_rate >= 5:
            benchmark = "Excellent"
        elif engagement_rate >= 3:
            benchmark = "Good"
        elif engagement_rate >= 1:
            benchmark = "Average"
        else:
            benchmark = "Below Average"

        return {
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "engagement_rate": engagement_rate,
            "trend": trend,
            "benchmark": benchmark,
            "likes_over_time": [p.likes for p in reversed(self.posts)],
            "comments_over_time": [p.comments for p in reversed(self.posts)],
            "dates": [p.date[:10] for p in reversed(self.posts)],
        }

    def _content_type_analysis(self) -> dict:
        type_counts = Counter(p.media_type for p in self.posts)
        total = len(self.posts)

        type_engagement = {}
        for ptype in ["image", "video", "carousel"]:
            type_posts = [p for p in self.posts if p.media_type == ptype]
            if type_posts:
                avg_eng = sum(p.likes + p.comments for p in type_posts) / len(type_posts)
                type_engagement[ptype] = {
                    "count": len(type_posts),
                    "percentage": round(len(type_posts) / total * 100, 1),
                    "avg_engagement": round(avg_eng, 1),
                }
            else:
                type_engagement[ptype] = {"count": 0, "percentage": 0, "avg_engagement": 0}

        # Best performing type
        best_type = max(type_engagement, key=lambda k: type_engagement[k]["avg_engagement"])

        return {
            "breakdown": type_engagement,
            "best_type": best_type,
            "total_posts": total,
        }

    def _hashtag_analysis(self) -> dict:
        all_hashtags = []
        hashtag_performance = {}  # hashtag -> list of engagements

        for post in self.posts:
            for tag in post.hashtags:
                tag_lower = tag.lower()
                all_hashtags.append(tag_lower)
                if tag_lower not in hashtag_performance:
                    hashtag_performance[tag_lower] = []
                hashtag_performance[tag_lower].append(post.likes + post.comments)

        # Most used hashtags
        tag_counts = Counter(all_hashtags).most_common(20)

        # Best performing hashtags (min 2 uses)
        tag_avg_eng = {}
        for tag, engagements in hashtag_performance.items():
            if len(engagements) >= 2:
                tag_avg_eng[tag] = round(sum(engagements) / len(engagements), 1)
        best_tags = sorted(tag_avg_eng.items(), key=lambda x: x[1], reverse=True)[:10]

        # Posts with vs without hashtags
        with_tags = [p for p in self.posts if p.hashtags]
        without_tags = [p for p in self.posts if not p.hashtags]
        avg_with = sum(p.likes + p.comments for p in with_tags) / max(len(with_tags), 1)
        avg_without = sum(p.likes + p.comments for p in without_tags) / max(len(without_tags), 1)

        # Hashtag cloud data (for visualization)
        hashtag_cloud = [{"text": tag, "count": count} for tag, count in tag_counts[:30]]

        return {
            "total_unique": len(set(all_hashtags)),
            "avg_per_post": round(len(all_hashtags) / max(len(self.posts), 1), 1),
            "most_used": tag_counts[:15],
            "best_performing": best_tags,
            "hashtag_cloud": hashtag_cloud,
            "with_hashtags_avg_eng": round(avg_with, 1),
            "without_hashtags_avg_eng": round(avg_without, 1),
        }

    def _posting_pattern_analysis(self) -> dict:
        if not self.posts:
            return {}

        # Day of week analysis
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_engagement = {d: [] for d in day_names}
        day_counts = {d: 0 for d in day_names}

        # Hour analysis
        hour_engagement = {h: [] for h in range(24)}

        for post in self.posts:
            try:
                dt = datetime.strptime(post.date[:10], "%Y-%m-%d")
                day = day_names[dt.weekday()]
                day_counts[day] += 1
                day_engagement[day].append(post.likes + post.comments)
            except (ValueError, IndexError):
                pass

            try:
                hour = int(post.date[11:13])
                hour_engagement[hour].append(post.likes + post.comments)
            except (ValueError, IndexError):
                pass

        # Best day
        day_avg = {}
        for day in day_names:
            if day_engagement[day]:
                day_avg[day] = round(sum(day_engagement[day]) / len(day_engagement[day]), 1)
            else:
                day_avg[day] = 0

        best_day = max(day_avg, key=day_avg.get)

        # Best hour
        hour_avg = {}
        for h in range(24):
            if hour_engagement[h]:
                hour_avg[f"{h:02d}:00"] = round(
                    sum(hour_engagement[h]) / len(hour_engagement[h]), 1
                )
            else:
                hour_avg[f"{h:02d}:00"] = 0

        best_hour = max(hour_avg, key=hour_avg.get)

        # Posting frequency
        if len(self.posts) >= 2:
            try:
                dates = sorted([datetime.strptime(p.date[:10], "%Y-%m-%d") for p in self.posts])
                gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
                avg_gap = round(sum(gaps) / len(gaps), 1)
                if avg_gap <= 1:
                    frequency = "Daily"
                elif avg_gap <= 3:
                    frequency = "Every 2-3 days"
                elif avg_gap <= 7:
                    frequency = "Weekly"
                elif avg_gap <= 14:
                    frequency = "Bi-weekly"
                else:
                    frequency = "Sporadic"
            except (ValueError, IndexError):
                avg_gap = 0
                frequency = "Unknown"
        else:
            avg_gap = 0
            frequency = "N/A"

        # Consistency score (0-100)
        if len(self.posts) >= 3 and avg_gap > 0:
            try:
                dates = sorted([datetime.strptime(p.date[:10], "%Y-%m-%d") for p in self.posts])
                gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
                variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
                std_dev = variance ** 0.5
                consistency = max(0, min(100, round(100 - (std_dev / max(avg_gap, 1)) * 50)))
            except (ValueError, IndexError):
                consistency = 50
        else:
            consistency = 50

        return {
            "day_engagement": day_avg,
            "day_counts": day_counts,
            "best_day": best_day,
            "hour_engagement": hour_avg,
            "best_hour": best_hour,
            "frequency": frequency,
            "avg_gap_days": avg_gap,
            "consistency_score": consistency,
        }

    def _caption_analysis(self) -> dict:
        captions = [p.caption for p in self.posts if p.caption]
        if not captions:
            return {"avg_length": 0, "common_words": [], "tone": "N/A"}

        # Average caption length
        avg_length = round(sum(len(c) for c in captions) / len(captions), 0)

        # Word frequency (excluding common stop words and hashtags/mentions)
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "it", "this", "that", "are", "was",
            "be", "has", "have", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "can", "i", "you", "we", "they", "he", "she",
            "my", "your", "our", "their", "not", "so", "if", "all", "just", "more",
            "about", "what", "which", "who", "how", "when", "where", "why", "no",
            "yes", "up", "out", "one", "new", "like", "get", "go", "now", "also",
        }
        words = []
        for caption in captions:
            for word in caption.split():
                clean = re.sub(r"[^a-zA-Z]", "", word).lower()
                if clean and len(clean) > 2 and clean not in stop_words and not clean.startswith("#") and not clean.startswith("@"):
                    words.append(clean)

        common_words = Counter(words).most_common(15)

        # Simple tone detection
        tone_keywords = {
            "Professional": ["business", "company", "team", "growth", "strategy", "results", "client", "service", "solution", "industry"],
            "Inspirational": ["dream", "believe", "inspire", "journey", "passion", "purpose", "vision", "goal", "achieve", "success"],
            "Casual": ["lol", "haha", "omg", "guys", "hey", "cool", "awesome", "fun", "love", "vibes"],
            "Educational": ["learn", "tip", "how", "why", "what", "guide", "tutorial", "step", "know", "understand"],
            "Promotional": ["buy", "shop", "sale", "discount", "offer", "link", "bio", "click", "order", "launch"],
        }

        tone_scores = {}
        all_text = " ".join(captions).lower()
        for tone, keywords in tone_keywords.items():
            score = sum(all_text.count(kw) for kw in keywords)
            tone_scores[tone] = score

        dominant_tone = max(tone_scores, key=tone_scores.get) if max(tone_scores.values()) > 0 else "Neutral"

        return {
            "avg_length": avg_length,
            "common_words": common_words,
            "dominant_tone": dominant_tone,
            "tone_scores": tone_scores,
            "total_captions": len(captions),
        }

    def _top_bottom_posts(self) -> dict:
        sorted_posts = sorted(self.posts, key=lambda p: p.likes + p.comments, reverse=True)

        def post_summary(p: PostData) -> dict:
            return {
                "url": p.url,
                "likes": p.likes,
                "comments": p.comments,
                "total_engagement": p.likes + p.comments,
                "caption_preview": (p.caption[:100] + "...") if p.caption and len(p.caption) > 100 else (p.caption or ""),
                "media_type": p.media_type,
                "date": p.date[:10],
                "hashtags_count": len(p.hashtags),
            }

        return {
            "top_5": [post_summary(p) for p in sorted_posts[:5]],
            "bottom_5": [post_summary(p) for p in sorted_posts[-5:]],
        }

    def _generate_recommendations(self) -> list:
        recs = []
        eng = self._engagement_analysis()
        ct = self._content_type_analysis()
        ht = self._hashtag_analysis()
        pp = self._posting_pattern_analysis()
        ca = self._caption_analysis()

        # Engagement recommendations
        if eng["engagement_rate"] < 2:
            recs.append({
                "type": "warning",
                "title": "Low Engagement Rate",
                "text": f"Engagement rate is {eng['engagement_rate']}% — below average. Focus on stronger CTAs, interactive captions, and Reels to boost interaction.",
            })

        # Content type recommendations
        if ct["best_type"] == "video" and ct["breakdown"]["video"]["percentage"] < 30:
            recs.append({
                "type": "opportunity",
                "title": "Post More Reels",
                "text": f"Videos get the highest engagement but only {ct['breakdown']['video']['percentage']}% of posts are Reels. Increase Reel frequency.",
            })
        elif ct["best_type"] == "carousel" and ct["breakdown"]["carousel"]["percentage"] < 30:
            recs.append({
                "type": "opportunity",
                "title": "Post More Carousels",
                "text": f"Carousels perform best but only {ct['breakdown']['carousel']['percentage']}% of content. Carousels drive saves and shares.",
            })

        # Hashtag recommendations
        if ht["avg_per_post"] < 5:
            recs.append({
                "type": "tip",
                "title": "Use More Hashtags",
                "text": f"Average {ht['avg_per_post']} hashtags per post. Aim for 15-20 relevant hashtags to increase discoverability.",
            })
        elif ht["avg_per_post"] > 25:
            recs.append({
                "type": "tip",
                "title": "Reduce Hashtag Spam",
                "text": f"Average {ht['avg_per_post']} hashtags per post. Over 25 can look spammy. Focus on 15-20 highly relevant ones.",
            })

        # Posting pattern recommendations
        if pp.get("consistency_score", 0) < 50:
            recs.append({
                "type": "warning",
                "title": "Inconsistent Posting",
                "text": f"Consistency score: {pp.get('consistency_score', 0)}/100. A regular posting schedule builds audience trust and algorithm favor.",
            })

        recs.append({
            "type": "info",
            "title": f"Best Time to Post",
            "text": f"Based on this profile's data, the best day is {pp.get('best_day', 'N/A')} and best hour is {pp.get('best_hour', 'N/A')}.",
        })

        # Caption recommendations
        if ca["avg_length"] < 50:
            recs.append({
                "type": "tip",
                "title": "Write Longer Captions",
                "text": f"Average caption is {ca['avg_length']} chars. Longer, story-driven captions increase dwell time and engagement.",
            })

        return recs
