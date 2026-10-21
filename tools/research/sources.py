"""공개 영상 목록 metadata만 수집한다. 영상의 매매 규칙을 추정하지 않는다."""

import hashlib
import json
import re
from datetime import UTC, datetime
from urllib.parse import quote
from urllib.request import Request, urlopen

CHANNELS = [
    ("baekdaenam", "빽대남 - 매매법 검증해드립니다", "빽대남"),
    ("jishelin", "지슐랭 트레이더", "jishelin"),
    ("bcchartlab", "BC 차트연구소", "bcchartlab"),
    ("sonic_thecoin", "세매법 / 세상의 모든 매매법", "sonic_thecoin"),
    ("shirtsguy", "셔츠아저씨", "shirtsguy"),
    ("humpback_whale", "혹등고래&차트개미 투자이야기", "humpback__whale"),
]
FEATURED = [
    ("arFmhlgkjxc", "jishelin"),
    ("3isDFvPrhd4", "shirtsguy"),
    ("BAYuQlHI4PA", "sonic_thecoin"),
]


def read_url(url: str) -> bytes:
    request = Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR,ko;q=0.9"}
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 — 고정 공개 URL
        return response.read()


def initial_data(html: str) -> dict:
    match = re.search(
        r"(?:var\s+ytInitialData\s*=|window\[\"ytInitialData\"\]\s*=)\s*", html
    )
    if not match:
        raise ValueError("ytInitialData가 없거나 로그인·동의 페이지입니다")
    return json.JSONDecoder().raw_decode(html[match.end() :])[0]


def video_renderers(value):
    if isinstance(value, dict):
        if "videoRenderer" in value:
            yield value["videoRenderer"]
        lockup = value.get("lockupViewModel", {})
        if lockup.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO":
            metadata = lockup.get("metadata", {}).get("lockupMetadataViewModel", {})
            rows = (
                metadata.get("metadata", {})
                .get("contentMetadataViewModel", {})
                .get("metadataRows", [])
            )
            parts = [
                part.get("text", {}).get("content", "")
                for row in rows
                for part in row.get("metadataParts", [])
            ]
            yield {
                "videoId": lockup.get("contentId"),
                "title": {"simpleText": metadata.get("title", {}).get("content", "")},
                "publishedTimeText": {"simpleText": " | ".join(parts)},
            }
        for child in value.values():
            yield from video_renderers(child)
    elif isinstance(value, list):
        for child in value:
            yield from video_renderers(child)


def text_value(value: dict) -> str:
    return value.get("simpleText") or "".join(
        run.get("text", "") for run in value.get("runs", [])
    )


def utc_publication(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed.astimezone(UTC).isoformat() if parsed.tzinfo else None


def collect_sources() -> dict:
    checked_at = datetime.now(UTC).isoformat()
    registry = {
        "schema_version": 1,
        "checked_at": checked_at,
        "channels": [],
        "sources": [],
    }
    for channel_id, name, handle in CHANNELS:
        url = "https://www.youtube.com/@" + quote(handle) + "/videos"
        channel = {"id": channel_id, "name": name, "url": url, "checked_at": checked_at}
        try:
            raw = read_url(url)
            data = initial_data(raw.decode())
            seen = set()
            for renderer in video_renderers(data):
                video_id = renderer.get("videoId")
                if not video_id or video_id in seen:
                    continue
                seen.add(video_id)
                registry["sources"].append(
                    {
                        "id": "yt-" + video_id,
                        "channel_id": channel_id,
                        "url": "https://www.youtube.com/watch?v=" + video_id,
                        "title": text_value(renderer.get("title", {})),
                        "publication": {
                            "display": text_value(
                                renderer.get("publishedTimeText", {})
                            ),
                            "date_utc": None,
                        },
                        "checked_at": checked_at,
                        "evidence_level": "public_listing_metadata_only",
                        "evidence": [
                            {
                                "kind": "channel_listing",
                                "url": url,
                                "sha256": hashlib.sha256(raw).hexdigest(),
                            }
                        ],
                        "video_timestamps": [],
                        "rules": None,
                        "unknowns": [
                            "설정값",
                            "진입·청산",
                            "손절·익절",
                            "영상·자막 내용",
                            "원본 코드 사용권",
                        ],
                        "license": "unknown_no_code_reuse_authorized",
                        "access": "public_metadata_only",
                    }
                )
            channel.update(
                access="public_metadata",
                video_count=len(seen),
                listing_sha256=hashlib.sha256(raw).hexdigest(),
            )
            if not seen:
                channel.update(
                    access="blocked", error="목록에서 영상 metadata를 찾지 못했습니다"
                )
        except Exception as exc:
            channel.update(access="blocked", error=f"{type(exc).__name__}: {exc}")
        registry["channels"].append(channel)
    for video_id, channel_id in FEATURED:
        item = next(
            (row for row in registry["sources"] if row["id"] == "yt-" + video_id), None
        )
        if item is None:
            item = {
                "id": "yt-" + video_id,
                "channel_id": channel_id,
                "url": "https://www.youtube.com/watch?v=" + video_id,
                "rules": None,
                "video_timestamps": [],
                "license": "unknown_no_code_reuse_authorized",
                "unknowns": ["진입·청산·손절·포지션 규칙", "원본 코드 사용권"],
                "evidence": [],
            }
            registry["sources"].append(item)
        try:
            raw = read_url(item["url"])
            match = re.search(r"var\s+ytInitialPlayerResponse\s*=\s*", raw.decode())
            if not match:
                raise ValueError("watch player metadata가 없습니다")
            player = json.JSONDecoder().raw_decode(raw.decode()[match.end() :])[0]
            detail = player.get("videoDetails", {})
            if detail.get("videoId") != video_id:
                raise ValueError(
                    "요청 영상의 공개 player metadata를 확인할 수 없습니다"
                )
            microformat = player.get("microformat", {}).get(
                "playerMicroformatRenderer", {}
            )
            item.update(
                title=detail.get("title"),
                description=detail.get("shortDescription"),
                publication={
                    "date_utc": utc_publication(microformat.get("publishDate")),
                    "reported_publish_date": microformat.get("publishDate"),
                    "upload_date": microformat.get("uploadDate"),
                },
                access="public_watch_metadata",
                evidence_level="public_description_only",
                checked_at=checked_at,
            )
            item["evidence"].append(
                {
                    "kind": "watch_metadata",
                    "url": item["url"],
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
            tracks = (
                player.get("captions", {})
                .get("playerCaptionsTracklistRenderer", {})
                .get("captionTracks", [])
            )
            item["caption_languages"] = [track.get("languageCode") for track in tracks]
            korean = next(
                (track for track in tracks if track.get("languageCode") == "ko"), None
            )
            item["transcript_access"] = "not_offered"
            if korean:
                caption_bytes = read_url(korean["baseUrl"] + "&fmt=json3")
                if not caption_bytes:
                    item["transcript_access"] = "blocked_empty_response"
                else:
                    transcript = json.loads(caption_bytes)
                    segments = [
                        {
                            "start_ms": event.get("tStartMs"),
                            "duration_ms": event.get("dDurationMs"),
                            "text": "".join(
                                segment.get("utf8", "")
                                for segment in event.get("segs", [])
                            ),
                        }
                        for event in transcript.get("events", [])
                        if event.get("segs")
                    ]
                    item["transcript_access"] = (
                        "public_captions_retrieved_not_rules_verified"
                    )
                    item["transcript_segments"] = segments
                    item["evidence"].append(
                        {
                            "kind": "public_captions",
                            "sha256": hashlib.sha256(caption_bytes).hexdigest(),
                        }
                    )
        except Exception as exc:
            item["watch_access_error"] = f"{type(exc).__name__}: {exc}"
    return registry
