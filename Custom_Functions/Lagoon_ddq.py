"""
title: LagoonDDQ  API Pipeline
author: moez
version: 0.1.0
description: A pipeline for communicating with Lagoon DDQ API Exposed via Archipel
"""

from typing import Union, AsyncGenerator, Dict, Any, Optional, List
import asyncio
import traceback
import httpx
import json
import os
from typing import Dict, Any
from pydantic import BaseModel, Field
import logging
import urllib3
from fastapi import Request

# Set up logging (minimal, errors only)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserValves(BaseModel):
    lagoon_api_taskendpoint: str = Field(
        default="https://api-dev.tikehaucapital.com/lagoon/api/chatv2/taskopenwebui",
        description="Lagoon API endpoint",
    )
    lagoon_api_endpoint: str = Field(
        default="https://api-dev.tikehaucapital.com/lagoon/api/ddqv2/chatopenwebui",
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
    ):
        """Make the pipe callable for Open WebUI."""
        return self.pipe(
            body, __user__, __request__, __event_emitter__, __source_context__
        )

    async def pipe(
        self,
        body: Dict[str, Any],
        __user__: Dict[str, Any] = None,
        __request__: Request = None,
        __event_emitter__=None,
        __task__=None,
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

            # Extract the latest prompt and history
            history = self._prepare_history(messages)

            # Handle task if present
            if __task__:
                logger.info(f"Task: {__task__}")
                result = await self._process_task(
                    user_email, history, __event_emitter__
                )
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

            # logger.info(body.get("messages"))
            # Moez
            # history = self._prepare_history(messages)

            # Make API call and stream response
            async for chunk in self._stream_api_response(
                user_email, history, __event_emitter__
            ):
                yield chunk

        except (httpx.RequestError, json.JSONDecodeError) as e:
            yield await self._handle_error(e, "API error", __event_emitter__)
        except Exception as e:
            yield await self._handle_error(e, "Unexpected error", __event_emitter__)
        finally:
            # Always send the final "done" status, even if an error occurs
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

    def _prepare_history(self, messages):
        """Extract and format message history."""
        return [
            {
                "content": msg.get("content", ""),
                "role": msg.get("role", msg.get("type", "unknown")),
            }
            for msg in messages
        ]

    async def _process_task(self, user_email, history, __event_emitter__):
        """Process internal tasks (title/tags generation)."""
        try:
            # Prepare payload with user email and message history
            payload = {"User": user_email, "Messages": history}
            headers = {"Content-Type": "application/json"}
            api_taskendpoint = self.valves.lagoon_api_taskendpoint

            async with httpx.AsyncClient(
                verify=self.valves.lagoon_server_certificate, timeout=30
            ) as client:
                response = await client.post(
                    api_taskendpoint, json=payload, headers=headers
                )

            response.raise_for_status()
            return response.text
        except Exception:
            return ""

    async def _stream_api_response(self, user_email, history, __event_emitter__):
        """Stream the API response to the client."""
        # Prepare payload and headers
        payload = {"User": user_email, "Messages": history}

        payload_json = json.dumps(payload, ensure_ascii=False)
        # logger.info(f"-------------->payload:{payload_json}")

        headers = {
            "Accept": "text/plain",
            "Content-Type": "application/json; charset=utf-8",
        }

        # Add API key if needed
        if self.valves.lagoon_needs_api_key:
            api_key = self.valves.lagoon_api_key
            headers["Authorization"] = f"Bearer {api_key}"

        # Make API call
        async with httpx.AsyncClient(
            verify=self.valves.lagoon_server_certificate, timeout=60
        ) as client:
            async with client.stream(
                "POST",
                self.valves.lagoon_api_endpoint,
                json=payload,
                headers=headers,
            ) as response:
                response.raise_for_status()

                # Read the full response body as a single string
                full_response = await response.aread()
                full_response_str = (
                    full_response.decode()
                    if isinstance(full_response, bytes)
                    else full_response
                )

                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "Answering",
                            "hidden": True,
                        },
                    }
                )

                # Yield the entire string at once
                yield full_response_str

                # first_chunk_received = False
                # async for chunk in response.aiter_text():
                #    if chunk:
                #        if not first_chunk_received:
                #            first_chunk_received = True
                #            await __event_emitter__(
                #                {
                #                    "type": "status",
                #                    "data": {
                #                        "description": "Answering",
                #                        "hidden": True,
                #                    },
                #                }
                #            )
                #        # Send chunk in real-time to Open Web UI
                #        yield chunk
                #        # For smooth streaming
                #        await asyncio.sleep(0.02)

    async def _handle_error(self, exception, error_type, __event_emitter__):
        """Handle and format errors."""
        tb = traceback.extract_tb(exception.__traceback__)
        error_msg = f"{error_type}: {str(exception)}"
        logger.error(error_msg)

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
