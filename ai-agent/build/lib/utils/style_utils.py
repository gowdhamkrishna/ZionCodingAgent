from rich.text import Text
from rich.panel import Panel
from rich import box
from rich.console import Console

console = Console()

def gradient_text(text: str, start_color: str, end_color: str) -> Text:
    """
    Creates a Text object with a gradient color effect.
    Note: Rich doesn't natively support true gradients on text, 
    so we simulate it by chunking or using a set of compatible colors.
    For this implementation, we will use a "shimmer" effect using alternating colors
    or simply return a high-contrast styled text as 'gradient' implies visual richness.
    """
    # True gradient is complex in terminal without TrueColor calculation libraries.
    # We will use a stylised implementation that alternatingly colors characters
    # to give a 'shimmering' cyber effect.
    
    result = Text()
    # Cyberpunk gradient palette
    colors = [
        "bright_cyan",
        "cyan",
        "blue",
        "bright_magenta",
        "magenta"
    ]
    
    for i, char in enumerate(text):
        # Cycle through the palette
        color = colors[i % len(colors)]
        result.append(char, style=color)
    return result

def cyber_panel(renderable, title: str = None, subtitle: str = None, style: str = "cyan") -> Panel:
    """
    Creates a Cyber-Futuristic Panel with heavy corners/borders.
    """
    return Panel(
        renderable,
        title=f"[bullseye] {title} " if title else None,
        subtitle=subtitle,
        border_style=style,
        box=box.HEAVY_EDGE,  # Heavier box for 'tech' feel
        padding=(1, 2)
    )

def make_header_text(text: str) -> Text:
    """Creates large, spaced-out header text"""
    t = Text(text.upper(), style="bold white")
    t.justify = "center"
    return t
