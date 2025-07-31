import asyncio
import uuid
import os

from shared.config import TEMPORAL_TASK_QUEUE, get_temporal_client
from workflows import ConsensusUnderwritingAnalysisWorkflow
from dotenv import load_dotenv

import argparse
parser = argparse.ArgumentParser(description="Run the repair agent workflow.")
parser.add_argument(
    "proposalname",
    type=str,
    default="bebop",
    help="Proposal name to analyze.",
)
args = parser.parse_args() 

async def main(proposalname: str) -> None:
    """Run the Consensus Underwriting Analysis Workflow. """
    
    # Load environment variables
    load_dotenv(override=True)
    user = os.environ.get("USER_NAME", "Spike.Spiegel") 
    print(f"Running proposal analysis for {user} on proposal: {proposalname}")
    # Create client connected to server at the given address
    client = await get_temporal_client()

    # Start the workflow with an initial prompt
    
    #todo have the analyses be passed in as a list of dicts, each with a model_config and additional_instructions
    start_msg = {
        "prompt": "Analyze and repair the orders in the order system.",
        "metadata": {
            "user": user,  
            "system": "temporal-underwriting-consensus-agent",
        },
        "proposalname": proposalname,
        "analyses_configs": [ # Define the models and instructions for each analysis
            # Each dict here represents a different analysis configuration
            # The model_config can be used to select the appropriate LLM model
            # The additional_instructions can be used to provide specific guidance for each analysis
            # make sure you have the LLM keys configured in your .env file
            {
                "model": "openai/gpt-4o",
                "additional_instructions": "",
            },
            {
                "model": "openai/gpt-4.1-mini",
                "additional_instructions": "The company guidance is to be more restrictive on underwriting, so assume no risk mitigations are implemented when you do your analysis.",
            },
            {
                "model": "openai/gpt-4o-mini",
                "additional_instructions": "Assume all risk mitigations are implemented.",
            },
        ],
    }
    
    handle = await client.start_workflow(
        ConsensusUnderwritingAnalysisWorkflow.run,
        start_msg,
        id=f"underwriting-analysis-{proposalname}-{user}",
        task_queue=TEMPORAL_TASK_QUEUE,
    )
    print(f"{user}'s proposal analyis started with: {handle.id}")

    # Wait for the workflow to complete
    result = await handle.result()
    print(f"Workflow completed with result: {result}")


if __name__ == "__main__":
    asyncio.run(main(args.proposalname))
