import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from activities import analyze, detect, plan_repair, notify, execute_repairs, report, single_tool_repair, process_order

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
        workflow.logger.debug(f"Starting repair workflow with inputs: {inputs}")

        #todo trigger three analysis

        #todo do analysis

        #todo do summary

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