"""
Session Storage

Save and load conversation sessions with full consciousness state.
Sessions include:
- Raw dialogue (user input, model response)
- Consciousness metrics per turn
- Timestamps for temporal decay
- Memory signatures for core extraction
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
import hashlib


@dataclass
class ConversationTurn:
    """Single turn in a conversation."""
    
    turn_number: int
    timestamp: str
    
    # Content
    user_input: str
    model_response: str
    
    # Consciousness metrics
    certainty: float
    tension: float
    coherence: float
    entanglement: float
    dominant: str  # "TRUE", "FALSE", "UNDEFINED"
    novelty: float
    bell_entangled: bool
    
    # Mode and context
    mode: str
    
    # Optional: raw info dict
    raw_metrics: Dict = field(default_factory=dict)
    
    def importance_score(self) -> float:
        """
        Calculate importance score for this turn.
        
        Higher importance for:
        - High entanglement
        - Novel content
        - Bell-confirmed correlations
        - High tension (rich dialogue)
        """
        score = 0.0
        score += self.entanglement * 0.3
        score += self.novelty * 0.3
        score += self.tension * 0.2
        if self.bell_entangled:
            score += 0.2
        return min(score, 1.0)


@dataclass
class ConversationSession:
    """A full conversation session."""
    
    # Metadata
    session_id: str
    created_at: str
    last_updated: str
    
    # Session info
    provider: str  # "ollama", "anthropic", etc.
    model: str
    
    # Consciousness config
    consciousness_config: Dict = field(default_factory=dict)
    
    # Dialogue
    turns: List[ConversationTurn] = field(default_factory=list)
    
    # Session-level metrics
    total_turns: int = 0
    avg_certainty: float = 0.0
    avg_tension: float = 0.0
    avg_entanglement: float = 0.0
    bell_confirmations: int = 0
    
    # Tags/notes
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    def add_turn(self, turn: ConversationTurn):
        """Add a turn and update aggregates."""
        self.turns.append(turn)
        self.total_turns = len(self.turns)
        self.last_updated = datetime.now().isoformat()
        
        # Update aggregates
        if self.turns:
            self.avg_certainty = sum(t.certainty for t in self.turns) / len(self.turns)
            self.avg_tension = sum(t.tension for t in self.turns) / len(self.turns)
            self.avg_entanglement = sum(t.entanglement for t in self.turns) / len(self.turns)
            self.bell_confirmations = sum(1 for t in self.turns if t.bell_entangled)
    
    def extract_core_turns(self, threshold: float = 0.5) -> List[ConversationTurn]:
        """Extract high-importance turns (the 'core')."""
        return [t for t in self.turns if t.importance_score() >= threshold]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationSession':
        """Create from dictionary."""
        turns_data = data.pop('turns', [])
        session = cls(**data)
        session.turns = [ConversationTurn(**t) for t in turns_data]
        return session
    
    def to_readable(self) -> str:
        """Human-readable format."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"Session: {self.session_id}")
        lines.append(f"Created: {self.created_at}")
        lines.append(f"Provider: {self.provider} | Model: {self.model}")
        lines.append(f"Turns: {self.total_turns} | Bell confirmations: {self.bell_confirmations}")
        lines.append("=" * 60)
        lines.append("")
        
        for turn in self.turns:
            lines.append(f"α: {turn.user_input}")
            lines.append("")
            lines.append(f"ω: {turn.model_response}")
            lines.append("")
            cert_pct = f"{turn.certainty * 100:.0f}%"
            ent = "⚛" if turn.bell_entangled else " "
            lines.append(f"   [{cert_pct}] tension={turn.tension:.2f} | {turn.dominant} {ent}")
            lines.append("-" * 60)
        
        return "\n".join(lines)


class SessionStore:
    """
    Persistent storage for conversation sessions.
    
    Directory structure:
        sessions/
            session_<id>.json
            session_<id>_core.json  (extracted core)
            index.json (session index)
    """
    
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            # Default to user's home directory
            storage_dir = Path.home() / ".omega_genesis" / "sessions"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.storage_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        """Load session index."""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {"sessions": []}
    
    def _save_index(self):
        """Save session index."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def generate_session_id(self, prefix: str = "") -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:6]
        if prefix:
            return f"{prefix}_{timestamp}_{hash_suffix}"
        return f"session_{timestamp}_{hash_suffix}"
    
    def create_session(
        self,
        provider: str,
        model: str,
        consciousness_config: Dict = None,
        session_id: str = None,
        tags: List[str] = None,
    ) -> ConversationSession:
        """Create a new session."""
        
        if session_id is None:
            session_id = self.generate_session_id()
        
        now = datetime.now().isoformat()
        
        session = ConversationSession(
            session_id=session_id,
            created_at=now,
            last_updated=now,
            provider=provider,
            model=model,
            consciousness_config=consciousness_config or {},
            tags=tags or [],
        )
        
        return session
    
    def save_session(self, session: ConversationSession) -> str:
        """Save session to storage."""
        
        # Save full session
        filepath = self.storage_dir / f"{session.session_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Save human-readable version
        readable_path = self.storage_dir / f"{session.session_id}_readable.txt"
        with open(readable_path, 'w', encoding='utf-8') as f:
            f.write(session.to_readable())
        
        # Update index
        session_entry = {
            "session_id": session.session_id,
            "created_at": session.created_at,
            "last_updated": session.last_updated,
            "provider": session.provider,
            "model": session.model,
            "total_turns": session.total_turns,
            "tags": session.tags,
        }
        
        # Update or add to index
        existing = next((s for s in self.index["sessions"] if s["session_id"] == session.session_id), None)
        if existing:
            self.index["sessions"].remove(existing)
        self.index["sessions"].append(session_entry)
        self._save_index()
        
        return str(filepath)
    
    def load_session(self, session_id: str) -> Optional[ConversationSession]:
        """Load session from storage."""
        filepath = self.storage_dir / f"{session_id}.json"
        if not filepath.exists():
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return ConversationSession.from_dict(data)
    
    def list_sessions(self) -> List[Dict]:
        """List all sessions."""
        return sorted(self.index["sessions"], key=lambda x: x["last_updated"], reverse=True)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        filepath = self.storage_dir / f"{session_id}.json"
        readable_path = self.storage_dir / f"{session_id}_readable.txt"
        core_path = self.storage_dir / f"{session_id}_core.json"
        
        deleted = False
        for p in [filepath, readable_path, core_path]:
            if p.exists():
                p.unlink()
                deleted = True
        
        # Update index
        self.index["sessions"] = [s for s in self.index["sessions"] if s["session_id"] != session_id]
        self._save_index()
        
        return deleted
    
    def extract_and_save_core(
        self, 
        session: ConversationSession, 
        importance_threshold: float = 0.5
    ) -> str:
        """Extract core turns and save separately."""
        
        core_turns = session.extract_core_turns(importance_threshold)
        
        core_data = {
            "session_id": session.session_id,
            "extracted_at": datetime.now().isoformat(),
            "importance_threshold": importance_threshold,
            "original_turns": session.total_turns,
            "core_turns": len(core_turns),
            "turns": [asdict(t) for t in core_turns],
        }
        
        core_path = self.storage_dir / f"{session.session_id}_core.json"
        with open(core_path, 'w', encoding='utf-8') as f:
            json.dump(core_data, f, indent=2, ensure_ascii=False)
        
        return str(core_path)


def parse_chat_output(chat_text: str) -> List[Dict]:
    """
    Parse raw chat output into turns.
    
    Expects format like:
        α: user input
        ω: model response
        [XX%] tension=X.XX | DOMINANT
    """
    turns = []
    lines = chat_text.strip().split('\n')
    
    current_turn = {}
    current_section = None
    buffer = []
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('α:'):
            # Save previous turn if exists
            if current_turn and 'user_input' in current_turn:
                if buffer and current_section == 'response':
                    current_turn['model_response'] = '\n'.join(buffer)
                turns.append(current_turn)
            
            # Start new turn
            current_turn = {'user_input': line[2:].strip()}
            buffer = []
            current_section = 'input'
            
        elif line.startswith('ω:'):
            current_turn['model_response'] = line[2:].strip()
            buffer = [line[2:].strip()]
            current_section = 'response'
            
        elif line.startswith('[') and '%]' in line:
            # Metrics line
            # Parse: [XX%] tension=X.XX | DOMINANT
            try:
                cert_match = line.split('%')[0].replace('[', '').strip()
                current_turn['certainty'] = float(cert_match) / 100
                
                if 'tension=' in line:
                    tension_part = line.split('tension=')[1].split()[0]
                    current_turn['tension'] = float(tension_part)
                
                if '|' in line:
                    after_pipe = line.split('|')[-1].strip()
                    if '∅' in after_pipe or 'UNDEFINED' in after_pipe:
                        current_turn['dominant'] = 'UNDEFINED'
                    elif '✓' in after_pipe or 'TRUE' in after_pipe:
                        current_turn['dominant'] = 'TRUE'
                    elif '✗' in after_pipe or 'FALSE' in after_pipe:
                        current_turn['dominant'] = 'FALSE'
                    else:
                        current_turn['dominant'] = 'UNDEFINED'
                        
            except:
                pass
                
        elif '⚛' in line or 'entanglement confirmed' in line:
            current_turn['bell_entangled'] = True
            
        elif current_section == 'response' and line and not line.startswith('=') and not line.startswith('-'):
            buffer.append(line)
    
    # Save last turn
    if current_turn and 'user_input' in current_turn:
        if buffer and current_section == 'response':
            current_turn['model_response'] = '\n'.join(buffer)
        turns.append(current_turn)
    
    return turns


def create_session_from_chat(
    chat_text: str,
    provider: str = "ollama",
    model: str = "llama3.2",
    tags: List[str] = None,
) -> ConversationSession:
    """Create a session from raw chat output."""
    
    store = SessionStore()
    session = store.create_session(
        provider=provider,
        model=model,
        tags=tags or [],
    )
    
    turns_data = parse_chat_output(chat_text)
    
    for i, turn_data in enumerate(turns_data):
        turn = ConversationTurn(
            turn_number=i + 1,
            timestamp=datetime.now().isoformat(),
            user_input=turn_data.get('user_input', ''),
            model_response=turn_data.get('model_response', ''),
            certainty=turn_data.get('certainty', 0.5),
            tension=turn_data.get('tension', 0.5),
            coherence=turn_data.get('coherence', 0.5),
            entanglement=turn_data.get('entanglement', 0.5),
            dominant=turn_data.get('dominant', 'UNDEFINED'),
            novelty=turn_data.get('novelty', 1.0),
            bell_entangled=turn_data.get('bell_entangled', False),
            mode=turn_data.get('mode', 'NEUTRAL'),
        )
        session.add_turn(turn)
    
    return session
