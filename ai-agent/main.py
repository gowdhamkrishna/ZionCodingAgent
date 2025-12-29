import sys
import os
from core.orchestrator import AgentOrchestrator
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import questionary
from config import config
from utils.ui_components import show_welcome_banner, show_agent_header

console = Console()

ZION_BANNER = """
[bold cyan]
███████╗██╗ ██████╗ ███╗   ██╗
╚══███╔╝██║██╔═══██╗████╗  ██║
  ███╔╝ ██║██║   ██║██╔██╗ ██║
 ███╔╝  ██║██║   ██║██║╚██╗██║
███████╗██║╚██████╔╝██║ ╚████║
╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
       AGENT v1.0
[/bold cyan]
"""

def main():
    show_welcome_banner()
    
    # Provider Selection
    provider = questionary.select(
        "Select AI Provider",
        choices=["ollama", "gemini", "cerebras"],
        default=config.provider
    ).ask()
    
    if not provider: return
    
    # Model Selection
    if provider == "ollama":
        models = config.ollama_models
    elif provider == "gemini":
        models = config.gemini_models
    elif provider == "cerebras":
        models = config.cerebras_models
    else:
        models = config.ollama_models
    
    model_name = questionary.select(
        f"Select {provider.upper()} Model",
        choices=models,
        default=models[0]
    ).ask()
    
    if not model_name: return
    
    show_agent_header(provider=provider, model_name=model_name)
    
    # Auto-enable learning mode (silent)
    use_learning = True
    
    try:
        if use_learning:
            from core.learning_orchestrator import LearningOrchestrator
            agent = LearningOrchestrator(
                base_dir=os.getcwd(),
                provider=provider,
                model_name=model_name,
                enable_learning=True
            )
        else:
            agent = AgentOrchestrator(
                base_dir=os.getcwd(),
                provider=provider,
                model_name=model_name
            )
    except Exception as e:
        console.print(f"[bold red]Initialization Error: {e}[/bold red]")
        sys.exit(1)
    
    # Display learning status
    if hasattr(agent, 'enable_learning'):
        if agent.enable_learning and agent.learner:
            console.print("[green]✓[/green] Learning mode active", style="dim")
        elif agent.enable_learning and not agent.learner:
            console.print("[yellow]⚠[/yellow] Learning mode disabled (initialization failed)", style="dim")
    
    console.print(Panel.fit(
        "[bold green]System Online[/bold green]\n"
        "Listening for commands...",
        title="[bold cyan]Zion Agent[/bold cyan]",
        border_style="green"
    ))
    
    while True:
        try:
            user_input = console.input("\n[bold cyan]Zion User > [/bold cyan]")
            
            # Learning stats command
            if user_input.lower() == "/stats":
                if hasattr(agent, 'show_learning_stats'):
                    agent.show_learning_stats()
                else:
                    console.print("[yellow]Learning mode is not enabled[/yellow]")
                continue
            
            if user_input.lower() in ["exit", "quit"]:
                break
            
            if not user_input.strip():
                continue

            agent.run(user_input)
            
        except KeyboardInterrupt:
            console.print("\n[bold red]Exiting...[/bold red]")
            break
        except Exception as e:
            console.print(f"[bold red]An error occurred: {e}[/bold red]")

if __name__ == "__main__":
    main()
