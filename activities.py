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

DEFAULT_MODEL: str = "openai/gpt-4o"
load_dotenv(override=True)

@activity.defn
async def analyze(input: dict) -> dict:
    """Analyze a proposal for underwriting suitability.
    Is an agentic activity that uses an LLM to analyze the proposal.
    Input should include:
    - proposalname: The name of the proposal to analyze (for demo needs to be a valid file in the proposals directory) - e.g. "bebop"
    - additional_instructions: Additional instructions for the analysis, e.g. "Assume no risk mitigations are implemented."
    - model_config: The model to use for the analysis, e.g. "primary", "secondary", "tertiary".
    """
    # Extract the proposal and prompt from the input
    proposalname = input.get("proposalname", "")
    additional_instructions = input.get("additional_instructions", "")

    proposal_contents = load_proposal_contents(proposalname)
    rate_tier_contents = load_rate_tiers()
    rating_criteria_contents = load_rating_criteria()
    activity.logger.debug(f"Proposal contents loaded: {proposal_contents[:100]}...")  # Log first 100 characters for brevity
    activity.logger.debug(f"Rate tier contents loaded: {rate_tier_contents[:100]}...")  # Log first 100 characters for brevity
    activity.logger.debug(f"Rating criteria contents loaded: {rating_criteria_contents[:100]}...")  # Log first 100 characters for brevity

    # Get the LLM model and key from environment variables
    llm_model = input.get("model_config", DEFAULT_MODEL)
    # use the model to get the appropriate LLM key
    # model will be something like "openai/gpt-4o", key environment variable will be OPENAI_LLM_KEY
    # get the model prefix before the first slash
    model_prefix = llm_model.split("/")[0]

    llm_key = os.environ.get(f"{model_prefix.upper()}_LLM_KEY", "")
    
    
    if not llm_model or not llm_key:
        # Default to openai model if not specified 
        activity.logger.warning(f"Using default primary LLM model and key for analysis.")
        llm_model = os.environ.get("LLM_MODEL")
        llm_key = os.environ.get("LLM_KEY")

    if not llm_model or not llm_key:
        exception_message = f"LLM model or key not found in environment variables for model: {llm_model}."
        activity.logger.error(exception_message)
        raise ApplicationError(exception_message)

    
    # This is a context instruction for the LLM to understand its task
    context_instructions = "You are a helpful agent that analyses proposals for underwriting suitability. " \
    "You will receive a proposal, rating tier determination data, and rating criteria, all in markdown format." \
    "Ensure your response is valid JSON and does not contain any markdown formatting. " \
    "The response should be a JSON object with a proposal_approved boolean, " \
    "the rating_tier as a string, the rating_tier_score as an integer, calculated from the rating criteria applied to the proposal, " \
    "and confidence_score of how confident you are in your rating as a float." \
    "Feel free to include additional notes in 'additional_notes' if necessary. " \
    "Proposal Contents: " \
    + proposal_contents + \
    "\n\nRate Tier Determination: " \
    + rate_tier_contents + \
    "\n\nRating Criteria: " \
    + rating_criteria_contents + \
    "\n\nAnalyze the proposal for underwriting suitability. " + \
    additional_instructions

    activity.logger.debug(f"Context instructions for LLM: {context_instructions}")

    messages = [
        {
            "role": "system",
            "content": context_instructions,
        },
        # {
        #     "role": "user",
        #     "content": input.prompt,
        # },
    ]

    try:
        completion_kwargs = {
            "model": llm_model,
            "messages": messages,
            "api_key": llm_key,
        }

        response = completion(**completion_kwargs)

        response_content = response.choices[0].message.content
        activity.logger.debug(f"Raw LLM response: {repr(response_content)}")
        activity.logger.debug(f"LLM response content: {response_content}")
        activity.logger.debug(f"LLM response type: {type(response_content)}")
        
        # Sanitize the response to ensure it is valid JSON
        response_content = sanitize_json_response(response_content)
        activity.logger.debug(f"Sanitized response: {repr(response_content)}")
        underwriting_json_response: dict = parse_json_response(response_content)

        activity.logger.debug(f"Validating Detection Result: {underwriting_json_response}")

        # Validate the JSON response
        # check for required keys in the response, 
        #  - proposal_approved (boolean)
        #  - rating_tier (string)
        #  - rating_tier_score (int)
        #  - confidence_score (float)
        #  - additional_notes (string, optional)
        if "confidence_score" not in underwriting_json_response or not isinstance(underwriting_json_response["confidence_score"], (float)) or \
           "rating_tier" not in underwriting_json_response or not isinstance(underwriting_json_response["rating_tier"], str) or \
           "rating_tier_score" not in underwriting_json_response or not isinstance(underwriting_json_response["rating_tier_score"], int) or \
           "proposal_approved" not in underwriting_json_response or not isinstance(underwriting_json_response["proposal_approved"], bool):
            
            exception_message = f"Underwriting analysis response does not contain required elements: {underwriting_json_response}."
            activity.logger.error(exception_message)
            raise ApplicationError(exception_message)
        
        activity.logger.debug(f"Underwriting analysis response validated: {underwriting_json_response}")
        return underwriting_json_response
    
    except Exception as e:
        activity.logger.error(f"Error in LLM completion: {str(e)}")
        raise
    
    

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
        raise ApplicationError(exception_message, non_retryable=True)

    # Read the proposal file
    with open(proposal_file_path, "r") as proposal_file:
        proposal_contents = proposal_file.read()
        
        return proposal_contents
    
def load_rate_tiers() -> dict:
    """
    Loads the rate tiers data from a markdown file.
    Raises an ApplicationError if the rate tiers data file is not found.
    """
    rate_tiers_file_path = Path(__file__).resolve().parent / "rules" / "rate_tier_determination.md"
    if not rate_tiers_file_path.exists():
        exception_message = f"Rate tiers file not found at {rate_tiers_file_path}"
        activity.logger.error(exception_message)
        raise ApplicationError(exception_message)

    with open(rate_tiers_file_path, "r") as rate_tiers_file:
        return rate_tiers_file.read()
    
def load_rating_criteria() -> dict:
    """
    Loads the rating criteria data from a markdown file.
    Raises an ApplicationError if the rating criteria data file is not found.
    """
    rating_criteria_file_path = Path(__file__).resolve().parent / "rules" / "rating_criteria.md"
    if not rating_criteria_file_path.exists():
        exception_message = f"Rating criteria file not found at {rating_criteria_file_path}"
        activity.logger.error(exception_message)
        raise ApplicationError(exception_message)

    with open(rating_criteria_file_path, "r") as rating_criteria_file:
        return rating_criteria_file.read()