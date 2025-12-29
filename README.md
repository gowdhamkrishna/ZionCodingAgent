# Zion AI Coding Agent 🚀

A powerful, self-improving AI coding assistant with unsupervised learning capabilities. Zion learns from its own experiences to become better over time without human labels or supervision.

![Version](https://img.shields.io/badge/version-2.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.8+-yellow)

## ✨ Features

### 🧠 **Unsupervised Learning System**
- **Self-Improving**: Learns from every task without manual supervision
- **Pattern Discovery**: Automatically identifies successful behavior patterns
- **Failure Learning**: Clusters and learns from errors to avoid repeating mistakes
- **Strategy Effectiveness**: Tracks which coding strategies work best
- **Incremental Learning**: Updates models continuously as new data arrives

### 🎯 **Multi-Provider AI Support**
- **Ollama** - Local LLM inference (qwen2.5-coder, llama3.1, codellama, mistral)
- **Google Gemini** - Cloud-based (gemini-2.5-flash-lite, gemini-2.0-flash-lite, gemini-1.5-flash)
- **Cerebras** - Ultra-fast inference (llama-3.3-70b, llama-3.1-8b, llama-3.1-70b)

### 💻 **Developer Experience**
- **Beautiful CLI** - Rich terminal UI with animations and progress indicators
- **Smart Context** - Intelligent file focusing and context management
- **Version Control** - Built-in undo/redo for all file changes
- **Shell Integration** - Direct command execution from within the agent
- **Multi-line Input** - Paste mode for complex requests
- **Task Cancellation** - Ctrl+C to stop any running task

### 🛠️ **Intelligent Tools**
- File operations (read, write, edit, patch)
- Directory navigation and search
- Command execution with output capture
- Context-aware file focusing
- Smart loop detection and intervention

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pipx (recommended) or pip
- Git

### Quick Install

```bash
# Clone the repository
git clone https://github.com/gowdhamkrishna/ZionCodingAgent.git
cd ZionCodingAgent/ai-agent

# Install using pipx (recommended)
pipx install -e .

# Or install learning dependencies
pipx inject zion-agent sentence-transformers scikit-learn hdbscan numpy

# Verify installation
zion --help
```

### Environment Setup

Create a `.env` file in your project root:

```env
# Choose your provider
AI_PROVIDER=cerebras  # or ollama, gemini

# API Keys (if using cloud providers)
CEREBRAS_API_KEY=your_cerebras_key_here
GOOGLE_API_KEY=your_google_key_here

# Ollama settings (if using local)
OLLAMA_BASE_URL=http://localhost:11434
AGENT_MODEL=qwen2.5-coder:7b
```

## 🚀 Usage

### Starting Zion

```bash
# Launch the agent
zion

# Select your AI provider (ollama/gemini/cerebras)
# Select your model
# Start coding!
```

### Available Commands

| Command | Description |
|---------|-------------|
| `paste` | Multi-line input mode |
| `$` or `shell` | Interactive shell mode |
| `new` | Start fresh chat session |
| `undo` | Restore previous version |
| `clear` | Clear screen |
| `Ctrl+C` | Cancel running task |
| `/stats` | View learning statistics |
| `exit` | Quit Zion |

### Example Interactions

```
❯ Create a Python web scraper for news articles

❯ Add error handling and retry logic to the scraper

❯ Write unit tests for the scraper functions

❯ /stats  # View what Zion has learned
```

## 🧠 Learning System

Zion's unsupervised learning system works by:

1. **Observation Capture** - Records every task: prompt, plan, code changes, outcomes
2. **Behavior Clustering** - Groups similar approaches using embeddings
3. **Outcome Analysis** - Clusters results (success/failure patterns)
4. **Correlation Discovery** - Maps which behaviors lead to which outcomes
5. **Strategy Learning** - Identifies effective coding strategies
6. **Adaptation** - Adjusts behavior based on learned patterns

### Learning Statistics

Use the `/stats` command to see:
- Total observations collected
- Number of behavior clusters discovered
- Failure patterns identified
- Strategies learned and their effectiveness
- Model confidence scores

## 🏗️ Architecture

```
Zion Coding Agent
│
├── Core
│   ├── LLM Client (Multi-provider support)
│   ├── Orchestrator (Main agent loop)
│   ├── Learning Orchestrator (Observation wrapper)
│   ├── Memory (Conversation history)
│   ├── Context Manager (File focusing)
│   └── Version Manager (Undo/redo)
│
├── Learning System
│   ├── Unsupervised Learner (Pattern discovery)
│   ├── Observation Database (SQLite storage)
│   ├── Clustering Models (Behavior/Outcome)
│   └── Strategy Analyzer (Effectiveness tracking)
│
├── Tools
│   ├── Filesystem (read, write, edit, patch, search)
│   ├── Shell (command execution)
│   └── Context (file focusing)
│
└── UI
    ├── Rich Terminal (Beautiful CLI)
    ├── Progress Indicators (Spinners, status)
    └── Protected Prompt (No backspace bugs)
```

## 📊 Learning Data

All learning data is stored in:
```
~/.zion/learning.db
```

The database contains:
- Observation records
- Embeddings (cached in memory)
- Cluster assignments
- Strategy metrics

## 🎨 UI Features

- **Thinking Animation** - 🤔 Animated spinner during processing
- **Task Completion** - ✓ Styled completion panel
- **Error Display** - Clear, color-coded error messages
- **Code Previews** - Syntax-highlighted diffs
- **Protected Prompt** - Can't accidentally delete the ❯ symbol

## 🔧 Configuration

### Provider Selection

Choose your AI provider based on your needs:

**Ollama** (Local)
- ✅ Complete privacy
- ✅ No API costs
- ✅ Fast for local models
- ❌ Requires local setup

**Gemini** (Cloud)
- ✅ Powerful models
- ✅ No local resources needed
- ✅ Fast inference
- ❌ Requires API key

**Cerebras** (Cloud)
- ✅ Ultra-fast inference
- ✅ Large context windows
- ✅ Competitive pricing
- ❌ Requires API key

### Model Recommendations

| Task | Recommended Model |
|------|-------------------|
| Code Generation | qwen2.5-coder:7b, llama-3.3-70b |
| Quick Fixes | gemini-2.5-flash-lite |
| Complex Refactoring | llama-3.1-70b |
| Fast Iteration | cerebras llama-3.3-70b |

## 🛣️ Roadmap

- [ ] Web UI with real-time learning visualization
- [ ] Multi-agent collaboration
- [ ] Code review agent mode
- [ ] Proactive suggestion system
- [ ] Integration with popular IDEs
- [ ] Advanced recommendation injection
- [ ] Distributed learning across multiple agents

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal UI
- Powered by [sentence-transformers](https://www.sbert.net/) for embeddings
- Uses [HDBSCAN](https://github.com/scikit-learn-contrib/hdbscan) for density-based clustering
- Inspired by the vision of self-improving AI systems

## 📧 Contact

Created by [@gowdhamkrishna](https://github.com/gowdhamkrishna)

---

**Made with ❤️ and AI** | **Star ⭐ if you find it useful!**
