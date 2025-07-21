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
