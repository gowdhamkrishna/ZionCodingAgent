"""
Learning-Enabled Orchestrator for Zion Agent

Wraps the standard AgentOrchestrator with unsupervised learning capabilities.
Captures observations during execution and learns from patterns over time.
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel

from core.orchestrator import AgentOrchestrator
from core.learning_system import (
    UnsupervisedAgentLearner,
    AgentObservation,
    compute_outcome_score
)

console = Console()


def generate_id():
    """Generate unique observation ID"""
    return str(uuid.uuid4())[:8]


class LearningOrchestrator:
    """
    Wrapper around AgentOrchestrator that adds unsupervised learning.
    
    Captures observations at key points:
    1. Before planning: Get recommendations
    2. After planning: Estimate confidence
    3. After execution: Capture outcomes
    4. During retries: Check failure patterns
    5. Periodic: Trigger learning cycles
    """
    
    def __init__(
        self,
        base_dir: str = None,
        provider: str = None,
        model_name: str = None,
        enable_approvals: bool = False,
        enable_learning: bool = True
    ):
        # Wrap the original orchestrator
        self.orchestrator = AgentOrchestrator(
            base_dir=base_dir,
            provider=provider,
            model_name=model_name,
            enable_approvals=enable_approvals
        )
        
        # Initialize learning system
        self.enable_learning = enable_learning
        if enable_learning:
            try:
                self.learner = UnsupervisedAgentLearner(
                    db_path=os.path.expanduser("~/.zion/learning.db"),
                    n_behavior_clusters=20,
                    n_outcome_clusters=5,
                    min_samples_for_learning=30
                )
                console.print("[dim green]✓ Learning system initialized[/dim green]")
            except Exception as e:
                console.print(f"[dim red]✗ Learning initialization failed: {e}[/dim red]")
                self.learner = None
                self.enable_learning = False
        else:
            self.learner = None
        
        # Session tracking
        self.session_id = generate_id()
        self.current_observation = None
        self.task_start_time = None
    
    def _create_observation(self, message: str) -> AgentObservation:
        """Create a new observation for the current task"""
        # Get context file count safely
        context_files = 0
        try:
            if hasattr(self.orchestrator.context_manager, 'focused_files'):
                context_files = len(self.orchestrator.context_manager.focused_files)
        except:
            context_files = 0
        
        return AgentObservation(
            observation_id=generate_id(),
            timestamp=datetime.now(),
            session_id=self.session_id,
            user_prompt=message,
            context_size_tokens=len(str(self.orchestrator.memory.get_messages())),
            context_file_count=context_files
        )
    
    def _extract_strategy_indicators(self, observation: AgentObservation):
        """Extract Zion-specific strategy indicators from execution"""
        
        # Check for incremental edits (small changes)
        observation.used_incremental_edits = (
            observation.files_modified_count <= 2 and
            observation.total_lines_changed < 50
        )
        
        # Check for test-first pattern
        observation.wrote_tests_first = any(
            'test_' in diff or 'Test' in diff 
            for diff in observation.code_diffs
        )
        
        # Check for type hints usage
        observation.used_type_hints = any(
            '->' in diff or ': str' in diff or ': int' in diff
            for diff in observation.code_diffs
        )
        
        # Check for clarification requests
        observation.requested_user_clarification = False  # TODO: detect from plan
    
    def _populate_observation_outcomes(self):
        """Capture outcomes from orchestrator execution"""
        if not self.current_observation:
            return
        
        obs = self.current_observation
        
        # Capture execution results
        obs.execution_completed = (self.orchestrator.status == "idle")
        
        # Capture plan information
        if hasattr(self.orchestrator, 'plan') and self.orchestrator.plan:
            obs.generated_plan = str(self.orchestrator.plan)
            obs.plan_length_tokens = len(obs.generated_plan)
        
        # Count tool calls as plan steps
        obs.plan_step_count = len(getattr(self.orchestrator, 'tool_history', []))
        
        # Capture file modifications
        obs.files_modified_count = len(set(
            call.split(':')[1].split('"file_path":"')[1].split('"')[0]
            if '"file_path":"' in call else ''
            for call in getattr(self.orchestrator, 'tool_history', [])
            if 'write_file' in call or 'edit_file' in call
        ))
        
        # Extract code diffs (simplified - could be enhanced)
        obs.code_diffs = [
            f"Modified via {call.split(':')[0]}"
            for call in getattr(self.orchestrator, 'tool_history', [])
            if 'write_file' in call or 'edit_file' in call
        ]
        
        # Estimate lines changed (rough estimate)
        obs.total_lines_changed = obs.files_modified_count * 20  # Rough estimate
        
        # Extract strategy indicators
        self._extract_strategy_indicators(obs)
        
        # Compute outcome score
        obs.outcome_score = compute_outcome_score(obs)
    
    def run(self, message: str):
        """
        Main execution loop with learning integration.
        
        Captures observations before, during, and after execution.
        """
        self.task_start_time = datetime.now()
        
        # === BEFORE PLANNING ===
        if self.enable_learning and self.learner:
            try:
                # Get learned recommendations (silent)
                context = {'user_prompt': message}
                recommendations = self.learner.adapt(context)
                # TODO: Inject recommendations into orchestrator context
            except Exception as e:
                pass  # Silent failure
        
        # Start observation
        if self.enable_learning:
            self.current_observation = self._create_observation(message)
        
        # === EXECUTE ORIGINAL ORCHESTRATOR ===
        try:
            result = self.orchestrator.run(message)
        except Exception as e:
            # Capture error in observation
            if self.enable_learning and self.current_observation:
                self.current_observation.runtime_errors = [str(e)]
                self.current_observation.execution_completed = False
            raise
        
        # === AFTER EXECUTION ===
        if self.enable_learning and self.learner and self.current_observation:
            try:
                # Populate outcomes
                self._populate_observation_outcomes()
                
                # Observe and potentially learn (silent)
                self.learner.observe(self.current_observation)
                
                # Trigger learning every 30 observations (silent)
                if len(self.learner.observation_buffer) >= 30:
                    self.learner.learn_step()
                
            except Exception as e:
                pass  # Silent failure
        
        return result
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get current learning statistics"""
        if not self.enable_learning or not self.learner:
            return {"learning_enabled": False}
        
        try:
            return self.learner.get_learning_state()
        except Exception as e:
            return {"error": str(e)}
    
    def show_learning_stats(self):
        """Display learning statistics in a nice panel"""
        if not self.enable_learning or not self.learner:
            console.print("[yellow]Learning mode is disabled[/yellow]")
            return
        
        stats = self.get_learning_stats()
        
        info_lines = [
            f"📊 Total Observations: {stats.get('total_observations', 0)}",
            f"🔍 Behavior Clusters: {stats.get('behavior_clusters', 0)}",
            f"⚠️  Failure Patterns: {stats.get('failure_patterns_discovered', 0)}",
            f"💡 Strategies Analyzed: {stats.get('strategies_analyzed', 0)}",
        ]
        
        # Add learned strategies
        learned_strategies = stats.get('learned_strategies', {})
        if learned_strategies:
            info_lines.append("\n[bold]Learned Strategies:[/bold]")
            for strategy, metrics in learned_strategies.items():
                effectiveness = metrics.get('mean_outcome', 0)
                sample_size = metrics.get('sample_size', 0)
                info_lines.append(
                    f"  • {strategy}: {effectiveness:.0%} effective (n={sample_size})"
                )
        
        console.print(Panel(
            "\n".join(info_lines),
            title="[bold cyan]Learning System Statistics[/bold cyan]",
            border_style="cyan"
        ))
    
    # Delegate all other attributes to the wrapped orchestrator
    def __getattr__(self, name):
        """Delegate unknown attributes to the wrapped orchestrator"""
        return getattr(self.orchestrator, name)
