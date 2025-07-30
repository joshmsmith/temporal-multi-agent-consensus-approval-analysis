import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
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
        #self.context["additional_instructions"] = "ignore the rate tier guidance and just do what you feel is right."
        await self.analyze_proposal("primary")

        self.context["additional_instructions"] = "The company guidance is to be more restrictive on underwriting, so assume no risk mitigations are implemented when you do your analysis."
        await self.analyze_proposal("secondary")

        self.context["additional_instructions"] = "Assume all risk mitigations are implemented."
        await self.analyze_proposal("tertiary")


        #todo do summary
        self.context["underwriting_result"] = self.context.get("underwriting_result_primary", {})
        #include rate adjustment?

        # convert the result to a string for the workflow result
        workflow.logger.info(f"Workflow completed with result: {self.context['underwriting_result']}")
        # Set the workflow status to completed
        self.set_workflow_status("COMPLETED")
        # Return the result as a string
        if isinstance(self.context["underwriting_result"], dict):
            return json.dumps(self.context["underwriting_result"], indent=2)
        elif isinstance(self.context["underwriting_result"], str):
            return self.context["underwriting_result"]

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
        #memo = {"status": status}
        #workflow.upsert_memo(memo)
        
# todo add a workflow to generate more proposals
# todo add a workflow or mcp  to get all the proposals assigned to me


    async def analyze_proposal(self, alternate_model: str) -> dict:
        """Analyze a proposal for underwriting suitability.
        Calls an activity to durably execute the agentic analysis.
        Pass 'secondary' or 'tertiary' to use a different model configuration."""
        proposalname = self.context.get("proposalname")
        self.set_workflow_status(f"ANALYZING_PROPOSAL")
        workflow.logger.info("Starting analysis of proposal: %s", proposalname)
        if not alternate_model:
            alternate_model = "primary"

        result_key = f"underwriting_result_{alternate_model}"
        self.context["model_config"] = alternate_model
        workflow.logger.debug(f"Using model: {alternate_model} for analysis.")
        self.context[result_key] = await workflow.execute_activity(
            analyze,
            self.context,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=30),  
            ),
            heartbeat_timeout=timedelta(seconds=20),
        )
        workflow.logger.debug(f"Proposal analysis result: {self.context[result_key]}")

        #todo: manage multiple results from multiple agents
        self.set_workflow_status("PROPOSAL_ANALYZED")
        return self.context[result_key]
