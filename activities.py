from asyncio import sleep
from datetime import datetime
import os
import json
from pathlib import Path
from typing import Callable
from temporalio import activity
from dotenv import load_dotenv

from litellm import completion
from temporalio.exceptions import ApplicationError
from shared.config import TEMPORAL_TASK_QUEUE, get_temporal_client
from markdown_pdf import MarkdownPdf, Section


load_dotenv(override=True)

@activity.defn
async def analyze(input: dict) -> dict:
    """Analyze a proposal for underwriting suitability.
    Is an agentic activity that uses an LLM to analyze the proposal."""
    # Extract the proposal and prompt from the input
    proposalname = input.get("proposalname", "")

    proposalcontents = load_proposal_contents(proposalname)
    activity.logger.warning(f"Proposal contents loaded: {proposalcontents[:100]}...")  # Log first 100 characters for brevity

    output = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "analysis": {
            "summary": "This is a summary of the analysis.", 
        }
    }
    return output

def sanitize_json_response(response_content: str) -> str:
        """
        Sanitizes the response content to ensure it's valid JSON.
        """
        # Remove any markdown code block markers
        response_content = response_content.replace("```json", "").replace("```", "")

        # Remove any leading/trailing whitespace
        response_content = response_content.strip()

        return response_content

def parse_json_response(response_content: str) -> dict:
        """
        Parses the JSON response content and returns it as a dictionary.
        """
        try:
            data = json.loads(response_content)
            return data
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
            raise

def load_proposal_contents(proposalname: str) -> dict:
    """
    Loads the orders data from a JSON file.
    If `orders_of_interest` is provided, it filters the orders based on the given order IDs.
    If no `orders_of_interest` is provided, it returns all orders.
    Raises an ApplicationError if the orders data file is not found.
    """
    proposal_file_name = f"{proposalname}.md"
    proposal_file_path = (
        Path(__file__).resolve().parent / "proposals" / proposal_file_name
    )
    # Check if the proposal file exists
    if not proposal_file_path.exists():
        exception_message = f"Proposal file not found at {proposal_file_path}"
        activity.logger.error(exception_message)
        raise ApplicationError(exception_message)

    # Read the proposal file
    with open(proposal_file_path, "r") as proposal_file:
        proposal_contents = proposal_file.read()
        
        return proposal_contents