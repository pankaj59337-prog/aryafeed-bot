"""Bollywood Music Service for Authentic Vocal / Lyrical Reels."""

import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

BOLLYWOOD_MUSIC_DIR = Path("assets/music/bollywood")

VOCAL_TRACKS: List[Dict[str, Any]] = [
    {
        "id": "pee_loon",
        "file": "pee_loon_vocal.mp3",
        "title": "Pee Loon",
        "artist": "Mohit Chauhan",
        "lyrics": "Pee loon tere neele neele naino se shabnam...",
        "icon": "💋",
        "style_affinity": ["sexy", "cinematic", "romantic"],
    },
    {
        "id": "kesariya",
        "file": "kesariya_vocal.mp3",
        "title": "Kesariya",
        "artist": "Arijit Singh",
        "lyrics": "Kesariya tera ishq hai piya, rang jaaun jo main...",
        "icon": "💖",
        "style_affinity": ["romantic", "quote", "cinematic", "traditional"],
    },
    {
        "id": "apna_bana_le",
        "file": "apna_bana_le_vocal.mp3",
        "title": "Apna Bana Le",
        "artist": "Arijit Singh",
        "lyrics": "Apna bana le piya, dil ke nagar mein shehar...",
        "icon": "✨",
        "style_affinity": ["sexy", "romantic", "cinematic"],
    },
    {
        "id": "raataan_lambiyan",
        "file": "raataan_lambiyan_vocal.mp3",
        "title": "Raataan Lambiyan",
        "artist": "Jubin Nautiyal",
        "lyrics": "Teri galliyan, raataan lambiyan lambiyan re...",
        "icon": "🌙",
        "style_affinity": ["romantic", "cinematic", "sexy"],
    },
    {
        "id": "o_maahi",
        "file": "o_maahi_vocal.mp3",
        "title": "O Maahi",
        "artist": "Arijit Singh",
        "lyrics": "O maahi re, o maahi re, tere sang ishq kiya...",
        "icon": "🎬",
        "style_affinity": ["cinematic", "romantic", "quote", "sexy"],
    },
    {
        "id": "tum_hi_ho",
        "file": "tum_hi_ho_vocal.mp3",
        "title": "Tum Hi Ho",
        "artist": "Arijit Singh",
        "lyrics": "Kyunki tum hi ho, ab tum hi ho, zindagi ab tum hi ho...",
        "icon": "🌹",
        "style_affinity": ["romantic", "quote", "cinematic", "traditional", "sexy"],
    },
    {
        "id": "tum_hi_aana",
        "file": "tum_hi_aana_vocal.mp3",
        "title": "Tum Hi Aana",
        "artist": "Jubin Nautiyal (Marjaavaan)",
        "lyrics": "Tere jaane ka gham aur na aane ka gham, fir zamane ka gham...",
        "icon": "🥀",
        "style_affinity": ["romantic", "cinematic", "quote", "sexy"],
    },
    {
        "id": "channa_mereya",
        "file": "channa_mereya_vocal.mp3",
        "title": "Channa Mereya",
        "artist": "Arijit Singh",
        "lyrics": "Achha chalta hoon, duaon mein yaad rakhna...",
        "icon": "🥀",
        "style_affinity": ["quote", "cinematic", "romantic"],
    },
    {
        "id": "zara_sa",
        "file": "zara_sa_vocal.mp3",
        "title": "Zara Sa",
        "artist": "KK",
        "lyrics": "Zara sa dil mein de jagah tu, zara sa apna le bana...",
        "icon": "🔥",
        "style_affinity": ["sexy", "romantic", "cinematic"],
    },
    {
        "id": "agar_tum_saath_ho",
        "file": "agar_tum_saath_ho_vocal.mp3",
        "title": "Agar Tum Saath Ho",
        "artist": "Alka Yagnik & Arijit",
        "lyrics": "Pal bhar theher jaao, dil yeh sambhal jaaye...",
        "icon": "🌧️",
        "style_affinity": ["romantic", "cinematic", "quote", "sexy"],
    },
    {
        "id": "shayad",
        "file": "shayad_vocal.mp3",
        "title": "Shayad",
        "artist": "Arijit Singh",
        "lyrics": "Shayad kabhi na keh sakoon main tumko...",
        "icon": "💫",
        "style_affinity": ["romantic", "quote", "minimal", "cinematic", "sexy"],
    },
    {
        "id": "kal_ho_naa_ho",
        "file": "kal_ho_naa_ho_vocal.mp3",
        "title": "Kal Ho Naa Ho",
        "artist": "Sonu Nigam",
        "lyrics": "Har ghadi badal rahi hai roop zindagi...",
        "icon": "🌅",
        "style_affinity": ["cinematic", "quote", "romantic"],
    },
    {
        "id": "ve_kamleya",
        "file": "ve_kamleya_vocal.mp3",
        "title": "Ve Kamleya",
        "artist": "Arijit Singh",
        "lyrics": "Ve kamleya, ve kamleya, mere naadan dil...",
        "icon": "🕊️",
        "style_affinity": ["romantic", "traditional", "quote"],
    },
    {
        "id": "hasi_ban_gaye",
        "file": "hasi_ban_gaye_vocal.mp3",
        "title": "Hasi Ban Gaye",
        "artist": "Shreya Ghoshal",
        "lyrics": "Haan hasi ban gaye, haan nami ban gaye...",
        "icon": "🌸",
        "style_affinity": ["romantic", "traditional", "minimal"],
    },
    {
        "id": "kaun_tujhe",
        "file": "kaun_tujhe_vocal.mp3",
        "title": "Kaun Tujhe",
        "artist": "Palak Muchhal",
        "lyrics": "Kaun tujhe yoon pyar karega jaise main karti hoon...",
        "icon": "🤍",
        "style_affinity": ["romantic", "traditional", "quote"],
    },
    {
        "id": "bol_do_na_zara",
        "file": "bol_do_na_zara_vocal.mp3",
        "title": "Bol Do Na Zara",
        "artist": "Armaan Malik",
        "lyrics": "Bol do na zara, dil mein jo hai chhipa...",
        "icon": "💌",
        "style_affinity": ["sexy", "romantic", "cinematic"],
    },
    {
        "id": "dil_de_diya_hai",
        "file": "dil_de_diya_hai_vocal.mp3",
        "title": "Dil De Diya Hai",
        "artist": "Anand Raj Anand",
        "lyrics": "Dil de diya hai, jaan tumhe denge...",
        "icon": "💔",
        "style_affinity": ["romantic", "broken", "cinematic", "traditional", "quote"],
    },
    {
        "id": "lut_gaye",
        "file": "lut_gaye_jubin_nautiyal_vocal.mp3",
        "title": "Lut Gaye",
        "artist": "Jubin Nautiyal",
        "lyrics": "Aankh uthi mohabbat ne angrai li, dil ka sauda hua chandi raat mein...",
        "icon": "🥀",
        "style_affinity": ["romantic", "broken", "cinematic", "sexy", "quote"],
    },
]

TRACK_METADATA: Dict[str, Dict[str, Any]] = {
    t["file"]: {
        "title": f"{t['title']} ({t['artist']} - Vocal)",
        "artist": t["artist"],
        "lyrics": t["lyrics"],
        "style_affinity": t["style_affinity"],
    }
    for t in VOCAL_TRACKS
}


class MusicService:
    """Manages Bollywood vocal soundtrack selection and integration."""

    def __init__(self, music_dir: Path = BOLLYWOOD_MUSIC_DIR):
        self.music_dir = music_dir
        self.music_dir.mkdir(parents=True, exist_ok=True)

    def get_vocal_options(
        self,
        category: Optional[str] = None,
        exclude_ids: Optional[set] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Return fresh vocal / lyrics Bollywood tracks filtered by category and excluding already used ones."""
        exclude = set(exclude_ids) if exclude_ids else set()

        # Filter by category / style affinity if provided
        cat = category.lower().strip() if category else None
        if cat:
            cat_pool = [
                t for t in VOCAL_TRACKS
                if any(cat in aff.lower() for aff in t.get("style_affinity", []))
                or (cat in ("baddie", "bestie", "aesthetic") and any(aff.lower() in ("sexy", "romantic") for aff in t.get("style_affinity", [])))
                or (cat == "broken" and any(aff.lower() in ("cinematic", "romantic") for aff in t.get("style_affinity", [])))
            ]
            # If category has tracks, use that pool; else fallback to all
            pool = cat_pool if cat_pool else VOCAL_TRACKS
        else:
            pool = VOCAL_TRACKS

        candidates = [t for t in pool if t["id"] not in exclude]
        if not candidates:
            candidates = list(pool)

        # Shuffle candidates for fresh order
        random.shuffle(candidates)
        results = []
        for t in candidates[:limit]:
            path = self.music_dir / t["file"]
            results.append({**t, "path": path})
        return results

    def get_vocal_track_by_id(self, track_id: str) -> Optional[Path]:
        """Find vocal track path by its identifier (e.g. 'pee_loon')."""
        for t in VOCAL_TRACKS:
            if t["id"] == track_id:
                p = self.music_dir / t["file"]
                if p.exists() and p.stat().st_size > 1000:
                    return p
                raw_p = self.music_dir / f"{track_id}_raw.mp3"
                if raw_p.exists():
                    return raw_p
        return None

    def resolve_song_by_name(self, query: str, category: Optional[str] = None) -> Tuple[Path, str]:
        """Resolve a user-specified song name or URL to an authentic vocal audio track.
        Matches against local library first, then searches & downloads via yt-dlp if needed."""
        import re

        clean_query = query.strip()
        url_match = re.search(r"https?://[^\s)\]]+", clean_query)
        url = url_match.group(0) if url_match else None

        # Clean text without URLs or markdown
        clean_text = re.sub(r"https?://[^\s)\]]+", "", clean_query)
        clean_text = re.sub(r"[\[\]\(\)\"\'\-_]", " ", clean_text)
        clean_text = " ".join(clean_text.split()).strip()
        q_norm = clean_text.lower()

        # If a direct URL was supplied, download/extract from it directly
        if url:
            logger.info(f"Direct song URL provided by user: {url}")
            downloaded = self._download_online_track(url, title_hint=clean_text)
            if downloaded:
                return downloaded

        # 1. Exact or strong substring match in VOCAL_TRACKS
        if q_norm:
            matches = []
            for t in VOCAL_TRACKS:
                t_title = t["title"].lower()
                t_id = t["id"].lower()
                # Exact equality
                if q_norm == t_title or q_norm == t_id:
                    matches.append((100, len(t_title), t))
                # Title is in user query (e.g. "Tum Hi Aana (From Marjaavaan)")
                elif t_title in q_norm or t_id in q_norm:
                    matches.append((50, len(t_title), t))
                # User query is in title
                elif len(q_norm) >= 4 and q_norm in t_title:
                    matches.append((30, len(q_norm), t))

            if matches:
                # Prioritize highest rank and longest matching title
                matches.sort(key=lambda x: (x[0], x[1]), reverse=True)
                best_t = matches[0][2]
                p = self.get_vocal_track_by_id(best_t["id"])
                if p and p.exists():
                    logger.info(f"Matched '{query}' to local track: {best_t['title']}")
                    return p, f"{best_t['title']} ({best_t['artist']})"

        # 2. Check existing local mp3 files in music directory
        if q_norm:
            safe_slug = re.sub(r"[^a-zA-Z0-9_]", "_", q_norm)[:30]
            for p in self.music_dir.glob("*.mp3"):
                stem = p.stem.lower()
                if q_norm in stem or stem in q_norm or safe_slug in stem:
                    return p, self.get_track_title(p)

        # 3. If not in local library, download exact requested song online via yt-dlp
        target_to_search = clean_text or clean_query
        try:
            logger.info(f"Song '{target_to_search}' not in local library. Downloading online via yt-dlp...")
            downloaded = self._download_online_track(target_to_search)
            if downloaded:
                return downloaded
        except Exception as e:
            logger.warning(f"Online song fetch failed for '{target_to_search}': {e}")

        # 4. Fallback to style-matched track from library only if download fails
        fallback = self.get_bollywood_track(category or "romantic")
        return fallback, self.get_track_title(fallback)

    def _download_online_track(self, query: str, title_hint: Optional[str] = None) -> Optional[Tuple[Path, str]]:
        """Download and trim a 16s chorus clip from YouTube or JioSaavn using yt-dlp."""
        import subprocess
        import re

        clean_q = query.strip()
        is_url = clean_q.startswith("http://") or clean_q.startswith("https://")

        if is_url:
            target = clean_q
            if "jiosaavn.com" in target and "/lyrics/" in target:
                # Convert JioSaavn lyrics URL to song URL for yt-dlp extractor
                target = target.replace("/lyrics/", "/song/").replace("-lyrics/", "/")
            slug = re.sub(r"[^a-zA-Z0-9_]", "", target.split("/")[-1])[:30] or "saavn_track"
        else:
            target = f"ytsearch1:{clean_q} song audio"
            slug = re.sub(r"[^a-zA-Z0-9_]", "_", clean_q.lower())[:30]

        out_raw = self.music_dir / f"{slug}_raw.mp3"
        out_vocal = self.music_dir / f"{slug}_vocal.mp3"

        if out_vocal.exists() and out_vocal.stat().st_size > 1000:
            display_title = title_hint.title() if title_hint else clean_q.title()
            return out_vocal, f"{display_title} (Vocal Chorus)"

        targets_to_try = [target]
        if not is_url:
            targets_to_try.append(f"scsearch1:{clean_q}")

        for current_target in targets_to_try:
            logger.info(f"Running yt-dlp for target: {current_target}")
            cmd = [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "mp3",
                "--output", str(out_raw),
                "--max-filesize", "25M",
                "--no-playlist",
            ]
            if "ytsearch" in current_target or "youtube" in current_target:
                cmd.extend(["--extractor-args", "youtube:player_client=android"])
            cmd.append(current_target)

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if res.returncode == 0 and out_raw.exists() and out_raw.stat().st_size > 1000:
                # Get video/song title
                title_cmd = ["yt-dlp", "--get-title", "--no-playlist", current_target]
                t_res = subprocess.run(title_cmd, capture_output=True, text=True, timeout=15)
                extracted_title = (
                    t_res.stdout.strip()
                    if t_res.returncode == 0 and t_res.stdout.strip()
                    else (title_hint.title() if title_hint else clean_q.title())
                )
                clean_display = extracted_title.split("|")[0].split("(")[0].strip() if "|" in extracted_title else extracted_title

                # Cut 16s high-energy chorus clip with FFmpeg (start at 30s)
                trim_cmd = [
                    "ffmpeg", "-y",
                    "-ss", "00:00:30",
                    "-i", str(out_raw),
                    "-t", "16",
                    "-c", "copy",
                    str(out_vocal),
                ]
                subprocess.run(trim_cmd, capture_output=True, timeout=15)
                if out_vocal.exists() and out_vocal.stat().st_size > 1000:
                    return out_vocal, f"{clean_display} (Vocal Chorus)"
                return out_raw, f"{clean_display} (Vocal Chorus)"
            else:
                logger.warning(f"Target '{current_target}' failed ({res.returncode}): {res.stderr[:160] if res.stderr else 'no output'}")

        return None

    def get_available_tracks(self) -> List[Path]:
        """List valid MP3 files in the Bollywood music library (prioritizing vocal tracks)."""
        if not self.music_dir.exists():
            return []
        vocals = [p for p in self.music_dir.glob("*_vocal.mp3") if p.stat().st_size > 1000]
        if vocals:
            return vocals
        return [p for p in self.music_dir.glob("*.mp3") if p.stat().st_size > 1000]

    def get_bollywood_track(self, style: Optional[str] = None) -> Optional[Path]:
        """Select a Bollywood vocal track, matching the given reel style if possible."""
        tracks = self.get_available_tracks()
        if not tracks:
            fallback = Path("data/audio/sensual_ambient.mp3")
            return fallback if fallback.exists() else None

        if style:
            style_lower = style.lower().strip()
            candidates = [
                p for p in tracks
                if p.name in TRACK_METADATA and (
                    style_lower in TRACK_METADATA[p.name].get("style_affinity", [])
                    or (style_lower in ("baddie", "bestie", "aesthetic") and any(s in TRACK_METADATA[p.name].get("style_affinity", []) for s in ["sexy", "romantic"]))
                    or (style_lower == "broken" and any(s in TRACK_METADATA[p.name].get("style_affinity", []) for s in ["cinematic", "romantic"]))
                )
            ]
            if candidates:
                chosen = random.choice(candidates)
                logger.info(f"Selected style-matched vocal track: {chosen.name} for style '{style}'")
                return chosen

        chosen = random.choice(tracks)
        logger.info(f"Selected random vocal track: {chosen.name}")
        return chosen

    def get_track_title(self, path: Optional[Path]) -> str:
        """Return human-friendly display name of the track."""
        if not path:
            return "Bollywood Vocal Track"
        filename = path.name
        if filename in TRACK_METADATA:
            return TRACK_METADATA[filename]["title"]
        clean = (
            path.stem.replace("_vocal", "")
            .replace("_raw", "")
            .replace("_lofi", "")
            .replace("_", " ")
            .title()
        )
        return f"{clean} (Vocal Lyrics)"


music_service = MusicService()


