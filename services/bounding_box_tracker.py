"""Redis-based cumulative bounding box tracking service."""

import json
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from utils.database import database


@dataclass
class BoundingBoxData:
    """Data structure for storing bounding box information."""
    x: int
    y: int
    width: int
    height: int
    timestamp: datetime
    attempt_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'timestamp': self.timestamp.isoformat(),
            'attempt_id': self.attempt_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BoundingBoxData':
        """Create from dictionary."""
        return cls(
            x=data['x'],
            y=data['y'],
            width=data['width'],
            height=data['height'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            attempt_id=data.get('attempt_id')
        )


@dataclass
class CumulativeBoundingBox:
    """Data structure for cumulative bounding box."""
    min_x: int
    min_y: int
    max_x: int
    max_y: int
    total_attempts: int
    last_updated: datetime
    individual_boxes: List[BoundingBoxData]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'min_x': self.min_x,
            'min_y': self.min_y,
            'max_x': self.max_x,
            'max_y': self.max_y,
            'total_attempts': self.total_attempts,
            'last_updated': self.last_updated.isoformat(),
            'individual_boxes': [box.to_dict() for box in self.individual_boxes]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CumulativeBoundingBox':
        """Create from dictionary."""
        return cls(
            min_x=data['min_x'],
            min_y=data['min_y'],
            max_x=data['max_x'],
            max_y=data['max_y'],
            total_attempts=data['total_attempts'],
            last_updated=datetime.fromisoformat(data['last_updated']),
            individual_boxes=[BoundingBoxData.from_dict(box) for box in data['individual_boxes']]
        )
    
    def get_union_box(self) -> Dict[str, int]:
        """Get the union bounding box in API format (minX, maxX, minY, maxY)."""
        return {
            'minX': self.min_x,
            'maxX': self.max_x,
            'minY': self.min_y,
            'maxY': self.max_y
        }
    
    def get_center_point(self) -> Tuple[float, float]:
        """Get the center point of the cumulative bounding box."""
        center_x = (self.min_x + self.max_x) / 2
        center_y = (self.min_y + self.max_y) / 2
        return center_x, center_y


class BoundingBoxTracker:
    """Redis-based service for tracking cumulative bounding boxes per session."""
    
    def __init__(self, ttl_hours: int = 24):
        """
        Initialize the bounding box tracker.
        
        Args:
            ttl_hours: Time-to-live for session data in hours (default: 24)
        """
        self.ttl_seconds = ttl_hours * 3600
        self.redis_client = None
    
    async def _get_redis_client(self):
        """Get Redis client, ensuring connection is established."""
        if not self.redis_client:
            self.redis_client = await database.get_redis_client()
        return self.redis_client
    
    def _get_session_key(self, socket_id: str, question_url: str) -> str:
        """Generate Redis key for session-specific bounding box data."""
        # Create a hash of question URL to ensure consistent key format
        import hashlib
        question_hash = hashlib.md5(question_url.encode()).hexdigest()[:8]
        return f"bbox:session:{socket_id}:question:{question_hash}"
    
    async def add_bounding_box(
        self, 
        socket_id: str, 
        question_url: str, 
        bounding_box: Dict[str, float],
        attempt_id: Optional[str] = None
    ) -> CumulativeBoundingBox:
        """
        Add a new bounding box to the session and return cumulative bounding box.
        
        Args:
            socket_id: Unique session identifier
            question_url: URL of the question image
            bounding_box: Bounding box in API format (minX, maxX, minY, maxY)
            attempt_id: Optional attempt identifier
            
        Returns:
            CumulativeBoundingBox: Updated cumulative bounding box
        """
        redis_client = await self._get_redis_client()
        session_key = self._get_session_key(socket_id, question_url)
        
        # Convert API format to internal format
        new_box = BoundingBoxData(
            x=int(bounding_box['minX']),
            y=int(bounding_box['minY']),
            width=int(bounding_box['maxX'] - bounding_box['minX']),
            height=int(bounding_box['maxY'] - bounding_box['minY']),
            timestamp=datetime.utcnow(),
            attempt_id=attempt_id
        )
        
        # Get existing cumulative data
        existing_data = await redis_client.get(session_key)
        
        if existing_data:
            # Parse existing cumulative bounding box
            cumulative = CumulativeBoundingBox.from_dict(json.loads(existing_data))
            
            # Add new box to individual boxes
            cumulative.individual_boxes.append(new_box)
            cumulative.total_attempts += 1
            cumulative.last_updated = datetime.utcnow()
            
            # Update cumulative bounds
            cumulative = self._update_cumulative_bounds(cumulative, new_box)
            
        else:
            # Create new cumulative bounding box
            cumulative = CumulativeBoundingBox(
                min_x=new_box.x,
                min_y=new_box.y,
                max_x=new_box.x + new_box.width,
                max_y=new_box.y + new_box.height,
                total_attempts=1,
                last_updated=datetime.utcnow(),
                individual_boxes=[new_box]
            )
        
        # Store updated cumulative data in Redis
        await redis_client.setex(
            session_key, 
            self.ttl_seconds, 
            json.dumps(cumulative.to_dict())
        )
        
        return cumulative
    
    def _update_cumulative_bounds(
        self, 
        cumulative: CumulativeBoundingBox, 
        new_box: BoundingBoxData
    ) -> CumulativeBoundingBox:
        """
        Update cumulative bounding box bounds with new box.
        
        This implements the union/merge logic for combining bounding boxes.
        """
        new_max_x = new_box.x + new_box.width
        new_max_y = new_box.y + new_box.height
        
        # Update bounds to include new box (union operation)
        cumulative.min_x = min(cumulative.min_x, new_box.x)
        cumulative.min_y = min(cumulative.min_y, new_box.y)
        cumulative.max_x = max(cumulative.max_x, new_max_x)
        cumulative.max_y = max(cumulative.max_y, new_max_y)
        
        return cumulative
    
    async def get_cumulative_bounding_box(
        self, 
        socket_id: str, 
        question_url: str
    ) -> Optional[CumulativeBoundingBox]:
        """
        Get cumulative bounding box for a session and question.
        
        Args:
            socket_id: Unique session identifier
            question_url: URL of the question image
            
        Returns:
            CumulativeBoundingBox or None if no data exists
        """
        redis_client = await self._get_redis_client()
        session_key = self._get_session_key(socket_id, question_url)
        
        data = await redis_client.get(session_key)
        if data:
            return CumulativeBoundingBox.from_dict(json.loads(data))
        return None
    
    async def get_session_stats(self, socket_id: str, question_url: str) -> Dict[str, any]:
        """
        Get statistics for a session and question.
        
        Args:
            socket_id: Unique session identifier
            question_url: URL of the question image
            
        Returns:
            Dictionary with session statistics
        """
        cumulative = await self.get_cumulative_bounding_box(socket_id, question_url)
        
        if not cumulative:
            return {
                'total_attempts': 0,
                'has_data': False,
                'session_duration_minutes': 0,
                'bounding_box_area': 0
            }
        
        # Calculate session duration
        if cumulative.individual_boxes:
            first_attempt = min(box.timestamp for box in cumulative.individual_boxes)
            session_duration = cumulative.last_updated - first_attempt
            session_duration_minutes = session_duration.total_seconds() / 60
        else:
            session_duration_minutes = 0
        
        # Calculate bounding box area
        bbox_area = (cumulative.max_x - cumulative.min_x) * (cumulative.max_y - cumulative.min_y)
        
        return {
            'total_attempts': cumulative.total_attempts,
            'has_data': True,
            'session_duration_minutes': round(session_duration_minutes, 2),
            'bounding_box_area': bbox_area,
            'cumulative_bounds': cumulative.get_union_box(),
            'center_point': cumulative.get_center_point(),
            'last_updated': cumulative.last_updated.isoformat()
        }
    
    async def clear_session_data(self, socket_id: str, question_url: str) -> bool:
        """
        Clear bounding box data for a specific session and question.
        
        Args:
            socket_id: Unique session identifier
            question_url: URL of the question image
            
        Returns:
            True if data was cleared, False if no data existed
        """
        redis_client = await self._get_redis_client()
        session_key = self._get_session_key(socket_id, question_url)
        
        result = await redis_client.delete(session_key)
        return result > 0
    
    async def get_all_sessions_for_socket(self, socket_id: str) -> List[Dict[str, any]]:
        """
        Get all question sessions for a socket_id.
        
        Args:
            socket_id: Unique session identifier
            
        Returns:
            List of session data for all questions
        """
        redis_client = await self._get_redis_client()
        pattern = f"bbox:session:{socket_id}:question:*"
        
        keys = await redis_client.keys(pattern)
        sessions = []
        
        for key in keys:
            data = await redis_client.get(key)
            if data:
                cumulative = CumulativeBoundingBox.from_dict(json.loads(data))
                # Extract question hash from key
                question_hash = key.split(':')[-1]
                sessions.append({
                    'question_hash': question_hash,
                    'stats': await self.get_session_stats(socket_id, f"question_{question_hash}"),
                    'cumulative_box': cumulative.to_dict()
                })
        
        return sessions


# Global instance
bounding_box_tracker = BoundingBoxTracker()
