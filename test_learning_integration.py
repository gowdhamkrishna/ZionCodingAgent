#!/usr/bin/env python3
"""
Quick test script for learning-enabled Zion agent.
Tests observation capture and learning system integration.
"""

import sys
import os

# Add the ai-agent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-agent'))

from core.learning_orchestrator import LearningOrchestrator
from rich.console import Console

console = Console()

def test_learning_system():
    """Test basic learning system functionality"""
    console.print("\n[bold cyan]=== Testing Learning System Integration ===[/bold cyan]\n")
    
    # Test 1: Initialize Learning Orchestrator
    console.print("[bold]Test 1: Initializing LearningOrchestrator...[/bold]")
    try:
        agent = LearningOrchestrator(
            base_dir=os.getcwd(),
            provider="ollama",
            model_name="qwen2.5-coder:7b",
            enable_learning=True
        )
        console.print("[green]✓ LearningOrchestrator initialized successfully[/green]")
    except Exception as e:
        console.print(f"[red]✗ Initialization failed: {e}[/red]")
        return False
    
    # Test 2: Check learner exists
    console.print("\n[bold]Test 2: Checking learning system...[/bold]")
    if hasattr(agent, 'learner') and agent.learner:
        console.print("[green]✓ Learning system active[/green]")
    else:
        console.print("[yellow]⚠ Learning system not active (may have failed to initialize)[/yellow]")
    
    # Test 3: Get learning stats
    console.print("\n[bold]Test 3: Getting learning statistics...[/bold]")
    try:
        stats = agent.get_learning_stats()
        console.print(f"[green]✓ Stats retrieved:[/green]")
        console.print(f"   - Total observations: {stats.get('total_observations', 0)}")
        console.print(f"   - Behavior clusters: {stats.get('behavior_clusters', 0)}")
        console.print(f"   - Learning enabled: {stats.get('learning_enabled', True)}")
    except Exception as e:
        console.print(f"[red]✗ Failed to get stats: {e}[/red]")
    
    # Test 4: Display stats panel
    console.print("\n[bold]Test 4: Displaying stats panel...[/bold]")
    try:
        agent.show_learning_stats()
        console.print("[green]✓ Stats panel displayed[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to display stats: {e}[/red]")
    
    # Test 5: Check database
    console.print("\n[bold]Test 5: Checking database...[/bold]")
    db_path = os.path.expanduser("~/.zion/learning.db")
    if os.path.exists(db_path):
        console.print(f"[green]✓ Database exists at {db_path}[/green]")
        size_kb = os.path.getsize(db_path) / 1024
        console.print(f"   - Size: {size_kb:.2f} KB")
    else:
        console.print(f"[yellow]⚠ Database not yet created (will be created on first observation)[/yellow]")
    
    console.print("\n[bold green]=== All Tests Complete ===[/bold green]\n")
    return True

if __name__ == "__main__":
    test_learning_system()
