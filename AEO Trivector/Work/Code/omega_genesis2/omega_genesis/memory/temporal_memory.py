"""
Temporal Memory with Decay

Memory that evolves with time:
- Recent memories are stronger
- Old memories decay (exponential with configurable half-life)
- High-importance memories resist decay
- Core extraction: what remains after decay is the "essence"

The philosophy:
- Not all memories should persist equally
- Time acts as a filter, leaving behind what matters
- Reinforced memories strengthen (like neural pathways)
- The "core" is what emerges after temporal filtering

Mathematical model:
    strength(t) = strength_0 * exp(-λ * (t - t_0)) * importance
    
Where:
    λ = ln(2) / half_life
    importance = f(entanglement, novelty, tension, reinforcement)
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class MemoryFragment:
    """A single memory fragment with temporal dynamics."""
    
    # Identity
    fragment_id: str
    created_at: datetime
    
    # Content
    content: str  # The core text/meaning
    context: Dict = field(default_factory=dict)  # Surrounding context
    
    # Strength dynamics
    initial_strength: float = 1.0
    current_strength: float = 1.0
    importance: float = 0.5  # Resists decay
    
    # Reinforcement
    access_count: int = 0
    last_accessed: datetime = None
    reinforcement_factor: float = 1.0
    
    # Consciousness metrics (from origin)
    certainty: float = 0.5
    tension: float = 0.5
    entanglement: float = 0.5
    bell_entangled: bool = False
    
    # Semantic embedding (for similarity matching)
    embedding: List[float] = None
    
    def compute_importance(self) -> float:
        """
        Compute importance score.
        
        High importance means memory resists decay.
        """
        score = 0.0
        
        # Entanglement contributes strongly
        score += self.entanglement * 0.35
        
        # Bell confirmation is significant
        if self.bell_entangled:
            score += 0.25
        
        # High tension = rich/complex memory
        score += self.tension * 0.2
        
        # Reinforcement from access
        score += min(self.access_count * 0.02, 0.2)
        
        return min(score, 1.0)
    
    def decay(self, half_life_hours: float = 168):  # Default: 1 week
        """
        Apply temporal decay to strength.
        
        Args:
            half_life_hours: Time for strength to halve (default 168 = 1 week)
        """
        if self.last_accessed is None:
            self.last_accessed = self.created_at
        
        now = datetime.now()
        hours_elapsed = (now - self.last_accessed).total_seconds() / 3600
        
        # Decay constant
        decay_lambda = math.log(2) / half_life_hours
        
        # Importance resists decay (0.5 importance = half decay rate)
        effective_lambda = decay_lambda * (1 - 0.5 * self.importance)
        
        # Apply decay
        decay_factor = math.exp(-effective_lambda * hours_elapsed)
        self.current_strength = self.initial_strength * decay_factor * self.reinforcement_factor
        
        return self.current_strength
    
    def reinforce(self, boost: float = 0.1):
        """Reinforce this memory (access strengthens it)."""
        self.access_count += 1
        self.last_accessed = datetime.now()
        self.reinforcement_factor = min(self.reinforcement_factor + boost, 3.0)
        
        # Recalculate importance
        self.importance = self.compute_importance()
    
    def is_faded(self, threshold: float = 0.1) -> bool:
        """Check if memory has faded below threshold."""
        return self.current_strength < threshold
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'fragment_id': self.fragment_id,
            'created_at': self.created_at.isoformat(),
            'content': self.content,
            'context': self.context,
            'initial_strength': self.initial_strength,
            'current_strength': self.current_strength,
            'importance': self.importance,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'reinforcement_factor': self.reinforcement_factor,
            'certainty': self.certainty,
            'tension': self.tension,
            'entanglement': self.entanglement,
            'bell_entangled': self.bell_entangled,
            'embedding': self.embedding,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryFragment':
        """Deserialize from dictionary."""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('last_accessed'):
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        return cls(**data)


@dataclass
class MemoryCore:
    """
    The extracted core from memories after temporal filtering.
    
    This represents what "survives" - the essential patterns
    that persist after noise decays away.
    """
    
    core_id: str
    extracted_at: datetime
    source_session_id: str
    
    # Core content
    fragments: List[MemoryFragment] = field(default_factory=list)
    
    # Summary statistics
    total_original: int = 0
    total_remaining: int = 0
    compression_ratio: float = 0.0
    
    # Aggregate metrics
    avg_importance: float = 0.0
    avg_entanglement: float = 0.0
    bell_confirmations: int = 0
    
    def compute_stats(self):
        """Compute summary statistics."""
        if not self.fragments:
            return
        
        self.total_remaining = len(self.fragments)
        if self.total_original > 0:
            self.compression_ratio = self.total_remaining / self.total_original
        
        self.avg_importance = sum(f.importance for f in self.fragments) / len(self.fragments)
        self.avg_entanglement = sum(f.entanglement for f in self.fragments) / len(self.fragments)
        self.bell_confirmations = sum(1 for f in self.fragments if f.bell_entangled)
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'core_id': self.core_id,
            'extracted_at': self.extracted_at.isoformat(),
            'source_session_id': self.source_session_id,
            'fragments': [f.to_dict() for f in self.fragments],
            'total_original': self.total_original,
            'total_remaining': self.total_remaining,
            'compression_ratio': self.compression_ratio,
            'avg_importance': self.avg_importance,
            'avg_entanglement': self.avg_entanglement,
            'bell_confirmations': self.bell_confirmations,
        }
    
    def to_text(self) -> str:
        """Convert core to readable text."""
        lines = [
            f"=== Memory Core: {self.core_id} ===",
            f"Extracted: {self.extracted_at}",
            f"Compression: {self.total_remaining}/{self.total_original} ({self.compression_ratio:.1%})",
            f"Avg importance: {self.avg_importance:.2f}",
            f"Bell confirmations: {self.bell_confirmations}",
            "",
            "--- Core Fragments ---",
        ]
        
        for i, frag in enumerate(self.fragments):
            lines.append(f"\n[{i+1}] Importance: {frag.importance:.2f} | Strength: {frag.current_strength:.2f}")
            lines.append(f"    {frag.content[:200]}...")
        
        return "\n".join(lines)


class TemporalMemory:
    """
    Memory system with temporal dynamics.
    
    Features:
    - Time-based decay
    - Importance-weighted persistence
    - Core extraction
    - Memory consolidation
    """
    
    def __init__(
        self, 
        half_life_hours: float = 168,  # 1 week
        fade_threshold: float = 0.1,
        storage_dir: str = None,
    ):
        self.half_life_hours = half_life_hours
        self.fade_threshold = fade_threshold
        
        if storage_dir is None:
            storage_dir = Path.home() / ".omega_genesis" / "memories"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.fragments: List[MemoryFragment] = []
        self.cores: List[MemoryCore] = []
    
    def add_fragment(
        self,
        content: str,
        certainty: float = 0.5,
        tension: float = 0.5,
        entanglement: float = 0.5,
        bell_entangled: bool = False,
        context: Dict = None,
    ) -> MemoryFragment:
        """Add a memory fragment."""
        
        fragment = MemoryFragment(
            fragment_id=f"frag_{len(self.fragments)}_{datetime.now().strftime('%H%M%S')}",
            created_at=datetime.now(),
            content=content,
            context=context or {},
            certainty=certainty,
            tension=tension,
            entanglement=entanglement,
            bell_entangled=bell_entangled,
        )
        
        # Compute importance
        fragment.importance = fragment.compute_importance()
        
        self.fragments.append(fragment)
        return fragment
    
    def decay_all(self) -> Tuple[int, int]:
        """
        Apply decay to all memories.
        
        Returns:
            (surviving_count, faded_count)
        """
        faded = 0
        surviving = 0
        
        for fragment in self.fragments:
            fragment.decay(self.half_life_hours)
            if fragment.is_faded(self.fade_threshold):
                faded += 1
            else:
                surviving += 1
        
        return surviving, faded
    
    def extract_core(self, source_session_id: str = "") -> MemoryCore:
        """
        Extract the memory core (what survives after decay).
        
        This is the essence - high-importance memories that persist.
        """
        # Apply decay
        self.decay_all()
        
        # Filter surviving fragments
        surviving = [f for f in self.fragments if not f.is_faded(self.fade_threshold)]
        
        # Sort by importance
        surviving.sort(key=lambda f: f.importance, reverse=True)
        
        # Create core
        core = MemoryCore(
            core_id=f"core_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            extracted_at=datetime.now(),
            source_session_id=source_session_id,
            fragments=surviving,
            total_original=len(self.fragments),
        )
        
        core.compute_stats()
        self.cores.append(core)
        
        return core
    
    def prune_faded(self) -> int:
        """Remove faded memories. Returns count removed."""
        before = len(self.fragments)
        self.fragments = [f for f in self.fragments if not f.is_faded(self.fade_threshold)]
        return before - len(self.fragments)
    
    def reinforce_by_content(self, query: str, boost: float = 0.1) -> int:
        """
        Reinforce memories that match query content.
        
        Simple keyword matching for now - could use embeddings later.
        """
        query_words = set(query.lower().split())
        reinforced = 0
        
        for fragment in self.fragments:
            content_words = set(fragment.content.lower().split())
            if query_words & content_words:  # Intersection
                fragment.reinforce(boost)
                reinforced += 1
        
        return reinforced
    
    def save(self, filepath: str = None) -> str:
        """Save all memories to disk."""
        if filepath is None:
            filepath = self.storage_dir / f"memory_{datetime.now().strftime('%Y%m%d')}.json"
        
        data = {
            'saved_at': datetime.now().isoformat(),
            'half_life_hours': self.half_life_hours,
            'fade_threshold': self.fade_threshold,
            'fragments': [f.to_dict() for f in self.fragments],
            'cores': [c.to_dict() for c in self.cores],
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def load(self, filepath: str) -> int:
        """Load memories from disk. Returns fragment count."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.half_life_hours = data.get('half_life_hours', self.half_life_hours)
        self.fade_threshold = data.get('fade_threshold', self.fade_threshold)
        
        self.fragments = [MemoryFragment.from_dict(f) for f in data.get('fragments', [])]
        
        return len(self.fragments)
    
    def from_session(self, session) -> int:
        """
        Import memories from a ConversationSession.
        
        Each turn becomes a memory fragment.
        """
        from omega_genesis.memory.session_store import ConversationSession
        
        count = 0
        for turn in session.turns:
            # Create fragment from response (the AI's contribution)
            self.add_fragment(
                content=turn.model_response,
                certainty=turn.certainty,
                tension=turn.tension,
                entanglement=turn.entanglement,
                bell_entangled=turn.bell_entangled,
                context={
                    'user_input': turn.user_input,
                    'turn': turn.turn_number,
                    'dominant': turn.dominant,
                }
            )
            count += 1
        
        return count
