import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from typing import List

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from activities import analyze_proposal_agent
    from activities import create_consensus_agent
    from activities import DEFAULT_MODEL




# todo add a workflow to generate more proposals
# todo add a workflow and data sources and mcp  to get all the proposals assigned to me

'''Workflow for multi-agent consensus/approval/analysis.
This workflow coordinates multiple agents to analyze and discern about underwriting proposals.'''
@workflow.defn
class ConsensusUnderwritingAnalysisWorkflow:
    def __init__(self) -> None:
        self.approved: bool = False
        self.rejected: bool = False
        self.status: str = "INITIALIZING"
        self.context: dict = {}
        self.context["underwriting_results"] = []  # Store results from multiple analyses

    @workflow.run
    async def run(self, inputs: dict) -> str:
        """Run the multi-agent consensus workflow.
        Inputs should include:
        - proposalname: The name of the proposal to analyze (for demo needs to be a valid file in the proposals directory) - e.g. "bebop"
        - metadata: Metadata about the user and system. (optional)
        - analyses_configs: List of dicts containing the model to use (model_config) and additional_instructions for each analysis.        
        """
        
        
        if not inputs or not isinstance(inputs, dict):
            raise ApplicationError("Invalid inputs provided to the workflow. Expected a dictionary with proposalname, metadata, and analyses_configs.")

        self.context["metadata"] = inputs.get("metadata", {})
        self.context["proposalname"] = inputs.get("proposalname", "")
        self.context["analyses_configs"] = inputs.get("analyses_configs", [])
        self.context["consensus_model"] = inputs.get("consensus_model", DEFAULT_MODEL)
        if not self.context["proposalname"] or not isinstance(self.context["proposalname"], str) or not self.context["analyses_configs"]:
            raise ApplicationError("Incorrect inputs to run this Workflow.")
        self.context["pretty_proposalname"] = self.context["proposalname"].replace("_", " ").title()
        
        workflow.logger.debug(f"Starting repair workflow with inputs: {inputs}")

        #step 1: analyze the proposal with multiple agents
        await self.run_analyses()
          
        #step 2: analyze the results of the analyses to build consensus and make a decision
        await self.build_consensus()

        #step 3: summarize the results and create a report
                
        #include rate adjustment?


        self.set_workflow_status("COMPLETED")
        
        # Return the result as a string
        if isinstance(self.context["consensus_underwriting_result"], dict):
            result = json.dumps(self.context["consensus_underwriting_result"], indent=2)
        elif isinstance(self.context["consensus_underwriting_result"], str):
            result = self.context["consensus_underwriting_result"]
        
        return result

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


    async def run_analyses(self) -> None:
        """Run multiple analyses on the proposal using different LLM models.
        For each analysis configuration, run the analyze method. """
        
        self.set_workflow_status(f"ANALYZING_PROPOSAL")

        for analysis_config in self.context["analyses_configs"]:
            model_config = analysis_config.get("model", DEFAULT_MODEL)
            additional_instructions = analysis_config.get("additional_instructions", "")
            agent_name = analysis_config.get("analysis_agent_name", "DefaultAgent")
            
            # Call the analyze_proposal method with the current model configuration
            await self.analyze_proposal(proposalname=self.context["proposalname"],
                                        model=model_config,
                                        additional_instructions=additional_instructions,
                                        agent_name=agent_name)
        
        self.set_workflow_status("PROPOSAL_ANALYZED")
        
        workflow.logger.debug(f"Analysis results {self.context["underwriting_results"]}" )
        


    async def analyze_proposal(self, proposalname: str, model: str, additional_instructions: str, agent_name: str) -> None:
        """Analyze a proposal for underwriting suitability.
        Calls an activity to durably execute the agentic analysis.
        Stores the results in the context["underwriting_results"] array."""
        if not model:
            model = DEFAULT_MODEL
        
        workflow.logger.info("Starting analysis of proposal: %s with model", proposalname, model)

        #todo try/except and just store "no result found" if the activity fails

        activity_input: dict = {
            "proposalname": proposalname,
            "additional_instructions": additional_instructions,
            "model_config": model,
            "agent_name": agent_name,
        }
        analysis_results: dict = await workflow.execute_activity(
            analyze_proposal_agent,
            activity_input,
            summary=f"{model.split("/")[1]}/{agent_name}",
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=30),  
            ),
            heartbeat_timeout=timedelta(seconds=20),
        )

        # Store the results in the context
        self.context["underwriting_results"].append(analysis_results)
    
    async def build_consensus(self) -> None:
        """Build consensus from the analysis results.
        For now, just use the last analysis result as the consensus result."""
        
        self.set_workflow_status("BUILDING_CONSENSUS")
        
        if not self.context["underwriting_results"]:
            raise ApplicationError("No underwriting results found to build consensus.")
        workflow.logger.info(f"Building consensus from underwriting results: {self.context['underwriting_results']}")
        consensus_inputs = {
            "underwriting_results": self.context["underwriting_results"],
            "model_config": self.context["consensus_model"],
            "proposalname": self.context["proposalname"],
            "metadata": self.context["metadata"],
        }
        
        
        consensus_results: dict = await workflow.execute_activity(
            create_consensus_agent,
            consensus_inputs,
            summary=f"For: {self.context['pretty_proposalname']}",
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=30),  
            ),
            heartbeat_timeout=timedelta(seconds=20),
        )

        # For now, just use the last analysis result as the consensus result
        self.context["consensus_underwriting_result"] = consensus_results
        
        workflow.logger.info(f"Consensus underwriting result: {self.context['consensus_underwriting_result']}")
        
        self.set_workflow_status("CONSENSUS_BUILT")
