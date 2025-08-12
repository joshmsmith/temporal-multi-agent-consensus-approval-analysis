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
                "analysis_agent_name": "Antonio"
            },
            {
                "model": "moonshotai/kimi-k2-instruct", 
                "additional_instructions": "The company guidance is to be more restrictive on underwriting, so assume no risk mitigations are implemented when you do your analysis.",
                "analysis_agent_name": "Carlos"
            },
            {
                "model": "groq/llama-3.3-70b-versatile", 
                "additional_instructions": "Assume all risk mitigations are implemented.",
                "analysis_agent_name": "Jobim"
            },
            # {
            #     "model": "openai/gpt-4o-mini",
            #     "additional_instructions": "Nothing good ever happened to me when I trusted others.",
            #     "analysis_agent_name": "Faye"
            # },
            # {
            #     "model": "openai/gpt-4.1-mini",
            #     "additional_instructions": "“Humans are meant to work and sweat to earn a living. Those that try to get rich quick or live at the expense of others, all get divine retributions somewhere along the line. That's the lesson.",
            #     "analysis_agent_name": "Jet"
            # },
            # {
            #     "model": "openai/gpt-4o-mini",
            #     "additional_instructions": "Whatever happens, happens.",
            #     "analysis_agent_name": "Spike"
            # },
        ],
        "consensus_model": "openai/gpt-4o-mini",  # Model to use for consensus analysis
    }
    
    handle = await client.start_workflow(
        ConsensusUnderwritingAnalysisWorkflow.run,
        start_msg,
        id=f"underwriting-analysis-{proposalname}",
        task_queue=TEMPORAL_TASK_QUEUE,
    )
    print(f"{user}'s proposal analyis started with: {handle.id}")

    # Wait for the workflow to complete
    result = await handle.result()
    print(f"Workflow completed with result: {result}")


if __name__ == "__main__":
    asyncio.run(main(args.proposalname))
