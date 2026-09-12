"""
Indian Railways AI Section Controller & Block Planner
SIH26028 — Smart India Hackathon 2026

Entry point for the Antigravity-powered railway maintenance block scheduler.

Usage:
    # Demo mode (single pre-defined query)
    python main.py

    # Interactive terminal mode
    python main.py --interactive

    # With explicit API key
    python main.py --api-key YOUR_KEY

    # With explicit API key + interactive mode
    python main.py --interactive --api-key YOUR_KEY
"""

import argparse
import asyncio
import logging
import os
import sys

# Load .env file if present (for GEMINI_API_KEY)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; user can set env var directly

from google.antigravity import Agent
from google.antigravity.utils.interactive import run_interactive_loop

from config import build_agent_config


# =====================================================================
# LOGGING SETUP
# =====================================================================

def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application and the Antigravity SDK."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # Keep SDK internals at INFO unless verbose
    if not verbose:
        logging.getLogger("google.antigravity").setLevel(logging.WARNING)

    # Our audit logger always at INFO
    logging.getLogger("sih26028.audit").setLevel(logging.INFO)


# =====================================================================
# DEMO QUERY
# =====================================================================

DEMO_QUERY = (
    "We need to schedule a 120-minute track maintenance block on "
    "Kanpur-Prayagraj section (KNP-PRYJ-SEC-B). "
    "Maintenance ID: MNT-KNP-04. Work type: Rail Replacement. "
    "Earliest start time is 10:00 AM (600 mins past midnight) and "
    "latest completion is 03:00 PM (900 mins past midnight). "
    "\n\n"
    "Please:\n"
    "1. Check section status and verify clearance.\n"
    "2. Run conflict analysis against all scheduled trains.\n"
    "3. Execute the OR-Tools optimization engine to find the optimal "
    "conflict-free window considering Vande Bharat (10:30-11:00 AM), "
    "Rajdhani (12:00-12:30 PM), and Purushottam Express (01:20-02:00 PM).\n"
    "4. Present the proposed block schedule with impact assessment.\n"
)


# =====================================================================
# DEMO MODE
# =====================================================================

async def run_demo(config) -> None:
    """Runs a single pre-defined query to demonstrate the agent."""

    print("=" * 70)
    print("  [IR-SIH] Indian Railways AI Section Controller & Block Planner")
    print("           SIH26028 - Smart India Hackathon 2026")
    print("=" * 70)
    print()
    print(f"Controller Request:\n{DEMO_QUERY}")
    print("-" * 70)
    print("Agent Decision & Execution Stream:")
    print("-" * 70)
    print()

    async with Agent(config) as agent:
        response = await agent.chat(DEMO_QUERY)

        async for chunk in response:
            print(chunk, end="", flush=True)

        print()
        print()

        # Print token usage summary
        usage = agent.conversation.total_usage
        print("-" * 70)
        print("Session Token Usage:")
        print(f"  Prompt tokens:     {usage.prompt_token_count}")
        print(f"  Response tokens:   {usage.candidates_token_count}")
        print(f"  Thinking tokens:   {usage.thoughts_token_count}")
        print(f"  Total tokens:      {usage.total_token_count}")
        print("-" * 70)
        print("Schedule planning completed.")


# =====================================================================
# INTERACTIVE MODE
# =====================================================================

async def run_interactive(config) -> None:
    """Starts a full interactive terminal session with the agent."""

    print("=" * 70)
    print("  [IR-SIH] Indian Railways AI Section Controller - Interactive Mode")
    print("           SIH26028 - Smart India Hackathon 2026")
    print("=" * 70)
    print()
    print("  Available commands:")
    print("    • Ask any maintenance scheduling question in natural language.")
    print("    • Type 'exit' or 'quit' to end the session.")
    print()

    await run_interactive_loop(config)


# =====================================================================
# ARGUMENT PARSING & MAIN
# =====================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Indian Railways AI Section Controller & Block Planner (SIH26028)",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Launch interactive terminal session instead of demo mode.",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Gemini API key (overrides GEMINI_API_KEY env var).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging.",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    setup_logging(verbose=args.verbose)

    # Resolve API key: CLI flag > env var
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print(
            "ERROR: No Gemini API key found.\n"
            "\n"
            "Set it via one of:\n"
            "  1. Environment variable:  export GEMINI_API_KEY=your-key\n"
            "  2. .env file:             GEMINI_API_KEY=your-key\n"
            "  3. CLI flag:              python main.py --api-key your-key\n"
            "\n"
            "Get a free key at: https://aistudio.google.com/app/api-keys\n"
        )
        sys.exit(1)

    config = build_agent_config(api_key=api_key)

    if args.interactive:
        await run_interactive(config)
    else:
        await run_demo(config)


def main() -> None:
    """Synchronous entry point."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
