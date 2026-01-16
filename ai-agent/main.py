import sys
import os
from core.orchestrator import AgentOrchestrator
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import questionary
from config import config
from utils.ui_components import show_welcome_banner, show_agent_header
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

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


def configure_agent():
    """Interactive configuration menu."""
    while True:
        console.clear()
        show_welcome_banner()
        console.print(Panel("[bold yellow]Configuration Settings[/bold yellow]", style="yellow"))
        
        choice = questionary.select(
            "What would you like to configure?",
            choices=[
                "Set API Provider",
                "Set API Keys",
                "Select/Create .env File",
                "Back to Main Menu"
            ]
        ).ask()
        
        if choice == "Back to Main Menu":
            break
            
        elif choice == "Set API Provider":
            provider = questionary.select(
                "Select Default AI Provider",
                choices=["ollama", "gemini", "cerebras"],
                default=config.provider
            ).ask()
            if provider:
                config.update_env_variable("AI_PROVIDER", provider)
                console.print(f"[green]Provider set to {provider}[/green]")
                questionary.press_any_key_to_continue().ask()

        elif choice == "Set API Keys":
            key_choice = questionary.select(
                "Which API Key would you like to set?",
                choices=["Gemini API Key", "Cerebras API Key", "Ollama Base URL"]
            ).ask()
            
            if key_choice == "Gemini API Key":
                key = questionary.password("Enter Google API Key:").ask()
                if key:
                    config.update_env_variable("GOOGLE_API_KEY", key)
            elif key_choice == "Cerebras API Key":
                key = questionary.password("Enter Cerebras API Key:").ask()
                if key:
                    config.update_env_variable("CEREBRAS_API_KEY", key)
            elif key_choice == "Ollama Base URL":
                url = questionary.text("Enter Ollama Base URL:", default=config.base_url).ask()
                if url:
                    config.update_env_variable("OLLAMA_BASE_URL", url)
                    
        elif choice == "Select/Create .env File":
            # This is a basic implementation. Enhancing it would require file browsing.
            # For now, we stick to the current .env or allow creating a new one in CWD.
            action = questionary.select(
                "Environment File Management",
                choices=["Reload current .env", "Create new .env in current directory"]
            ).ask()
            
            if action == "Reload current .env":
                config.reload()
                console.print("[green]Configuration reloaded![/green]")
            elif action == "Create new .env in current directory":
                if os.path.exists(".env"):
                    overwrite = questionary.confirm("A .env file already exists. Overwrite?").ask()
                    if not overwrite:
                        continue
                with open(".env", "w") as f:
                    f.write("# Zion Agent Configuration\n")
                console.print("[green]New .env created.[/green]")
                config.reload()
            
            questionary.press_any_key_to_continue().ask()



def start_agent():
    """Starts the main agent loop."""
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
        questionary.press_any_key_to_continue().ask()
        return
    
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
    
    # Status Bar Logic
    def get_toolbar():
        learning_status = "ON" if use_learning else "OFF"
        return HTML(
            f' <b>Provider:</b> {provider} | <b>Model:</b> {model_name} | '
            f'<b>Learning:</b> {learning_status} | <b>CWD:</b> {os.path.basename(os.getcwd())} '
            f'| <b>Help:</b> /back, /stats, /clear'
        )

    # Custom Style
    style = Style.from_dict({
        'bottom-toolbar': '#333333 bg:#ccffcc',
    })

    session = PromptSession()

    while True:
        try:
            # Use prompt_toolkit for input
            user_input = session.prompt(
                HTML('<b><cyan>Zion User</cyan> &gt; </b>'),
                bottom_toolbar=get_toolbar,
                style=style
            )
            
            # Learning stats command
            if user_input.lower() == "/stats":
                if hasattr(agent, 'show_learning_stats'):
                    agent.show_learning_stats()
                else:
                    console.print("[yellow]Learning mode is not enabled[/yellow]")
                continue
            
            if user_input.lower() in ["exit", "quit", "/back"]:
                break
                
            # Magic commands
            if user_input.lower() == "/clear":
                console.clear()
                continue
                
            if user_input.lower() == "/config":
                console.print("[yellow]Switching to configuration (session will resume)...[/yellow]")
                configure_agent()
                show_agent_header(provider=provider, model_name=model_name) # Re-show header
                continue
            
            if not user_input.strip():
                continue

            agent.run(user_input)
            
        except KeyboardInterrupt:
            # In prompt_toolkit, Ctrl+C raises KeyboardInterrupt
            # We want to confirm exit or just break the loop
            console.print("\n[bold red]Stopping Agent...[/bold red]")
            break
        except EOFError:
             # Ctrl+D
             break
        except Exception as e:
            console.print(f"[bold red]An error occurred: {e}[/bold red]")

def main():
    while True:
        console.clear()
        show_welcome_banner()
        
        choice = questionary.select(
            "Main Menu",
            choices=[
                "Start Agent",
                "Configuration",
                "Exit"
            ]
        ).ask()
        
        if choice == "Start Agent":
            start_agent()
        elif choice == "Configuration":
            configure_agent()
        elif choice == "Exit":
            console.print("[bold cyan]Goodbye![/bold cyan]")
            sys.exit(0)

if __name__ == "__main__":
    main()
