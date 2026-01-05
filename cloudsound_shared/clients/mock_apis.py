"""Mock implementations of external APIs for development and testing."""
from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)

class MockYouTubeClient:
    """Mock YouTube API client for development."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "mock-youtube-key"
        logger.info("mock_youtube_client_initialized")
    
    def search_music(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Mock search for music videos."""
        logger.debug("mock_youtube_search", query=query, max_results=max_results)
        
        # Return mock results
        return [
            {
                "video_id": f"mock_video_{i}",
                "title": f"{query} - Track {i+1}",
                "channel": "Mock Artist Channel",
                "duration": 180 + (i * 30),
                "thumbnail": f"https://i.ytimg.com/vi/mock_video_{i}/default.jpg",
                "url": f"https://youtube.com/watch?v=mock_video_{i}",
            }
            for i in range(max_results)
        ]
    
    def get_video_info(self, video_id: str) -> Dict[str, Any]:
        """Mock get video information."""
        logger.debug("mock_youtube_get_info", video_id=video_id)
        return {
            "video_id": video_id,
            "title": "Mock Track Title",
            "channel": "Mock Artist",
            "duration": 240,
            "description": "Mock track description",
        }
    
    def extract_audio_url(self, video_id: str) -> str:
        """Mock extract audio URL (returns mock file path)."""
        logger.debug("mock_youtube_extract_audio", video_id=video_id)
        return f"https://mock-cdn.example.com/audio/{video_id}.mp3"

class MockBandcampClient:
    """Mock Bandcamp API client for development."""
    
    def __init__(self):
        logger.info("mock_bandcamp_client_initialized")
    
    def search_album(self, query: str) -> List[Dict[str, Any]]:
        """Mock search for albums."""
        logger.debug("mock_bandcamp_search", query=query)
        return [
            {
                "album_id": f"mock_album_{i}",
                "title": f"{query} Album {i+1}",
                "artist": "Mock Bandcamp Artist",
                "tracks": [
                    {
                        "track_id": f"mock_track_{i}_{j}",
                        "title": f"Track {j+1}",
                        "duration": 200 + (j * 20),
                    }
                    for j in range(5)
                ],
                "url": f"https://mockartist.bandcamp.com/album/{query.lower().replace(' ', '-')}-{i}",
            }
            for i in range(3)
        ]
    
    def get_track_info(self, track_url: str) -> Dict[str, Any]:
        """Mock get track information."""
        logger.debug("mock_bandcamp_get_track", url=track_url)
        return {
            "track_id": "mock_track_123",
            "title": "Mock Bandcamp Track",
            "artist": "Mock Artist",
            "duration": 250,
            "album": "Mock Album",
            "audio_url": f"https://mock-cdn.example.com/bandcamp/mock_track_123.mp3",
        }

class MockFacebookEventsClient:
    """Mock Facebook Events API client for development."""
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or "mock-facebook-token"
        logger.info("mock_facebook_events_client_initialized")
    
    def get_events(
        self,
        page_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Mock get events from Facebook."""
        logger.debug("mock_facebook_get_events", page_id=page_id, since=since, until=until)
        
        # Generate mock events
        base_date = datetime.utcnow()
        mock_events = []
        
        for i in range(5):
            event_date = base_date + timedelta(days=7 + (i * 7))
            mock_events.append({
                "id": f"mock_event_{i}",
                "name": f"Mock Concert Event {i+1}",
                "start_time": event_date.isoformat(),
                "end_time": (event_date + timedelta(hours=3)).isoformat(),
                "place": {
                    "name": f"Mock Venue {i+1}",
                    "location": {
                        "city": "Mock City",
                        "country": "Mock Country",
                    },
                },
                "description": f"Mock event description {i+1}",
                "cover": {
                    "source": f"https://mock-cdn.example.com/events/event_{i}.jpg",
                },
            })
        
        return mock_events
    
    def get_event_details(self, event_id: str) -> Dict[str, Any]:
        """Mock get event details."""
        logger.debug("mock_facebook_get_event_details", event_id=event_id)
        return {
            "id": event_id,
            "name": "Mock Concert Event",
            "start_time": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "place": {
                "name": "Mock Venue",
                "location": {
                    "city": "Mock City",
                    "country": "Mock Country",
                },
            },
            "description": "Mock event description",
        }

# Environment-based configuration - automatically determined from ENVIRONMENT variable
import os
from cloudsound_shared.config.settings import app_settings

# Use mock APIs in development and test, real APIs in production
USE_MOCK_APIS = app_settings.use_mock_apis

def get_youtube_client(api_key: Optional[str] = None):
    """Get YouTube client (mock or real based on config)."""
    if USE_MOCK_APIS:
        return MockYouTubeClient(api_key)
    else:
        # Import real client when implemented
        # from backend.music_discovery.src.clients.youtube_client import YouTubeClient
        # return YouTubeClient(api_key)
        raise NotImplementedError("Real YouTube client not yet implemented")

def get_bandcamp_client():
    """Get Bandcamp client (mock or real based on config)."""
    if USE_MOCK_APIS:
        return MockBandcampClient()
    else:
        # Import real client when implemented
        # from backend.music_discovery.src.clients.bandcamp_client import BandcampClient
        # return BandcampClient()
        raise NotImplementedError("Real Bandcamp client not yet implemented")

def get_facebook_events_client(access_token: Optional[str] = None):
    """Get Facebook Events client (mock or real based on config)."""
    if USE_MOCK_APIS:
        return MockFacebookEventsClient(access_token)
    else:
        # Import real client when implemented
        # from backend.event_manager.src.clients.facebook_client import FacebookEventsClient
        # return FacebookEventsClient(access_token)
        raise NotImplementedError("Real Facebook Events client not yet implemented")

