import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from activities import analyze

'''Workflow for multi-agent consensus/approval/analysis.
This workflow coordinates multiple agents to analyze and discern about underwriting proposals.'''
@workflow.defn
class ConsensusUnderwritingAnalysisWorkflow:
    def __init__(self) -> None:
        self.approved: bool = False
        self.rejected: bool = False
        self.status: str = "INITIALIZING"
        self.context: dict = {}

    @workflow.run
    async def run(self, inputs: dict) -> str:
        
        self.context["prompt"] = inputs.get("prompt", {})
        self.context["metadata"] = inputs.get("metadata", {})
        self.context["proposalname"] = inputs.get("proposalname", "")
        workflow.logger.debug(f"Starting repair workflow with inputs: {inputs}")

        #todo trigger three analyses
        #step 1: activity that does analysis, inputs: prompt, LLM model (Or model #, do in a loop?), outputs: rate tier and confidence score
        await self.analyze_proposal()


        #todo do summary
        #include rate adjustment?

        return "ANALYZED!"

    # workflow helper functions
    def set_workflow_status(self, status: str) -> None: 
        """Set the current status of the workflow."""
        self.status = status
        # set workflow current details in Markdown format. Include status, iteration count, and timestamp.
        details: str = f"## Workflow Status \n\n" \
                    f"- **Phase:** {status}\n" 
        details += f"- **Last Status Set:** {workflow.now().isoformat()}\n"
        workflow.set_current_details(details)
        workflow.logger.debug(f"Workflow status set to: {status}")

        
# todo add a workflow to generate more proposals
# todo add a workflow or mcp  to get all the proposals assigned to me


    async def analyze_proposal(self) -> dict:
        """Analyze a proposal for underwriting suitability.
        Calls an activity to durably execute the agentic analysis."""
        proposalname = self.context.get("proposalname")
        self.set_workflow_status(f"ANALYZING_PROPOSAL: {proposalname}")
        workflow.logger.info("Starting analysis of proposal: %s", proposalname)
        self.context["underwriting_result"] = await workflow.execute_activity(
            analyze,
            self.context,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=30),  
            ),
            heartbeat_timeout=timedelta(seconds=20),
        )
        workflow.logger.debug(f"Proposal analysis result: {self.context["underwriting_result"]}")

        return self.context["underwriting_result"]
