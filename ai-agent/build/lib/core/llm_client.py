import ollama
import warnings
import os

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=FutureWarning)
# Also set environment variable to silence it if possible
os.environ["PYTHONWARNINGS"] = "ignore:All support for the `google.generativeai` package has ended:FutureWarning"

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from cerebras.cloud.sdk import Cerebras
except ImportError:
    Cerebras = None
from config import config
from typing import List, Dict, Any, Optional
import signal
import time

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("LLM request timed out")

class LLMClient:
    def __init__(self, provider: str = config.provider, model_name: str = config.model_name, timeout: int = 120):
        self.provider = provider
        self.model_name = model_name
        self.timeout = timeout
        
        if self.provider == "ollama":
            self.client = ollama.Client(host=config.base_url, timeout=timeout)
        elif self.provider == "gemini":
            if genai is None:
                raise ImportError("google-generativeai package not found. Install it to use Gemini.")
            if not config.google_api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")
            genai.configure(api_key=config.google_api_key)
            self.model = genai.GenerativeModel(self.model_name)
        elif self.provider == "cerebras":
            if Cerebras is None:
                raise ImportError("cerebras_cloud_sdk package not found. Install it to use Cerebras.")
            if not config.cerebras_api_key:
                raise ValueError("CEREBRAS_API_KEY not found in environment")
            self.client = Cerebras(api_key=config.cerebras_api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Sends a chat request to the selected provider with timeout.
        """
        if self.provider == "ollama":
            return self._chat_ollama(messages)
        elif self.provider == "gemini":
            return self._chat_gemini(messages)
        elif self.provider == "cerebras":
            return self._chat_cerebras(messages)
        return "Error: Unknown provider"

    def _chat_ollama(self, messages: List[Dict[str, str]]) -> str:
        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.timeout)
        
        try:
            response = self.client.chat(
                model=self.model_name, 
                messages=messages,
                options={
                    "num_predict": 4096,
                    "temperature": 0.3,
                }
            )
            signal.alarm(0)  # Cancel the alarm
            return response['message']['content']
        except TimeoutError:
            signal.alarm(0)
            return "Error: LLM request timed out. Please try again or check if ollama is running properly."
        except Exception as e:
            signal.alarm(0)
            print(f"Error communicating with Ollama: {e}")
            raise e
        finally:
            signal.signal(signal.SIGALRM, old_handler)

    def _chat_gemini(self, messages: List[Dict[str, str]]) -> str:
        # Convert messages to Gemini format
        # Gemini expects history [ {"role": "user/model", "parts": ["..."]}, ...]
        # And the last message is the prompt.
        
        history = []
        # Extract system prompt if present
        system_instruction = ""
        for msg in messages:
            if msg["role"] == "system":
                system_instruction += msg["content"] + "\n"
        
        # Filter system messages and convert Others
        chat_messages = [m for m in messages if m["role"] != "system"]
        
        # If we have system instructions, we should ideally use them.
        # Gemini 1.5+ supports system_instruction in initialization.
        if system_instruction:
            model = genai.GenerativeModel(self.model_name, system_instruction=system_instruction)
        else:
            model = self.model
            
        gemini_history = []
        for msg in chat_messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})
            
        last_msg = chat_messages[-1]["content"]
        
        try:
            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(last_msg)
            return response.text
        except Exception as e:
            print(f"Error communicating with Gemini: {e}")
            return f"Error communicating with Gemini: {str(e)}"

    def _chat_cerebras(self, messages: List[Dict[str, str]]) -> str:
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error communicating with Cerebras: {e}")
            return f"Error communicating with Cerebras: {str(e)}"

    def generate(self, prompt: str) -> str:
        """
        Simple generation (completion).
        """
        if self.provider == "ollama":
            return self._generate_ollama(prompt)
        elif self.provider == "gemini":
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Error generating with Gemini: {str(e)}"
        elif self.provider == "cerebras":
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model_name,
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                return f"Error generating with Cerebras: {str(e)}"
        return "Error: Unknown provider"

    def _generate_ollama(self, prompt: str) -> str:
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.timeout)
        
        try:
            response = self.client.generate(
                model=self.model_name, 
                prompt=prompt,
                options={
                    "num_predict": 4096,
                    "temperature": 0.3,
                }
            )
            signal.alarm(0)
            return response['response']
        except TimeoutError:
            signal.alarm(0)
            return "Error: LLM request timed out."
        except Exception as e:
            signal.alarm(0)
            print(f"Error generating text: {e}")
            raise e
        finally:
            signal.signal(signal.SIGALRM, old_handler)
