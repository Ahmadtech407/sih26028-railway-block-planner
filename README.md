# 🚂 Indian Railways AI Section Controller & Block Planner (SIH26028)

An AI-powered railway track maintenance block scheduling system built with
**Google Antigravity SDK** and **Google OR-Tools CP-SAT Solver**.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│              Google Antigravity Agent                 │
│    (Gemini LLM - Reasoning, Orchestration, NLP)      │
├──────────────────────────────────────────────────────┤
│  Custom Tools                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ query_section│  │ check_track  │  │  commit    │ │
│  │ _status      │  │ _conflicts   │  │  _block    │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
│  ┌──────────────────────────────────────────────────┐│
│  │      run_or_tools_block_optimizer                ││
│  │    (Google OR-Tools CP-SAT Solver)               ││
│  │    Mathematical Constraint Satisfaction           ││
│  └──────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────┤
│  Hooks & Policies                                    │
│  • Pre-tool audit logging                            │
│  • Safety-critical commit gating                     │
│  • Token usage tracking                              │
├──────────────────────────────────────────────────────┤
│  Mock Railway Infrastructure Database                │
│  (Replace with real CRIS/RailMadad API in prod)      │
└──────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Prerequisites

- Python 3.10+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/app/api-keys)

### 2. Install Dependencies

```bash
cd sih26028-railway-block-planner
pip install -r requirements.txt
```

### 3. Set API Key

**Option A — Environment variable (recommended):**
```bash
# Windows PowerShell
$env:GEMINI_API_KEY = "your-api-key-here"

# Linux / macOS
export GEMINI_API_KEY="your-api-key-here"
```

**Option B — `.env` file:**
```
GEMINI_API_KEY=your-api-key-here
```

**Option C — Inline in code:**
```python
config = LocalAgentConfig(api_key="your-api-key-here", ...)
```

### 4. Run

```bash
# Single-query demo mode
python main.py

# Interactive terminal session
python main.py --interactive
```

## Project Structure

```
sih26028-railway-block-planner/
├── main.py                  # Entry point (demo + interactive modes)
├── config.py                # Agent configuration & system prompt
├── tools/
│   ├── __init__.py
│   ├── section_status.py    # Track section status queries
│   ├── conflict_checker.py  # Train path conflict detection
│   ├── optimizer.py         # OR-Tools CP-SAT block optimizer
│   └── commit.py            # Block schedule commit tool
├── models/
│   ├── __init__.py
│   └── railway.py           # Pydantic data models
├── data/
│   ├── __init__.py
│   └── mock_db.py           # Mock railway infrastructure DB
├── hooks/
│   ├── __init__.py
│   └── audit.py             # Audit logging & safety hooks
├── requirements.txt
├── .env.example
└── README.md
```

## Priority Hierarchy

| Tier | Category                        | Max Permissible Delay |
|------|---------------------------------|-----------------------|
| 1    | Emergency Track Repairs         | Immediate preemption  |
| 2    | Premium Express (VB, Rajdhani)  | ≤ 5 minutes           |
| 3    | Express / Superfast             | ≤ 15 minutes          |
| 4    | Routine Maintenance Blocks      | Flexible              |
| 5    | Freight & Goods                 | Flexible              |

## License

Built for Smart India Hackathon 2026 — Problem Statement SIH26028.
