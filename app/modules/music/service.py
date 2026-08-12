from typing import List
from app.modules.music.schemas import TrackResult

FEATURED_TRACKS = [
    TrackResult(
        id="honeymoon",
        title="Honeymoon Avenue (Live from London)",
        artist="Ariana Grande",
        preview_url="https://audio-ssl.itunes.apple.com/itunes-assets/AudioVideo126/v4/bf/97/81/bf97813a-73d7-e070-5b5c-42b7a9775338/mzaf_16239109015945199859.plus.aac.p.m4a",
    ),
    TrackResult(
        id="be-with-you",
        title="Be with you",
        artist="The Ridleys",
        preview_url="https://audio-ssl.itunes.apple.com/itunes-assets/AudioVideo116/v4/4a/12/32/4a123282-3d84-c5a4-ee4f-4dcdbf4e3752/mzaf_10014234057861917726.plus.aac.p.m4a",
    ),
    TrackResult(
        id="ivy",
        title="Ivy",
        artist="Frank Ocean",
        preview_url="https://audio-ssl.itunes.apple.com/itunes-assets/AudioVideo125/v4/80/c8/f5/80c8f5f6-c5db-64df-9cf8-66164287be19/mzaf_17772782782725838029.plus.aac.p.m4a",
    ),
    TrackResult(
        id="birds",
        title="Birds of a Feather",
        artist="Billie Eilish",
        preview_url="https://audio-ssl.itunes.apple.com/itunes-assets/AudioVideo211/v4/6b/97/99/6b979929-c852-50d4-1a98-0c6ef2c56b6c/mzaf_7190802874056262193.plus.aac.p.m4a",
    ),
    TrackResult(
        id="no-one",
        title="No One Noticed",
        artist="The Marías",
        preview_url="https://audio-ssl.itunes.apple.com/itunes-assets/AudioVideo221/v4/21/53/78/215378c8-b4b3-f61a-0e6d-2d4e7b8b4b1a/mzaf_1130386704177114670.plus.aac.p.m4a",
    ),
    TrackResult(
        id="lovers-rock",
        title="Lovers Rock",
        artist="TV Girl",
        preview_url="https://audio-ssl.itunes.apple.com/itunes-assets/AudioVideo112/v4/8d/ef/7e/8def7e7c-ebc4-bfef-c5ee-eec4bb6321df/mzaf_986291938183921074.plus.aac.p.m4a",
    ),
    TrackResult(
        id="those-eyes",
        title="Those Eyes",
        artist="New West",
        preview_url="https://audio-ssl.itunes.apple.com/itunes-assets/AudioVideo116/v4/95/8e/32/958e32d6-ee90-a2ef-99b3-4613c2f9d501/mzaf_16428784964654921634.plus.aac.p.m4a",
    ),
    TrackResult(
        id="just-the-way",
        title="Just The Way You Are",
        artist="Bruno Mars",
        preview_url="https://audio-ssl.itunes.apple.com/itunes-assets/AudioVideo125/v4/ee/12/36/ee12368c-28df-ff53-1596-f04eb581e2eb/mzaf_1079361730034636365.plus.aac.p.m4a",
    ),
    TrackResult(
        id="heavy",
        title="Heavy",
        artist="The Marías",
        preview_url="https://audio-ssl.itunes.apple.com/itunes-assets/AudioVideo221/v4/28/67/6f/28676f14-04aa-5769-b593-51c3ff32a58b/mzaf_10986518178129759885.plus.aac.p.m4a",
    ),
    TrackResult(
        id="perfect",
        title="Perfect",
        artist="Ed Sheeran",
        preview_url="https://audio-ssl.itunes.apple.com/itunes-assets/AudioVideo115/v4/10/d8/50/10d850a5-5f56-02e6-a212-002d24dd80d2/mzaf_2448373305988771146.plus.aac.p.m4a",
    ),
]


class MusicService:
    @staticmethod
    def get_featured_songs() -> List[TrackResult]:
        return FEATURED_TRACKS

    @staticmethod
    def search_songs(query: str) -> List[TrackResult]:
        """An empty query means "show me everything"; a query that matches
        nothing returns nothing. Falling back to featured tracks on a miss made
        every search look successful, however far off the term was."""
        q = query.lower().strip()
        if not q:
            return FEATURED_TRACKS
        return [t for t in FEATURED_TRACKS if q in t.title.lower() or q in t.artist.lower()]
