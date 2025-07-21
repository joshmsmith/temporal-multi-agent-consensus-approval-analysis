import json
import os
from pathlib import Path
import uuid
from typing import Dict

from mcp.server.fastmcp import FastMCP, Context
import asyncio
import uuid
import os

from shared.config import TEMPORAL_TASK_QUEUE, get_temporal_client
from workflows import ConsensusUnderwritingAnalysisWorkflow
from dotenv import load_dotenv


mcp = FastMCP(name="Cosmos Insurance Underwriting Assistance Agent",
              description="An assistant agent for underwriters to assist in the underwriting process.",
              version="0.1.0",
              author="Josh Smith",
              instructions="""
This agent assists underwriters in the underwriting process by analyzing and repairing order problems. 
It can review proposals and recommend rejection or acceptance based on the analysis.
It can also recommend rating tiers based on the analysis of the proposals."""
                )

@mcp.tool(description="Trigger a repair workflow to start that will detect order problems and propose repairs. " \
          "Upon Approval, the workflow will continue with the repairs and eventually report its results.",
          #tags={"underwriting", "consensus", "workflow", "start workflow"},
          )
async def Underwrite(inputs: Dict[str, str]) -> Dict[str, str]:
    """Start the underwriting agent to analyze a proposal."""
    
    load_dotenv(override=True)
    user = os.environ.get("USER_NAME", "Agent.Smith") 
    client = await get_temporal_client()

    start_msg = {
        "prompt": "Analyze and underwite the proposals.",
        "metadata": {
            "user": user,  
            "system": "temporal-consensus-underwriting-agent",
        },
    }
    
    handle = await client.start_workflow(
        ConsensusUnderwritingAnalysisWorkflow.run,
        start_msg,
        id=f"repair-{user}-{uuid.uuid4()}",
        task_queue=TEMPORAL_TASK_QUEUE,
    )
    
    desc : str= await handle.describe()
    status : str = await handle.query("GetRepairStatus")    
    
    return {"workflow_id": handle.id, "run_id": handle.result_run_id, "status": status, "description": desc.status.name}

@mcp.tool(description="Get the current status of the repair workflow.",
          #tags={"underwriting", "workflow", "status"},
          )
async def status(workflow_id: str, run_id: str) -> Dict[str, str]:
    """Return current status of the workflow."""
    load_dotenv(override=True)
    user = os.environ.get("USER_NAME", "Harry.Potter") 
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id=workflow_id, run_id=run_id)
    desc = await handle.describe()
    status = await handle.query("GetRepairStatus")
    return {
        "status": status,
        "description": desc.status.name
    }


#todo maybe we want approval/rejection tools here?

if __name__ == "__main__":
    mcp.run(transport="stdio")
