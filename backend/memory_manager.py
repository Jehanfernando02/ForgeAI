"""
ForgeAI Phase 2: Memory Management
====================================

Session-level conversation memory with fact extraction and history trimming.
Manages all conversation state for active user sessions.
"""

import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class UserProfile:
    """User profile data extracted from conversation."""
    
    goals: Dict[str, str] = field(default_factory=dict)
    """Goals: {'strength': 'Build muscle', 'endurance': 'Run 5k', ...}"""
    
    measurements: Dict[str, float] = field(default_factory=dict)
    """Measurements: {'weight_kg': 80, 'height_cm': 180, 'body_fat_pct': 15}"""
    
    preferences: Dict[str, str] = field(default_factory=dict)
    """Preferences: {'training_time': 'morning', 'diet_type': 'high_protein'}"""
    
    facts: List[str] = field(default_factory=list)
    """Extracted facts: ['User prefers morning workouts', 'Recovering from knee injury']"""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Session:
    """A conversation session."""
    
    session_id: str
    """Unique session identifier"""
    
    created_at: float = field(default_factory=time.time)
    """Creation timestamp"""
    
    last_updated: float = field(default_factory=time.time)
    """Last update timestamp"""
    
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    """List of messages: [{'role': 'user'|'model', 'content': '...'}, ...]"""
    
    user_profile: UserProfile = field(default_factory=UserProfile)
    """Extracted user profile"""
    
    routing_history: List[Dict[str, Any]] = field(default_factory=list)
    """History of routing decisions"""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Session metadata: {'agent_stats': {...}, 'token_count': 0}"""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['user_profile'] = self.user_profile.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary."""
        if 'user_profile' in data and isinstance(data['user_profile'], dict):
            data['user_profile'] = UserProfile.from_dict(data['user_profile'])
        return cls(**data)


# ============================================================================
# MEMORY MANAGER (SINGLETON)
# ============================================================================

class MemoryManager:
    """
    Global memory manager for ForgeAI sessions.
    
    Handles:
    - Session creation and lifecycle
    - Conversation history management
    - User fact extraction and storage
    - Memory trimming (keep last 10 turns + summaries)
    
    In Phase 1-2, this is in-memory. In Phase 4, it will use a database.
    """
    
    _instance = None
    _sessions: Dict[str, Session] = {}
    
    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "MemoryManager":
        """Get the singleton instance."""
        return cls()
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    def create_session(self, session_id: str = None) -> Session:
        """
        Create a new session.
        
        Args:
            session_id: Optional custom session ID. If None, generates one.
        
        Returns:
            The new Session object
        """
        import os
        if session_id is None:
            session_id = os.urandom(16).hex()
        
        session = Session(session_id=session_id)
        self._sessions[session_id] = session
        
        print(f"[MemoryManager] Created session {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve a session.
        
        Args:
            session_id: Session ID to retrieve
        
        Returns:
            The Session object, or None if not found
        """
        return self._sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            print(f"[MemoryManager] Deleted session {session_id}")
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        """Get all active session IDs."""
        return list(self._sessions.keys())
    
    # ========================================================================
    # CONVERSATION HISTORY MANAGEMENT
    # ========================================================================
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        Add a message to a session's conversation history.
        
        Args:
            session_id: Session ID
            role: 'user' or 'model'
            content: Message content
        
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        session.last_updated = time.time()
        
        return True
    
    def get_history(self, session_id: str, limit: int = None) -> List[Dict[str, str]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return (None = all)
        
        Returns:
            List of message dicts, or empty list if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return []
        
        history = session.conversation_history
        if limit:
            history = history[-limit:]
        
        # Remove timestamp field for LLM consumption
        return [{"role": msg["role"], "content": msg["content"]} for msg in history]
    
    def trim_history(self, session_id: str, keep_last_turns: int = 10) -> bool:
        """
        Trim conversation history to keep only the last N turns.
        
        Removes oldest messages but keeps at least keep_last_turns.
        In Phase 3+, could store summaries of older messages.
        
        Args:
            session_id: Session ID
            keep_last_turns: Number of recent turns to keep
        
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Each turn = 2 messages (user + model)
        keep_messages = keep_last_turns * 2
        
        if len(session.conversation_history) > keep_messages:
            session.conversation_history = session.conversation_history[-keep_messages:]
            session.last_updated = time.time()
        
        return True
    
    def clear_history(self, session_id: str) -> bool:
        """
        Clear all conversation history for a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.conversation_history = []
        session.last_updated = time.time()
        
        return True
    
    # ========================================================================
    # USER PROFILE & FACTS MANAGEMENT
    # ========================================================================
    
    def add_facts(self, session_id: str, facts: List[str]) -> bool:
        """
        Add extracted facts to the user profile.
        
        Args:
            session_id: Session ID
            facts: List of fact strings
        
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Avoid duplicates
        existing = set(session.user_profile.facts)
        new_facts = [f for f in facts if f not in existing]
        
        session.user_profile.facts.extend(new_facts)
        session.last_updated = time.time()
        
        return True
    
    def update_profile(
        self,
        session_id: str,
        goals: Dict = None,
        measurements: Dict = None,
        preferences: Dict = None
    ) -> bool:
        """
        Update user profile fields.
        
        Args:
            session_id: Session ID
            goals: Dict of goals to merge
            measurements: Dict of measurements to merge
            preferences: Dict of preferences to merge
        
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        if goals:
            session.user_profile.goals.update(goals)
        if measurements:
            session.user_profile.measurements.update(measurements)
        if preferences:
            session.user_profile.preferences.update(preferences)
        
        session.last_updated = time.time()
        
        return True
    
    def get_profile(self, session_id: str) -> Optional[UserProfile]:
        """
        Get the user profile for a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            UserProfile object, or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        return session.user_profile
    
    def get_facts(self, session_id: str) -> List[str]:
        """
        Get all extracted facts for a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            List of fact strings, or empty list if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return []
        
        return session.user_profile.facts
    
    # ========================================================================
    # ROUTING & ANALYTICS
    # ========================================================================
    
    def record_routing(
        self,
        session_id: str,
        route_data: Dict[str, Any],
        agent_used: str
    ) -> bool:
        """
        Record a routing decision for analytics.
        
        Args:
            session_id: Session ID
            route_data: Routing decision data from supervisor
            agent_used: The agent that was ultimately used
        
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.routing_history.append({
            "timestamp": time.time(),
            "route": route_data.get('route', []),
            "agent_used": agent_used,
            "urgency": route_data.get('urgency', 'normal'),
        })
        
        # Update agent stats
        if 'agent_stats' not in session.metadata:
            session.metadata['agent_stats'] = {}
        
        stats = session.metadata['agent_stats']
        stats[agent_used] = stats.get(agent_used, 0) + 1
        
        return True
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get analytics for a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            Dict with stats (agent usage, routing decisions, etc.)
        """
        session = self.get_session(session_id)
        if not session:
            return {}
        
        return {
            "session_id": session_id,
            "created_at": datetime.fromtimestamp(session.created_at).isoformat(),
            "last_updated": datetime.fromtimestamp(session.last_updated).isoformat(),
            "total_messages": len(session.conversation_history),
            "total_turns": len(session.conversation_history) // 2,
            "agent_stats": session.metadata.get('agent_stats', {}),
            "routing_count": len(session.routing_history),
        }
    
    # ========================================================================
    # EXPORT & DEBUG
    # ========================================================================
    
    def export_session(self, session_id: str) -> Optional[dict]:
        """
        Export a session to a dictionary (for debugging/storage).
        
        Args:
            session_id: Session ID
        
        Returns:
            Session dict, or None if not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        return session.to_dict()
    
    def get_session_summary(self, session_id: str) -> str:
        """
        Get a human-readable summary of a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            Summary string, or error message if not found
        """
        session = self.get_session(session_id)
        if not session:
            return f"Session {session_id} not found"
        
        stats = self.get_session_stats(session_id)
        profile = session.user_profile
        
        summary = f"""
Session: {session_id}
Created: {stats['created_at']}
Messages: {stats['total_messages']}
Turns: {stats['total_turns']}

User Profile:
- Goals: {profile.goals or '(none)'}
- Measurements: {profile.measurements or '(none)'}
- Preferences: {profile.preferences or '(none)'}
- Facts extracted: {len(profile.facts)}

Agent Usage: {stats['agent_stats']}
        """.strip()
        
        return summary

