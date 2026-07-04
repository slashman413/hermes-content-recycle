#!/usr/bin/env python3
"""
hermes-content-recycle: Auto cross-post YouTube Shorts to other platforms.
Maximizes ROI of existing content by republishing everywhere.
"""
import os, sys, json, csv, random, subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = BASE_DIR / "config.json"

CONTENT_LOG = DATA_DIR / "content_log.json"

# ---------------------------------------------------------------------------
# Product CTAs — UTM-tagged links injected into every cross-post.
# {SRC} is substituted per platform; CAMP is fixed.
# ---------------------------------------------------------------------------
_UTM_CAMP = "hermes-content-recycle"

_SAAS_URL = (
    "https://slashman413.gumroad.com/l/saas-starter"
    "?utm_source={src}&utm_medium=social&utm_campaign=" + _UTM_CAMP
)
_TWSE_URL = (
    "https://slashman413.github.io/twse-backtests/"
    "?utm_source={src}&utm_medium=social&utm_campaign=" + _UTM_CAMP
)


def _cta_block(platform: str, mode: str = "both") -> str:
    """Return a CTA footer string for the given platform.

    mode='both'   — two links (Facebook / Threads / Telegram)
    mode='single' — SaaS Starter only (Twitter/X)
    mode='ig'     — single link line, Instagram style
    """
    src = platform.lower()
    saas = _SAAS_URL.format(src=src)
    twse = _TWSE_URL.format(src=src)

    if mode == "single":
        return f"\n🚀 SaaS Starter Kit → {saas}"
    if mode == "ig":
        return f"\n🔗 {saas}"
    # both
    return (
        f"\n\n---\n"
        f"🚀 SaaS Starter Kit → {saas}\n"
        f"📈 TWSE 量化訊號 → {twse}"
    )


def get_latest_shorts() -> list[dict]:
    """Get latest Shorts from pixabay-shorts-bot output."""
    shorts_dir = Path(__file__).parent.parent.parent / "pixabay-shorts-bot" / "output"
    if not shorts_dir.exists():
        # Fallback: use mock data for testing
        return get_mock_shorts()
    
    results = []
    for f in sorted(shorts_dir.glob("pipeline_result*.json"), reverse=True)[:10]:
        try:
            data = json.loads(f.read_text())
            if data.get("youtube_url"):
                results.append({
                    "url": data["youtube_url"],
                    "video_id": data.get("video_id", ""),
                    "date": data.get("date", f.stat().st_mtime),
                    "title": data.get("title", "Shorts"),
                })
        except Exception:
            pass
    return results


def get_mock_shorts() -> list[dict]:
    """Mock data for development/testing."""
    return [
        {"url": "https://youtu.be/B0LEQORowpM", "video_id": "B0LEQORowpM",
         "date": "2026-06-27", "title": "💭 維克多·弗蘭克 說：當我們無法改變情況時"},
        {"url": "https://youtu.be/xal0OlmLGDw", "video_id": "xal0OlmLGDw",
         "date": "2026-06-27", "title": "💭 榮格 說：了解自己的黑暗"},
    ]


def generate_share_text(shorts: dict) -> dict:
    """Generate platform-specific share text for a Shorts video.

    Each platform's copy ends with a UTM-tagged product CTA so every
    cross-post drives measurable traffic to paid products.
    """
    vid_id = shorts.get("video_id", "")
    url = f"https://youtu.be/{vid_id}"
    title = shorts.get("title", "心靈語錄 Shorts")

    return {
        # X/Twitter: char-limited → one link (SaaS Starter)
        "twitter": (
            f"{title}\n\n{url}\n\n#Shorts #名言語錄 #勵志"
            + _cta_block("twitter", mode="single")
        ),
        # Facebook: long-form → both CTAs
        "facebook": (
            f"{title}\n\n🎬 觀看完整影片：{url}\n\n追蹤更多心靈語錄 👉 https://slashman413.github.io/"
            + _cta_block("facebook", mode="both")
        ),
        # Instagram: "link in bio" style + one link line
        "instagram": (
            f"{title}\n\n點擊 bio 連結觀看完整影片 🎬"
            + _cta_block("instagram", mode="ig")
            + "\n\n#Shorts #名言語錄 #勵志 #心靈雞湯"
        ),
        # Threads: full, includes both CTAs
        "threads": (
            f"{title}\n\n{url}\n\n#Shorts #名言語錄"
            + _cta_block("threads", mode="both")
        ),
        # Telegram: full, includes both CTAs
        "telegram": (
            f"✨ {title}\n\n{url}"
            + _cta_block("telegram", mode="both")
        ),
        # Discord: no UTM CTA (internal community channel, not a public post)
        "discord": f"**✨ {title}**\n{url}",
    }


def generate_schedule_html(shorts_list: list[dict]) -> str:
    """Generate a posting schedule HTML page."""
    cards = ""
    for s in shorts_list:
        texts = generate_share_text(s)
        cards += f"""
        <div class="shorts-card">
            <h3>{s.get('title', 'Shorts')[:40]}...</h3>
            <p class="date">{s.get('date', '')}</p>
            <a href="{s['url']}" target="_blank">觀看影片 →</a>
            <div class="share-texts">
                <div class="platform"><span>🐦 Twitter/X</span><pre>{texts['twitter']}</pre></div>
                <div class="platform"><span>📘 Facebook</span><pre>{texts['facebook']}</pre></div>
                <div class="platform"><span>📸 Instagram</span><pre>{texts['instagram']}</pre></div>
            </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><meta charset="UTF-8"><title>Content Recycle — 跨平台發布排程</title>
<style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family: -apple-system, sans-serif; background:#0f172a; color:#e2e8f0; max-width:900px; margin:auto; padding:20px; }}
    h1 {{ text-align:center; margin:20px 0; }}
    .stats {{ display:flex; gap:20px; justify-content:center; margin:20px 0; }}
    .stat {{ background:#1e293b; padding:15px 25px; border-radius:12px; text-align:center; }}
    .stat .num {{ font-size:2rem; font-weight:bold; color:#3b82f6; }}
    .shorts-card {{ background:#1e293b; border-radius:16px; padding:20px; margin:15px 0; }}
    .shorts-card h3 {{ margin-bottom:5px; }}
    .shorts-card .date {{ color:#64748b; font-size:0.9rem; }}
    .shorts-card a {{ color:#3b82f6; text-decoration:none; }}
    .share-texts {{ margin-top:15px; }}
    .platform {{ margin:10px 0; padding:10px; background:#0f172a; border-radius:8px; }}
    .platform span {{ font-weight:bold; color:#f59e0b; }}
    .platform pre {{ white-space:pre-wrap; font-size:0.85rem; color:#94a3b8; margin-top:5px; }}
    .repost-btn {{ display:inline-block; background:#22c55e; color:#0f172a; padding:8px 20px; border-radius:8px; font-weight:bold; text-decoration:none; }}
</style>
</head>
<body>
    <h1>♻️ Content Recycle</h1>
    <p style="text-align:center;color:#64748b;">將現有 Shorts 自動跨平台發布</p>
    <div class="stats">
        <div class="stat"><div class="num">{len(shorts_list)}</div><div>待發布</div></div>
        <div class="stat"><div class="num">{len(shorts_list) * 4}</div><div>平台貼文</div></div>
    </div>
    {cards}
    <footer style="text-align:center;color:#475569;padding:20px;">
        <p>hermes-content-recycle | 每日自動更新</p>
        <p>🤖 自動發布腳本需各平台 API Token 後啟用</p>
    </footer>
</body>
</html>"""
    return html


def log_content(content_list: list[dict]):
    """Log content recycle activity."""
    DATA_DIR.mkdir(exist_ok=True)
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "content_count": len(content_list),
        "platforms": ["twitter", "facebook", "instagram", "threads", "telegram", "discord"],
        "status": "scheduled",
    }
    
    log = []
    if CONTENT_LOG.exists():
        log = json.loads(CONTENT_LOG.read_text())
    log.append(entry)
    CONTENT_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"📝 Logged: {len(content_list)} pieces of content ready for cross-posting")


def main():
    shorts = get_latest_shorts()
    if not shorts:
        print("No Shorts found")
        return
    
    # Generate schedule page
    docs_dir = BASE_DIR / "docs"
    docs_dir.mkdir(exist_ok=True)
    html = generate_schedule_html(shorts)
    (docs_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"✅ Generated schedule page with {len(shorts)} shorts")
    
    # Generate individual share files for each platform
    for s in shorts[:3]:  # Top 3
        texts = generate_share_text(s)
        share_dir = docs_dir / "shares"
        share_dir.mkdir(exist_ok=True)
        vid = s.get("video_id", "unknown")
        for platform, text in texts.items():
            (share_dir / f"{vid}_{platform}.txt").write_text(text, encoding="utf-8")
    
    log_content(shorts)


if __name__ == "__main__":
    main()
