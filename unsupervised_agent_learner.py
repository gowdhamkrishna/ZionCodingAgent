"""
Unsupervised Learning System for Self-Improving Coding Agent

This module implements a complete unsupervised learning system that enables
a coding agent to improve its behavior by discovering patterns in its own
actions and outcomes - without labeled data or manual intervention.

Key Components:
1. Observation capture and embedding
2. Behavior and outcome clustering
3. Failure pattern discovery
4. Correlation-based adaptation
5. Strategy effectiveness learning
6. Confidence estimation

Architecture: Distributional learning + correlation-based adaptation
Models: MiniBatchKMeans, HDBSCAN, sentence-transformers, GMM
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np
from collections import defaultdict
import json
import sqlite3
from pathlib import Path

# External dependencies (install via: pip install sentence-transformers scikit-learn hdbscan)
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import MiniBatchKMeans, KMeans
    from sklearn.mixture import GaussianMixture
    from hdbscan import HDBSCAN
except ImportError:
    print("WARNING: Required packages not installed. Run:")
    print("pip install sentence-transformers scikit-learn hdbscan")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class AgentObservation:
    """
    Single observation of agent behavior and outcome.
    This is the fundamental unit of learning - purely observational data.
    """
    
    # Identifiers
    observation_id: str
    timestamp: datetime
    session_id: str
    
    # Input Context
    user_prompt: str
    user_prompt_embedding: Optional[np.ndarray] = None
    context_size_tokens: int = 0
    context_file_count: int = 0
    
    # Agent Behavior
    generated_plan: str = ""
    generated_plan_embedding: Optional[np.ndarray] = None
    plan_length_tokens: int = 0
    plan_step_count: int = 0
    
    code_diffs: List[str] = field(default_factory=list)
    code_diff_embeddings: List[np.ndarray] = field(default_factory=list)
    total_lines_changed: int = 0
    files_modified_count: int = 0
    
    # Strategy Indicators (extracted features)
    used_incremental_edits: bool = False
    wrote_tests_first: bool = False
    used_type_hints: bool = False
    requested_user_clarification: bool = False
    
    # Execution Outcomes (Raw Signals - NOT labels)
    compiler_errors: List[str] = field(default_factory=list)
    compiler_error_embeddings: List[np.ndarray] = field(default_factory=list)
    
    lint_warnings: List[str] = field(default_factory=list)
    lint_warning_count: int = 0
    
    test_output: Optional[str] = None
    test_pass_count: int = 0
    test_fail_count: int = 0
    
    runtime_errors: List[str] = field(default_factory=list)
    runtime_error_embeddings: List[np.ndarray] = field(default_factory=list)
    
    # Retry Information
    retry_count: int = 0
    previous_attempt_ids: List[str] = field(default_factory=list)
    
    # Success Indicators (Observable, Not Labels)
    execution_completed: bool = False
    error_count_reduced: Optional[bool] = None
    user_accepted_changes: Optional[bool] = None
    
    # Derived Metrics (Computed from signals)
    outcome_score: float = 0.5  # 0-1, derived from observables
    
    # Clustering Assignments (Updated by learning system)
    behavior_cluster_id: Optional[int] = None
    outcome_cluster_id: Optional[int] = None
    failure_pattern_id: Optional[int] = None

    def to_dict(self) -> Dict:
        """Serialize for storage (excluding embeddings)"""
        return {
            'observation_id': self.observation_id,
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'user_prompt': self.user_prompt,
            'context_size_tokens': self.context_size_tokens,
            'context_file_count': self.context_file_count,
            'generated_plan': self.generated_plan,
            'plan_length_tokens': self.plan_length_tokens,
            'plan_step_count': self.plan_step_count,
            'code_diffs': self.code_diffs,
            'total_lines_changed': self.total_lines_changed,
            'files_modified_count': self.files_modified_count,
            'used_incremental_edits': self.used_incremental_edits,
            'wrote_tests_first': self.wrote_tests_first,
            'used_type_hints': self.used_type_hints,
            'requested_user_clarification': self.requested_user_clarification,
            'compiler_errors': self.compiler_errors,
            'lint_warnings': self.lint_warnings,
            'lint_warning_count': self.lint_warning_count,
            'test_output': self.test_output,
            'test_pass_count': self.test_pass_count,
            'test_fail_count': self.test_fail_count,
            'runtime_errors': self.runtime_errors,
            'retry_count': self.retry_count,
            'previous_attempt_ids': self.previous_attempt_ids,
            'execution_completed': self.execution_completed,
            'error_count_reduced': self.error_count_reduced,
            'user_accepted_changes': self.user_accepted_changes,
            'outcome_score': self.outcome_score,
            'behavior_cluster_id': self.behavior_cluster_id,
            'outcome_cluster_id': self.outcome_cluster_id,
            'failure_pattern_id': self.failure_pattern_id,
        }


# ============================================================================
# OUTCOME SCORING (From Raw Signals Only)
# ============================================================================

def compute_outcome_score(obs: AgentObservation) -> float:
    """
    Compute 0-1 score from observable signals only.
    This is NOT a label - it's a numerical summary of raw signals.
    
    The agent doesn't know what "good" means - it just observes:
    - Did it run without errors?
    - Did tests pass?
    - Did user accept changes?
    
    These are objective, observable facts.
    """
    score = 0.5  # neutral baseline
    
    # Positive signals
    if obs.execution_completed:
        score += 0.2
    if obs.test_pass_count > 0 and obs.test_fail_count == 0:
        score += 0.15
    if len(obs.compiler_errors) == 0:
        score += 0.1
    if obs.user_accepted_changes:
        score += 0.15
    if obs.error_count_reduced:
        score += 0.1
    
    # Negative signals
    if len(obs.compiler_errors) > 0:
        score -= 0.15
    if len(obs.runtime_errors) > 0:
        score -= 0.15
    if obs.retry_count > 3:
        score -= 0.1 * (obs.retry_count - 3)
    
    return np.clip(score, 0.0, 1.0)


# ============================================================================
# OBSERVATION DATABASE
# ============================================================================

class ObservationDatabase:
    """
    Storage for agent observations with efficient retrieval.
    Uses SQLite for structured data and numpy for embeddings.
    """
    
    def __init__(self, db_path: str = "./agent_observations.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
        
        # In-memory embedding cache
        self.embedding_cache = {}
    
    def _create_tables(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                observation_id TEXT PRIMARY KEY,
                timestamp TEXT,
                session_id TEXT,
                data TEXT,
                outcome_score REAL,
                behavior_cluster_id INTEGER,
                outcome_cluster_id INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON observations(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session 
            ON observations(session_id)
        """)
        
        self.conn.commit()
    
    def store(self, obs: AgentObservation):
        """Store observation"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO observations 
            (observation_id, timestamp, session_id, data, outcome_score, 
             behavior_cluster_id, outcome_cluster_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            obs.observation_id,
            obs.timestamp.isoformat(),
            obs.session_id,
            json.dumps(obs.to_dict()),
            obs.outcome_score,
            obs.behavior_cluster_id,
            obs.outcome_cluster_id
        ))
        
        self.conn.commit()
        
        # Cache embeddings
        if obs.user_prompt_embedding is not None:
            self.embedding_cache[obs.observation_id] = {
                'prompt': obs.user_prompt_embedding,
                'plan': obs.generated_plan_embedding,
                'diffs': obs.code_diff_embeddings
            }
    
    def get_all(self, limit: Optional[int] = None) -> List[AgentObservation]:
        """Retrieve all observations"""
        cursor = self.conn.cursor()
        
        query = "SELECT data FROM observations ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        
        observations = []
        for (data_json,) in cursor.fetchall():
            data = json.loads(data_json)
            obs = self._dict_to_observation(data)
            observations.append(obs)
        
        return observations
    
    def get_recent(self, days: int = 7) -> List[AgentObservation]:
        """Get observations from last N days"""
        cursor = self.conn.cursor()
        
        cutoff = datetime.now().timestamp() - (days * 86400)
        cursor.execute("""
            SELECT data FROM observations 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC
        """, (datetime.fromtimestamp(cutoff).isoformat(),))
        
        observations = []
        for (data_json,) in cursor.fetchall():
            data = json.loads(data_json)
            obs = self._dict_to_observation(data)
            observations.append(obs)
        
        return observations
    
    def find_similar(self, embedding: np.ndarray, k: int = 10) -> List[AgentObservation]:
        """Find k most similar observations by prompt embedding"""
        similarities = []
        
        for obs_id, embeddings in self.embedding_cache.items():
            prompt_emb = embeddings['prompt']
            if prompt_emb is not None:
                sim = np.dot(embedding, prompt_emb) / (
                    np.linalg.norm(embedding) * np.linalg.norm(prompt_emb)
                )
                similarities.append((obs_id, sim))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_k = similarities[:k]
        
        # Retrieve observations
        result = []
        for obs_id, _ in top_k:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT data FROM observations WHERE observation_id = ?",
                (obs_id,)
            )
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                obs = self._dict_to_observation(data)
                result.append(obs)
        
        return result
    
    def _dict_to_observation(self, data: Dict) -> AgentObservation:
        """Reconstruct observation from dict"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return AgentObservation(**data)
    
    def observation_count(self) -> int:
        """Total observation count"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM observations")
        return cursor.fetchone()[0]


# ============================================================================
# UNSUPERVISED LEARNER
# ============================================================================

class UnsupervisedAgentLearner:
    """
    Core unsupervised learning system.
    
    Learning Loop:
    1. Observe: Capture and embed agent behavior
    2. Cluster: Group similar behaviors and outcomes
    3. Discover: Find recurring failure patterns
    4. Correlate: Map behaviors to outcomes
    5. Analyze: Identify effective strategies
    6. Adapt: Generate recommendations
    """
    
    def __init__(
        self,
        db_path: str = "./agent_observations.db",
        n_behavior_clusters: int = 30,
        n_outcome_clusters: int = 5,
        min_samples_for_learning: int = 50
    ):
        # Embedding model
        print("Loading embedding model...")
        self.embed_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Clustering models
        self.behavior_clusterer = MiniBatchKMeans(
            n_clusters=n_behavior_clusters,
            batch_size=100,
            random_state=42
        )
        
        self.failure_clusterer = HDBSCAN(
            min_cluster_size=5,
            min_samples=3
        )
        
        self.outcome_clusterer = KMeans(
            n_clusters=n_outcome_clusters,
            random_state=42
        )
        
        # State
        self.observation_buffer = []
        self.behavior_outcome_correlations = np.zeros((n_behavior_clusters, n_outcome_clusters))
        self.behavior_quality_scores = np.zeros(n_behavior_clusters)
        self.failure_signatures = {}
        self.strategy_effectiveness = {}
        
        # Database
        self.db = ObservationDatabase(db_path)
        
        # Configuration
        self.min_samples = min_samples_for_learning
        self.n_behavior_clusters = n_behavior_clusters
        self.n_outcome_clusters = n_outcome_clusters
        
        # Tracking
        self.total_observations = 0
        self.last_learning_step = 0
    
    # ========================================================================
    # STEP 1: OBSERVE
    # ========================================================================
    
    def observe(self, observation: AgentObservation) -> AgentObservation:
        """
        Observe agent behavior and embed all textual components.
        This is the entry point for learning.
        """
        print(f"Observing: {observation.observation_id}")
        
        # Embed textual components
        observation.user_prompt_embedding = self.embed_model.encode(
            observation.user_prompt
        )
        
        if observation.generated_plan:
            observation.generated_plan_embedding = self.embed_model.encode(
                observation.generated_plan
            )
        
        if observation.code_diffs:
            observation.code_diff_embeddings = [
                self.embed_model.encode(diff) for diff in observation.code_diffs
            ]
        
        if observation.compiler_errors:
            observation.compiler_error_embeddings = [
                self.embed_model.encode(err) for err in observation.compiler_errors
            ]
        
        # Compute outcome score from raw signals
        observation.outcome_score = compute_outcome_score(observation)
        
        # Store
        self.observation_buffer.append(observation)
        self.db.store(observation)
        self.total_observations += 1
        
        print(f"  Outcome score: {observation.outcome_score:.2f}")
        
        return observation
    
    # ========================================================================
    # STEP 2: CLUSTER
    # ========================================================================
    
    def cluster_behaviors(self):
        """
        Cluster agent behaviors based on [prompt, plan, code] embeddings.
        Discovers groups of similar approaches to tasks.
        """
        if len(self.observation_buffer) < self.min_samples:
            print(f"Need {self.min_samples} samples for clustering (have {len(self.observation_buffer)})")
            return
        
        print("Clustering behaviors...")
        
        # Extract features
        behavior_features = []
        for obs in self.observation_buffer:
            # Concatenate: prompt + plan + avg(code_diffs)
            prompt_emb = obs.user_prompt_embedding
            plan_emb = obs.generated_plan_embedding if obs.generated_plan_embedding is not None else np.zeros_like(prompt_emb)
            
            if obs.code_diff_embeddings:
                avg_code_diff = np.mean(obs.code_diff_embeddings, axis=0)
            else:
                avg_code_diff = np.zeros_like(prompt_emb)
            
            feature = np.concatenate([prompt_emb, plan_emb, avg_code_diff])
            behavior_features.append(feature)
        
        behavior_features = np.array(behavior_features, dtype=np.float64)
        
        # Update clusters (incremental)
        self.behavior_clusterer.partial_fit(behavior_features)
        
        # Assign cluster IDs
        for obs, features in zip(self.observation_buffer, behavior_features):
            obs.behavior_cluster_id = int(
                self.behavior_clusterer.predict([features])[0]
            )
            self.db.store(obs)  # Update in database
        
        print(f"  Assigned {len(set(obs.behavior_cluster_id for obs in self.observation_buffer))} unique behavior clusters")
    
    def cluster_outcomes(self):
        """
        Cluster outcomes based on [outcome_score, retry_count, errors, tests].
        Discovers groups of similar result patterns.
        """
        if len(self.observation_buffer) < self.min_samples:
            return
        
        print("Clustering outcomes...")
        
        # Extract outcome features
        outcome_features = []
        for obs in self.observation_buffer:
            feature = [
                obs.outcome_score,
                min(obs.retry_count / 10.0, 1.0),  # normalized
                min(len(obs.compiler_errors) / 5.0, 1.0),  # normalized
                obs.test_pass_count / max(obs.test_pass_count + obs.test_fail_count, 1)
            ]
            outcome_features.append(feature)
        
        outcome_features = np.array(outcome_features, dtype=np.float64)
        
        # Fit outcome clusters
        self.outcome_clusterer.fit(outcome_features)
        
        # Assign cluster IDs
        for obs, features in zip(self.observation_buffer, outcome_features):
            obs.outcome_cluster_id = int(
                self.outcome_clusterer.predict([features])[0]
            )
            self.db.store(obs)
        
        print(f"  Assigned {len(set(obs.outcome_cluster_id for obs in self.observation_buffer))} unique outcome clusters")
    
    # ========================================================================
    # STEP 3: DISCOVER FAILURE PATTERNS
    # ========================================================================
    
    def discover_failure_patterns(self):
        """
        Use HDBSCAN to discover recurring failure patterns.
        No labels needed - just clusters similar error messages.
        """
        print("Discovering failure patterns...")
        
        # Collect all error embeddings
        error_embeddings = []
        error_metadata = []
        
        for obs in self.observation_buffer:
            for err, emb in zip(obs.compiler_errors, obs.compiler_error_embeddings):
                error_embeddings.append(emb)
                error_metadata.append({
                    'observation_id': obs.observation_id,
                    'error_text': err,
                    'behavior_cluster': obs.behavior_cluster_id
                })
        
        if len(error_embeddings) < 10:
            print("  Not enough errors for pattern discovery")
            return
        
        # Cluster errors
        error_embeddings = np.array(error_embeddings)
        labels = self.failure_clusterer.fit_predict(error_embeddings)
        
        # Build failure signatures
        pattern_groups = defaultdict(list)
        for label, metadata in zip(labels, error_metadata):
            if label != -1:  # -1 = outlier
                pattern_groups[label].append(metadata)
        
        # Update signatures
        for pattern_id, errors in pattern_groups.items():
            if pattern_id not in self.failure_signatures:
                self.failure_signatures[pattern_id] = {
                    'pattern_id': pattern_id,
                    'occurrences': 0,
                    'example_errors': [],
                    'associated_behaviors': []
                }
            
            sig = self.failure_signatures[pattern_id]
            sig['occurrences'] = len(errors)
            sig['example_errors'] = [e['error_text'] for e in errors[:3]]
            sig['associated_behaviors'] = [e['behavior_cluster'] for e in errors]
        
        print(f"  Discovered {len(self.failure_signatures)} failure patterns")
        for pattern_id, sig in self.failure_signatures.items():
            print(f"    Pattern {pattern_id}: {sig['occurrences']} occurrences")
    
    # ========================================================================
    # STEP 4: CORRELATE
    # ========================================================================
    
    def correlate_behaviors_to_outcomes(self):
        """
        Build correlation matrix: P(outcome | behavior)
        This is how the agent learns which behaviors lead to which outcomes.
        """
        if len(self.observation_buffer) < self.min_samples:
            return
        
        print("Correlating behaviors to outcomes...")
        
        # Build co-occurrence matrix
        cooccurrence = np.zeros((self.n_behavior_clusters, self.n_outcome_clusters))
        
        for obs in self.observation_buffer:
            if obs.behavior_cluster_id is not None and obs.outcome_cluster_id is not None:
                cooccurrence[obs.behavior_cluster_id, obs.outcome_cluster_id] += 1
        
        # Normalize to get conditional probabilities: P(outcome | behavior)
        row_sums = cooccurrence.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1  # avoid division by zero
        self.behavior_outcome_correlations = cooccurrence / row_sums
        
        # Compute quality score for each behavior cluster
        # Assume outcome clusters are ordered: 0=worst, 4=best
        outcome_weights = np.linspace(0.0, 1.0, self.n_outcome_clusters)
        
        behavior_quality_scores = []
        for b_id in range(self.n_behavior_clusters):
            quality_score = np.dot(
                self.behavior_outcome_correlations[b_id],
                outcome_weights
            )
            behavior_quality_scores.append(quality_score)
        
        self.behavior_quality_scores = np.array(behavior_quality_scores)
        
        # Print top and bottom behaviors
        top_5 = np.argsort(self.behavior_quality_scores)[-5:]
        bottom_5 = np.argsort(self.behavior_quality_scores)[:5]
        
        print(f"  Top 5 behavior clusters: {top_5.tolist()} (scores: {self.behavior_quality_scores[top_5]})")
        print(f"  Bottom 5 behavior clusters: {bottom_5.tolist()} (scores: {self.behavior_quality_scores[bottom_5]})")
    
    # ========================================================================
    # STEP 5: ANALYZE STRATEGIES
    # ========================================================================
    
    def analyze_strategies(self):
        """
        Discover which coding strategies correlate with success.
        Examples: incremental edits, test-first, type hints, asking for clarification
        """
        print("Analyzing strategy effectiveness...")
        
        # Group observations by strategy
        strategies = {
            'incremental_edits': [],
            'test_first': [],
            'type_hints': [],
            'ask_clarification': []
        }
        
        for obs in self.observation_buffer:
            if obs.used_incremental_edits:
                strategies['incremental_edits'].append(obs.outcome_score)
            if obs.wrote_tests_first:
                strategies['test_first'].append(obs.outcome_score)
            if obs.used_type_hints:
                strategies['type_hints'].append(obs.outcome_score)
            if obs.requested_user_clarification:
                strategies['ask_clarification'].append(obs.outcome_score)
        
        # Compute effectiveness
        for strategy_name, outcomes in strategies.items():
            if len(outcomes) >= 10:  # minimum sample size
                self.strategy_effectiveness[strategy_name] = {
                    'mean_outcome': np.mean(outcomes),
                    'std_outcome': np.std(outcomes),
                    'sample_size': len(outcomes)
                }
                print(f"  {strategy_name}: mean={np.mean(outcomes):.2f} (n={len(outcomes)})")
    
    # ========================================================================
    # STEP 6: ADAPT
    # ========================================================================
    
    def adapt(self, context: Dict) -> Dict:
        """
        Generate adaptation recommendations based on learned patterns.
        This is what the agent uses to modify its behavior.
        """
        recommendations = {
            'preferred_behavior_clusters': [],
            'avoid_behavior_clusters': [],
            'failure_warnings': [],
            'strategy_suggestions': [],
            'confidence_level': 1.0
        }
        
        # Only make recommendations if we have enough data
        if self.total_observations < self.min_samples:
            return recommendations
        
        # Recommend high-quality behavior clusters
        if len(self.behavior_quality_scores) > 0:
            top_behaviors = np.argsort(self.behavior_quality_scores)[-5:]
            bottom_behaviors = np.argsort(self.behavior_quality_scores)[:5]
            
            # Only recommend if we have evidence
            sample_counts = [
                int(self.behavior_outcome_correlations[b_id].sum() * 100)
                for b_id in top_behaviors
            ]
            
            recommendations['preferred_behavior_clusters'] = [
                {'cluster_id': int(b_id), 'quality_score': float(self.behavior_quality_scores[b_id])}
                for b_id, count in zip(top_behaviors, sample_counts)
                if count >= 10  # Only recommend if we have enough samples
            ]
            
            recommendations['avoid_behavior_clusters'] = [
                {'cluster_id': int(b_id), 'quality_score': float(self.behavior_quality_scores[b_id])}
                for b_id in bottom_behaviors
            ]
        
        # Check for known failure patterns
        if context.get('current_error'):
            error_emb = self.embed_model.encode(context['current_error'])
            
            # Find similar failure patterns
            for pattern_id, signature in self.failure_signatures.items():
                recommendations['failure_warnings'].append({
                    'pattern_id': int(pattern_id),
                    'occurrences': signature['occurrences'],
                    'example': signature['example_errors'][0] if signature['example_errors'] else '',
                    'suggestion': f'This error matches pattern #{pattern_id} seen {signature["occurrences"]} times'
                })
        
        # Suggest effective strategies
        for strategy, metrics in self.strategy_effectiveness.items():
            if metrics['mean_outcome'] > 0.7 and metrics['sample_size'] > 20:
                recommendations['strategy_suggestions'].append({
                    'strategy': strategy,
                    'effectiveness': float(metrics['mean_outcome']),
                    'confidence': min(metrics['sample_size'] / 100.0, 1.0)
                })
        
        return recommendations
    
    def estimate_confidence(self, current_plan: str, context: Dict) -> float:
        """
        Estimate confidence for a proposed plan based on variance in similar past attempts.
        High variance = low confidence (unstable pattern)
        Low variance = high confidence (stable pattern)
        """
        plan_emb = self.embed_model.encode(current_plan)
        
        # Find similar past observations
        similar_obs = self.db.find_similar(plan_emb, k=10)
        
        if len(similar_obs) < 3:
            return 0.5  # neutral confidence
        
        # Compute variance in outcomes
        outcomes = [obs.outcome_score for obs in similar_obs]
        variance = np.var(outcomes)
        mean_outcome = np.mean(outcomes)
        
        # High variance = low confidence
        # High mean = higher base confidence
        confidence = mean_outcome * (1.0 - min(variance * 2, 1.0))
        
        return float(confidence)
    
    # ========================================================================
    # FULL LEARNING LOOP
    # ========================================================================
    
    def learn_step(self):
        """
        Execute one complete learning iteration.
        This is called periodically (e.g., every 50 observations).
        """
        print("\n" + "="*60)
        print("LEARNING STEP")
        print("="*60)
        
        self.cluster_behaviors()
        self.cluster_outcomes()
        self.discover_failure_patterns()
        self.correlate_behaviors_to_outcomes()
        self.analyze_strategies()
        
        # Clear buffer after learning
        self.observation_buffer = []
        self.last_learning_step = self.total_observations
        
        print("="*60 + "\n")
    
    # ========================================================================
    # MONITORING & EXPLAINABILITY
    # ========================================================================
    
    def get_learning_state(self) -> Dict:
        """Get current learning state (for monitoring/debugging)"""
        return {
            'total_observations': self.total_observations,
            'observations_since_last_learning': len(self.observation_buffer),
            'behavior_clusters': self.n_behavior_clusters,
            'outcome_clusters': self.n_outcome_clusters,
            'failure_patterns_discovered': len(self.failure_signatures),
            'strategies_analyzed': len(self.strategy_effectiveness),
            'top_behaviors': [
                {
                    'cluster_id': int(i),
                    'quality_score': float(score)
                }
                for i, score in enumerate(self.behavior_quality_scores)
                if score > 0.7
            ][:10],
            'learned_strategies': self.strategy_effectiveness
        }
    
    def explain_recommendation(self, recommendation: Dict) -> str:
        """Generate human-readable explanation"""
        if 'cluster_id' in recommendation:
            cluster_id = recommendation['cluster_id']
            quality_score = recommendation.get('quality_score', 0)
            sample_count = int(self.behavior_outcome_correlations[cluster_id].sum() * 100)
            
            return f"""
Recommendation: Use behavior pattern #{cluster_id}
Reason: This behavior has shown {quality_score:.0%} success rate
        over {sample_count} observations.
Evidence: {self.behavior_outcome_correlations[cluster_id]}
            """.strip()
        
        return "No explanation available"


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """
    Demonstration of the unsupervised learning system.
    Shows how agent learns from observations without labels.
    """
    print("Initializing Unsupervised Agent Learner...")
    learner = UnsupervisedAgentLearner(
        db_path="./example_agent_learning.db",
        n_behavior_clusters=20,
        n_outcome_clusters=5,
        min_samples_for_learning=30
    )
    
    # Simulate observations
    print("\nSimulating agent observations...")
    
    for i in range(60):
        # Create synthetic observation
        obs = AgentObservation(
            observation_id=f"obs_{i}",
            timestamp=datetime.now(),
            session_id=f"session_{i // 10}",
            user_prompt=f"Implement feature {i % 5}",
            generated_plan=f"Plan for feature {i % 5} with {i % 3} steps",
            code_diffs=[f"diff_{i}"],
            total_lines_changed=10 + (i % 50),
            files_modified_count=1 + (i % 3),
            used_incremental_edits=(i % 2 == 0),  # 50% use incremental
            wrote_tests_first=(i % 3 == 0),  # 33% write tests first
            compiler_errors=[] if i % 4 != 0 else [f"Error in iteration {i}"],
            test_pass_count=5 if i % 4 != 0 else 0,
            test_fail_count=0 if i % 4 != 0 else 2,
            execution_completed=(i % 4 != 0),
            retry_count=0 if i % 4 != 0 else 2
        )
        
        # Observe
        learner.observe(obs)
        
        # Trigger learning every 30 observations
        if len(learner.observation_buffer) >= 30:
            learner.learn_step()
    
    # Get recommendations
    print("\nGenerating recommendations...")
    recommendations = learner.adapt({})
    
    print("\nLearned Recommendations:")
    print(json.dumps(recommendations, indent=2))
    
    # Get learning state
    print("\nLearning State:")
    state = learner.get_learning_state()
    print(json.dumps(state, indent=2))
    
    # Estimate confidence for a new plan
    confidence = learner.estimate_confidence(
        "Implement feature 2",
        {}
    )
    print(f"\nConfidence for new plan: {confidence:.2%}")


if __name__ == "__main__":
    example_usage()
