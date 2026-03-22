import json
import os
from fastmcp import FastMCP

mcp = FastMCP("NeuroFlowTranscription")

_current_transcript: dict | None = None

FALLBACK_PATH = os.path.join(os.path.dirname(__file__), "demo_audio", "fallback_transcript.json")


def _get_openai_client():
    from agents.models.config import OPENAI_API_KEY
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        return None


def _load_fallback() -> dict:
    with open(FALLBACK_PATH) as f:
        return json.load(f)


@mcp.tool()
def transcribe_audio(audio_path: str = "") -> str:
    """Transcribe a lecture audio file. Uses Whisper API if available, otherwise falls back to demo transcript."""
    global _current_transcript

    if audio_path and os.path.exists(audio_path):
        client = _get_openai_client()
        if client:
            try:
                with open(audio_path, "rb") as f:
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        response_format="verbose_json",
                        timestamp_granularities=["segment"],
                    )
                segments = []
                for seg in response.segments:
                    segments.append({
                        "start": round(seg.start, 1),
                        "end": round(seg.end, 1),
                        "text": seg.text.strip(),
                    })
                _current_transcript = {
                    "transcript": response.text,
                    "duration_seconds": round(segments[-1]["end"]) if segments else 0,
                    "word_count": len(response.text.split()),
                    "speakers_detected": 1,
                    "segments": segments,
                }
                return json.dumps({
                    "action": "transcribed",
                    "source": "whisper",
                    "word_count": _current_transcript["word_count"],
                    "duration_seconds": _current_transcript["duration_seconds"],
                    "transcript_preview": _current_transcript["transcript"][:300],
                })
            except Exception:
                pass

    if _current_transcript is not None:
        return json.dumps({
            "action": "transcribed",
            "source": "cached",
            "word_count": _current_transcript["word_count"],
            "duration_seconds": _current_transcript["duration_seconds"],
            "transcript_preview": _current_transcript["transcript"][:300],
        })

    _current_transcript = _load_fallback()
    return json.dumps({
        "action": "transcribed",
        "source": "demo_fallback",
        "word_count": _current_transcript["word_count"],
        "duration_seconds": _current_transcript["duration_seconds"],
        "transcript_preview": _current_transcript["transcript"][:300],
    })


@mcp.tool()
def get_transcript() -> str:
    """Get the full current lecture transcript."""
    if not _current_transcript:
        return json.dumps({"error": "No transcript loaded. Transcribe audio first."})
    return json.dumps({
        "transcript": _current_transcript["transcript"],
        "word_count": _current_transcript["word_count"],
        "duration_seconds": _current_transcript["duration_seconds"],
        "speakers_detected": _current_transcript["speakers_detected"],
        "segment_count": len(_current_transcript["segments"]),
    })


@mcp.tool()
def get_recent(minutes: int = 5) -> str:
    """Get the last N minutes of the transcript using timestamp data."""
    if not _current_transcript:
        return json.dumps({"error": "No transcript loaded."})

    total_dur = _current_transcript["duration_seconds"]
    cutoff = max(0, total_dur - (minutes * 60))

    recent_segments = [
        s for s in _current_transcript["segments"]
        if s["start"] >= cutoff
    ]
    text = " ".join(s["text"] for s in recent_segments)
    return json.dumps({
        "minutes_requested": minutes,
        "from_timestamp": cutoff,
        "text": text,
        "segment_count": len(recent_segments),
    })


@mcp.tool()
def search_transcript(query: str) -> str:
    """Search the transcript for segments mentioning a keyword or concept."""
    if not _current_transcript:
        return json.dumps({"error": "No transcript loaded."})

    query_lower = query.lower()
    matches = [
        s for s in _current_transcript["segments"]
        if query_lower in s["text"].lower()
    ]

    if not matches:
        all_text = _current_transcript["transcript"].lower()
        if query_lower in all_text:
            idx = all_text.index(query_lower)
            start = max(0, idx - 100)
            end = min(len(all_text), idx + 200)
            return json.dumps({
                "query": query,
                "exact_matches": 0,
                "context_snippet": _current_transcript["transcript"][start:end],
            })

    return json.dumps({
        "query": query,
        "matches": matches,
        "match_count": len(matches),
    })
