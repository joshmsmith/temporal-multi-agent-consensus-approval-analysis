# temporal-multi-agent-consensus-approval-analysis
Examples showing agents analyzing data and doing consensus to review and approve proposals - in this case, Cosmos Insurance proposals.
These agents are automation agents who accomplish tasks intelligently and independently. 
They are _not_ conversational. These agents are exposed as tools (via MCP) so they can be used 
by an MCP client.

We will demonstrate several kinds of agents:
- local agents that strips sensitive data?
- analysis agents that review proposals for acceptance based on insurance rules
  - these are evaluated which weighs their judgements
- consensus agent that reviews analysis and comes to a final result
- summary agent that summarizes the review and analysis

## Space Insurance Approvals


## How it works: Consensus


## Prerequisites:
- Python3+
- `uv` (curl -LsSf https://astral.sh/uv/install.sh | sh)
- Temporal [Local Setup Guide](https://learn.temporal.io/getting_started/?_gl=1*1bxho70*_gcl_au*MjE1OTM5MzU5LjE3NDUyNjc4Nzk.*_ga*MjY3ODg1NzM5LjE2ODc0NTcxOTA.*_ga_R90Q9SJD3D*czE3NDc0MDg0NTIkbzk0NyRnMCR0MTc0NzQwODQ1MiRqMCRsMCRoMA..)
- [Claude for Desktop](https://claude.ai/download), [Goose](https://github.com/block/goose), or maybe [mcp inspector](https://github.com/modelcontextprotocol/inspector)


## 1. Setup
```bash
uv venv
source .venv/bin/activate
poetry install
```

### Launch Temporal locally 
(if using local Temporal, see [.env.example](./.env.example) for other options)
```bash
temporal server start-dev
```

### Set up your .env settings
Copy `.env.example` to `.env` and set your properties, particularly:
```bash
LLM_MODEL=openai/gpt-4o
LLM_KEY=sk-proj-...
```
### Start the worker
```bash
poetry run python run_worker.py
```

## 2. Running

This agent is:
- a *tool* that takes action for an agent in MCP context
- an *agent* that makes decisions - to approve or reject the proposals
- an *orchestrator* of the consensus agents
- a Temporal Workflow - dynamically taking action to accomplish the review analysis

([related definitions](https://temporal.io/blog/building-an-agentic-system-thats-actually-production-ready#agentic-systems-definitions))

**Note:** It does create `reviews.json` and creates a `review.pdf` 

#### Terminal
An easy way to understand what it's doing is to kick it off via a terminal:
```bash
poetry run python run_consensus_agent.py 
```

Here's what the output looks like:
```none

```

You can follow along with its progress in the Temporal UI Workflow History.

#### MCP
You can also hook this up to an MCP Client using the included `mcp_server.py`. <br />
(You may want to reset the data files between runs to get the same results again.)
WSL config:
```JSON
    "analysis_agent": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "wsl.exe",
      "args": [
        "--cd",
        "/path/to/temporal-multi-agent-consensus-approval-analysis",
        "--",
        "poetry",
        "run",
        "python",
        "mcp_server.py"
      ]
    }
```

## agents and what they do

## 3. Results


### What's Cool About This:
Building agents is easy and straightforward with Temporal. Temporal features like Workflows, Activities, and Signals, plus durable state management and retries, dramatically simplify building out agentic systems. Plus, because Temporal Cloud can scale to extremely high volumes, our agent application is also scalable to high volumes easily, by scaling up our workers (and paying for LLM API Keys with high rate limits, ha).

Consensus is useful for important processes that you want to automate but not leave to only one agent.


If you already know how to build with Temporal, you have a head start on building some agentic systems. If not, play with the code, take some (free) courses, and enjoy learning.

## In Production