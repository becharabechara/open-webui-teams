"""
title: Lagoon API Pipeline
author: becharabechara
author_url: https://github.com/bbechara-tikehaucapital
version: 0.3.7
license: MIT
description: A pipeline for communicating with Lagoon API Exposed via Archipel
features:
v0.1.0 - bechara:
  - Communicating with Lagoon API
  - Customizable API endpoint,key, and certificate verification
  - Error handling and logging
  - Citation support
v0.2.0 - Moez:
  - Async API calls
  - Enhanced status management
  - Streaming support
  - Prompt on uploaded files
v0.3.1 - bechara:
  - All calls are send to Lagoon API
  - Env Variables aren't set by default
  - Detection of Web Search Tool And Boolean added to Payload
v0.3.2 - Moez:
  - Add API Citations
  - Add API Status
v0.3.3 - Moez:
  - Document Full Content if (One document)
  - Status Document Mode.
v0.3.4 - Moez:
  - Change from 150000 Character to 150000 Token
v0.3.5 - Bechara:
  - Changed the tiktoken encoding formatter
v0.3.6 - Bechara:
  - Added escaping path and message content from within the content to conflicts
v0.3.7 - Bechara:
  - Always include full file content with metadata in document mode
  - Removed token limit conditions for file processing
"""

from typing import Union, AsyncGenerator, Dict, Any, Optional, List
import asyncio
import traceback
import httpx
import json
import os
from pydantic import BaseModel, Field
import logging
import urllib3
from fastapi import Request
import re
import tiktoken

# Set up logging (minimal, errors only)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserValves(BaseModel):
    lagoon_api_taskendpoint: str = Field(
        default=os.getenv(
            "LAGOON_API_TASKENDPOINT",
            "https://api-dev.tikehaucapital.com/lagoon/api/chatv2/taskopenwebui",
        ),
        description="Lagoon API endpoint",
    )
    lagoon_api_endpoint: str = Field(
        default=os.getenv(
            "LAGOON_API_ENDPOINT",
            "https://api-dev.tikehaucapital.com/lagoon/api/chatv2/chatopenwebuistreaming",
        ),
        description="Lagoon API endpoint",
    )
    lagoon_api_key: str = Field(
        default=os.getenv("LAGOON_API_KEY", "default-lagoon-key"),
        description="Lagoon API key",
    )
    lagoon_needs_api_key: bool = Field(
        default=os.getenv("LAGOON_NEEDS_API_KEY", "false").lower() == "true",
        description="Whether the Lagoon API requires an API key",
    )
    lagoon_server_certificate: bool = Field(
        default=os.getenv("LAGOON_SERVER_CERTIFICATE", "false").lower() == "true",
        description="Whether to verify the Lagoon API server certificate",
    )


class Pipe:
    def __init__(self):
        self.type = "pipe"
        self.valves = UserValves()
        self.citation = True  # Enable citations for references
        if not self.valves.lagoon_server_certificate:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def __call__(
        self,
        body: Dict[str, Any],
        __user__: Dict[str, Any] = None,
        __request__: Request = None,
        __event_emitter__=None,
        __task__=None,
        __metadata__=None,
    ):
        """Make the pipe callable for Open WebUI."""
        return self.pipe(
            body, __user__, __request__, __event_emitter__, __task__, __metadata__
        )

    async def pipe(
        self,
        body: Dict[str, Any],
        __user__: Dict[str, Any] = None,
        __request__: Request = None,
        __event_emitter__=None,
        __task__=None,
        __metadata__: Dict[str, Any] = None,
        __files__=None,
    ) -> Union[str, AsyncGenerator[str, None], Dict[str, Any]]:
        """Custom pipe that processes user messages and communicates with the Lagoon API."""
        try:
            # Validate input data
            messages = self._validate_messages(body, __event_emitter__)
            if not isinstance(messages, list):
                yield messages
                return

            user_email = self._validate_user(__user__, __event_emitter__)
            if not user_email:
                yield {
                    "content": "Could not detect user email from metadata.",
                    "citations": [],
                }
                return

            # Extract WebSearchActivated from __metadata__['features']['web_search']
            web_search_activated = False
            if __metadata__ and "features" in __metadata__:
                web_search_activated = __metadata__["features"].get("web_search", False)

            # Prepare message history
            history = self._prepare_history(messages, __files__)

            # Handle task if present
            if __task__:
                result = await self._process_task(
                    user_email,
                    history,
                    web_search_activated,
                    __event_emitter__,
                    __task__,
                )
                if not result:
                    logger.warning(
                        f"Empty response from Lagoon API for task {__task__}"
                    )
                    yield {
                        "content": f"No response received from Lagoon API for task {__task__}.",
                        "citations": [],
                    }
                    return
                yield result
                return

            # Begin regular processing
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Processing...", "done": False},
                    }
                )

            # Make API call and stream response
            async for chunk in self._stream_api_response(
                user_email, history, web_search_activated, __event_emitter__
            ):
                yield chunk

        except (httpx.RequestError, json.JSONDecodeError) as e:
            yield await self._handle_error(e, "API error", __event_emitter__)
        except Exception as e:
            yield await self._handle_error(e, "Unexpected error", __event_emitter__)
        finally:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Done", "done": True, "hidden": True},
                    }
                )

    def _validate_messages(self, body, __event_emitter__):
        """Validate messages from the request body."""
        messages = body.get("messages", [])
        if not messages:
            error_msg = "No messages provided."
            logger.error(error_msg)
            if __event_emitter__:
                asyncio.create_task(
                    __event_emitter__(
                        {"type": "message", "data": {"content": error_msg}}
                    )
                )
            return {"content": error_msg, "citations": []}
        return messages

    def _validate_user(self, __user__, __event_emitter__):
        """Validate user information."""
        if not __user__:
            error_msg = "No user metadata provided."
            logger.error(error_msg)
            if __event_emitter__:
                asyncio.create_task(
                    __event_emitter__(
                        {"type": "message", "data": {"content": error_msg}}
                    )
                )
            return None

        user_email = __user__.get("email", "unknown_user")
        if user_email == "unknown_user":
            error_msg = "Could not detect user email from metadata."
            logger.error(error_msg)
            if __event_emitter__:
                asyncio.create_task(
                    __event_emitter__(
                        {"type": "message", "data": {"content": error_msg}}
                    )
                )
            return None

        return user_email

    def _prepare_history(self, messages, files):
        """Extract and format message history with full file content and metadata."""
        # Process files if present - always include full content with metadata
        if files:
            self._inject_file_content_into_context(messages, files)

        return [
            {
                "content": msg.get("content", ""),
                "role": msg.get("role", msg.get("type", "unknown")),
            }
            for msg in messages
        ]

    def _inject_file_content_into_context(self, messages, files):
        """Inject file content with metadata into system message context."""
        try:
            # Build comprehensive file content with metadata
            file_contexts = []

            for file_info in files:
                # Extract file information from OpenWebUI structure
                file_obj = file_info.get("file", {})
                file_data = file_obj.get("data", {})
                file_meta = file_obj.get("meta", {})
                
                # Get content from data section
                content = file_data.get("content", "")
                
                # Get metadata from multiple possible locations
                filename = (
                    file_obj.get("filename") or 
                    file_meta.get("name") or 
                    file_info.get("name") or 
                    "Unknown File"
                )
                
                file_type = (
                    file_meta.get("content_type") or 
                    file_obj.get("content_type") or 
                    "Unknown Type"
                )
                
                file_size = (
                    file_meta.get("size") or 
                    file_obj.get("size") or 
                    file_info.get("size") or 
                    "Unknown Size"
                )

                # Create structured file context with metadata
                file_context = self._format_file_context(
                    filename, file_type, file_size, content
                )
                file_contexts.append(file_context)

            # Combine all file contexts
            combined_context = "\n\n".join(file_contexts)

            # Find and update system message
            for message in messages:
                if message.get("role") == "system":
                    system_message = message.get("content", "")

                    # Escape content to prevent regex issues
                    escaped_content = self._escape_content(combined_context)

                    # Replace or add context
                    updated_message = self._update_system_message_context(
                        system_message, escaped_content
                    )
                    message["content"] = updated_message
                    break

        except Exception as e:
            logger.error(f"Error injecting file content: {str(e)}")
            raise

    def _format_file_context(self, filename, file_type, file_size, content):
        """Format individual file content with metadata."""
        return f"""--- FILE: {filename} ---
Type: {file_type}
Size: {file_size}
Content:
{content}
--- END FILE: {filename} ---"""

    def _escape_content(self, content):
        """Escape content to prevent regex conflicts."""
        return content.replace("\\", "\\\\").replace("$", "\\$")

    def _update_system_message_context(self, system_message, escaped_content):
        """Update system message with new context content."""
        # Check if context tags exist
        if "<context>" in system_message and "</context>" in system_message:
            # Replace existing context
            return re.sub(
                r"<context>(.*?)</context>",
                f"<context>\n{escaped_content}\n</context>",
                system_message,
                flags=re.DOTALL,
            )
        else:
            # Add context at the end of system message
            return f"{system_message}\n\n<context>\n{escaped_content}\n</context>"

    async def _process_task(
        self, user_email, history, web_search_activated, event_emitter, task
    ):
        """Process internal tasks (title/tags generation)."""
        if task == "query_generation":
            if event_emitter:
                await event_emitter(
                    {
                        "type": "message",
                        "data": {
                            "content": f"📚 **Document Mode**\n\n",
                            "citations": [],
                        },
                    }
                )

        try:
            # Prepare payload with user email, message history, and web search status
            payload = {
                "User": user_email,
                "Messages": history,
                "WebSearchActivated": web_search_activated,
            }
            headers = {"Content-Type": "application/json"}
            api_taskendpoint = self.valves.lagoon_api_taskendpoint

            async with httpx.AsyncClient(
                verify=self.valves.lagoon_server_certificate, timeout=30
            ) as client:
                response = await client.post(
                    api_taskendpoint, json=payload, headers=headers
                )

            response.raise_for_status()
            response_text = response.text
            if not response_text:
                logger.warning(f"Empty response from Lagoon API for task {task}")
                return ""
            return response_text
        except Exception as e:
            logger.error(f"Error in process_task: {str(e)}")
            return ""

    async def _stream_api_response(
        self, user_email, history, web_search_activated, __event_emitter__
    ):
        """Stream the API response to the client."""
        payload = {
            "User": user_email,
            "Messages": history,
            "WebSearchActivated": web_search_activated,
        }
        headers = {
            "Accept": "text/plain",
            "Content-Type": "application/json; charset=utf-8",
        }

        if self.valves.lagoon_needs_api_key:
            api_key = self.valves.lagoon_api_key
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(
            verify=self.valves.lagoon_server_certificate, timeout=120
        ) as client:
            async with client.stream(
                "POST",
                self.valves.lagoon_api_endpoint,
                json=payload,
                headers=headers,
            ) as response:
                response.raise_for_status()

                first_chunk_received = False
                response_text = ""
                async for chunk in response.aiter_text():
                    if chunk:
                        response_text += chunk
                        jsonblock = chunk.strip()
                        if jsonblock.startswith("{") and jsonblock.endswith("}"):
                            try:
                                obj = json.loads(jsonblock)
                                obj_type = obj.get("type")
                                if obj_type in {"citation", "status"}:
                                    await __event_emitter__(obj)
                                    continue
                            except json.JSONDecodeError:
                                pass

                        if not first_chunk_received:
                            first_chunk_received = True
                            await __event_emitter__(
                                {
                                    "type": "status",
                                    "data": {
                                        "description": "Answering",
                                        "hidden": True,
                                    },
                                }
                            )

                        yield chunk

                if not response_text:
                    logger.warning(
                        "Empty response from Lagoon API in stream_api_response"
                    )
                    yield {
                        "content": "No response received from Lagoon API.",
                        "citations": [],
                    }

    async def _handle_error(self, exception, error_type, __event_emitter__):
        """Handle and format errors."""
        tb = traceback.extract_tb(exception.__traceback__)
        error_msg = f"{error_type}: {str(exception)}\n{''.join(traceback.format_tb(exception.__traceback__))}"
        logger.error(error_msg)
        error_msg = f"{error_type}: {str(exception)}"
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "message",
                    "data": {
                        "content": f"#### ❌ Error\n{error_msg}.",
                        "citations": [],
                    },
                }
            )
        return {"content": error_msg, "citations": []}