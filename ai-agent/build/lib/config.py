import os
import sys
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv, find_dotenv

# Try multiple strategies to find .env file
def load_environment_variables():
    loaded_from = None
    
    # Strategy 1: Search upward from CWD
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path, override=True)
        loaded_from = env_path
    
    # Strategy 2: Check user's home directory
    if not loaded_from:
        home_env = os.path.expanduser("~/.env")
        if os.path.exists(home_env):
            load_dotenv(home_env, override=True)
            loaded_from = home_env
    
    # Strategy 3: Check if ZION_ENV_FILE environment variable is set
    if not loaded_from:
        custom_env = os.getenv("ZION_ENV_FILE")
        if custom_env and os.path.exists(custom_env):
            load_dotenv(custom_env, override=True)
            loaded_from = custom_env
    
    if loaded_from:
        print(f"[Zion] Loaded environment from: {loaded_from}", file=sys.stderr)
    else:
        print("[Zion] No .env file found. API keys must be set via environment variables.", file=sys.stderr)
    
    return loaded_from

# Load environment variables on module import
load_environment_variables()

class Config(BaseModel):
    provider: str = os.getenv("AI_PROVIDER", "ollama")
    model_name: str = os.getenv("AGENT_MODEL", "qwen2.5-coder:7b")
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    cerebras_api_key: str = os.getenv("CEREBRAS_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    workspace_root: str = os.getcwd()
    
    # Model lists
    ollama_models: List[str] = ["qwen2.5-coder:7b", "llama3.1:8b", "codellama:7b", "mistral:7b"]
    gemini_models: List[str] = ["gemini-2.5-flash-lite", "gemini-2.0-flash-lite", "gemini-1.5-flash"]
    cerebras_models: List[str] = ["llama-3.3-70b", "llama-3.1-8b", "llama-3.1-70b"]

    def update_env_variable(self, key: str, value: str):
        """Updates or adds an environment variable to the current .env file."""
        # Update current process environment
        os.environ[key] = value
        setattr(self, key.lower(), value) # Update config instance attribute if it matches
        
        # Update .env file
        env_path = find_dotenv(usecwd=True) or os.path.expanduser("~/.env")
        if not os.path.exists(env_path):
             # If no .env exists, default to local .env
             env_path = os.path.join(self.workspace_root, ".env")
        
        # Read existing lines
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
        
        # Update or append
        key_found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                key_found = True
            else:
                new_lines.append(line)
        
        if not key_found:
            # Ensure newline before appending if file is not empty and doesn't end with newline
            if new_lines and not new_lines[-1].endswith('\n'):
                 new_lines[-1] += '\n'
            new_lines.append(f"{key}={value}\n")
            
        with open(env_path, "w") as f:
            f.writelines(new_lines)
            
        print(f"[Zion] Updated {key} in {env_path}", file=sys.stderr)

    def reload(self):
        """Reloads configuration from environment variables."""
        # Force reload from .env
        load_environment_variables()
        # Update instance variables
        self.provider = os.getenv("AI_PROVIDER", "ollama")
        self.model_name = os.getenv("AGENT_MODEL", "qwen2.5-coder:7b")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.cerebras_api_key = os.getenv("CEREBRAS_API_KEY", "")
        self.google_api_key = os.getenv("GOOGLE_API_KEY", "")


config = Config()
