"""
title: Lagoon API Pipeline
author: becharabechara
author_url: https://github.com/bbechara-tikehaucapital
version: 0.3.0
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
v0.3.0 - bechara:
  - All calls are send to Lagoon API
  - Additional Filtering on the requests
"""

from typing import Union, AsyncGenerator, Dict, Any, List, Optional, Callable
import asyncio
import httpx
import os
import urllib3
from pydantic import BaseModel, Field
from fastapi import Request


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
    language: str = Field(
        default="en",
        description="Preferred language for responses (e.g., 'en' for English, 'fr' for French)",
    )


class Pipe:
    def __init__(self):
        self._verify_env()
        self.type = "pipe"
        self.valves = UserValves()
        self.citation = True
        if not self.valves.lagoon_server_certificate:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _verify_env(self):
        required_vars = [
            "LAGOON_API_ENDPOINT",
            "LAGOON_API_TASKENDPOINT",
            "LAGOON_API_KEY",
            "LAGOON_NEEDS_API_KEY",
            "LAGOON_SERVER_CERTIFICATE",
        ]
        missing_vars = [var for var in required_vars if os.getenv(var) is None]
        if missing_vars:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                "Please ensure all are defined in your environment or .env file."
            )

    def pipes(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "lagoon_api_pipeline",
                "name": "Lagoon",
                "tools": ["web_search"],
            }
        ]

    async def pipe(
        self,
        body: Dict[str, Any],
        __user__: Dict[str, Any] = None,
        __request__: Request = None,
        __event_emitter__: Optional[Callable] = None,
        __task__: Optional[str] = None,
        __source_context__: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[str, AsyncGenerator[str, None], Dict[str, Any]]:
        try:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Processing...", "done": False},
                    }
                )

            messages = self._validate_messages(body, __event_emitter__)
            if not isinstance(messages, list):
                yield messages
                return

            user_email = self._validate_user(__user__, __event_emitter__)
            if not user_email:
                yield {"content": "Could not detect user email.", "citations": []}
                return

            if not messages:
                yield {"content": "No messages found.", "citations": []}
                return

            latest_user_query = messages[-1]["content"]
            current_file_content, historical_file_content = self._extract_file_content(
                __source_context__
            )
            full_history = await self._prepare_full_history(
                messages, historical_file_content, current_file_content, body
            )
            print(f"full_history: {full_history}")
            lagoon_payload = {
                "User": user_email,
                "Messages": [
                    {"Role": msg["role"], "Content": msg["content"]}
                    for msg in full_history
                ],
            }
            print(f"lagoon_payload: {lagoon_payload}")
            if __task__:
                result = await self._process_task(lagoon_payload, __event_emitter__)
                yield result
                return

            async for chunk in self._stream_api_response(
                lagoon_payload, __event_emitter__
            ):
                yield chunk

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

    def _validate_messages(
        self, body: Dict[str, Any], __event_emitter__: Callable
    ) -> Union[List, Dict]:
        messages = body.get("messages", [])
        if not messages:
            error_msg = (
                "No messages provided."
                if self.valves.language == "en"
                else "Aucun message fourni."
            )
            if __event_emitter__:
                asyncio.create_task(
                    __event_emitter__(
                        {"type": "message", "data": {"content": error_msg}}
                    )
                )
            return {"content": error_msg, "citations": []}
        return messages

    def _validate_user(
        self, __user__: Dict[str, Any], __event_emitter__: Callable
    ) -> Optional[str]:
        if not __user__ or "email" not in __user__:
            error_msg = (
                "No valid user metadata provided."
                if self.valves.language == "en"
                else "Aucune métadonnée d'utilisateur valide fournie."
            )
            if __event_emitter__:
                asyncio.create_task(
                    __event_emitter__(
                        {"type": "message", "data": {"content": error_msg}}
                    )
                )
            return None
        return __user__.get("email", "unknown_user")

    def _extract_file_content(
        self, source_context: Optional[List[Dict[str, Any]]]
    ) -> tuple[str, str]:
        print("_extract_file_content source_context: ", source_context)
        print("_extract_file_content self: ", self)
        if not source_context or not isinstance(source_context, list):
            return "", ""

        current_file_content = ""
        historical_file_content = ""
        latest_file_id = None

        for context in reversed(source_context):
            if "file_id" in context and "source" in context:
                latest_file_id = context["file_id"]
                break

        for context in source_context:
            if "data" in context and "document" in context["data"]:
                content = context["data"]["document"][0]
                file_id = context.get("file_id", "")
                file_source = context.get("source", "unknown")
                if file_id == latest_file_id:
                    current_file_content += f"File: {file_source}\nContent: {content}\n"
                else:
                    historical_file_content += (
                        f"File: {file_source}\nContent: {content[:100]}...\n"
                    )
        return current_file_content, historical_file_content

    async def _prepare_full_history(
        self,
        messages: List[Dict[str, str]],
        historical_file_content: str,
        current_file_content: str,
        body: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        history = messages.copy()

        if historical_file_content:
            history.insert(
                0,
                {
                    "role": "system",
                    "content": f"<context>Historical files:\n{historical_file_content}</context>",
                },
            )
        if current_file_content:
            history.insert(
                0,
                {
                    "role": "system",
                    "content": f"<context>Current file:\n{current_file_content}</context>",
                },
            )
        if "web_search_results" in body and body["web_search_results"]:
            search_content = "\n".join(body["web_search_results"])
            history.insert(
                0,
                {
                    "role": "system",
                    "content": f"<context>Web search results:\n{search_content}</context>",
                },
            )

        return history

    async def _process_task(
        self, payload: Dict[str, Any], __event_emitter__: Callable
    ) -> str:
        headers = {"Content-Type": "application/json"}
        async with httpx.AsyncClient(
            verify=self.valves.lagoon_server_certificate, timeout=30
        ) as client:
            response = await client.post(
                self.valves.lagoon_api_taskendpoint, json=payload, headers=headers
            )
            response.raise_for_status()
            return response.text

    async def _stream_api_response(
        self, payload: Dict[str, Any], __event_emitter__: Callable
    ) -> AsyncGenerator[str, None]:
        headers = {"Accept": "text/plain", "Content-Type": "application/json"}
        if self.valves.lagoon_needs_api_key:
            headers["Authorization"] = f"Bearer {self.valves.lagoon_api_key}"

        async with httpx.AsyncClient(
            verify=self.valves.lagoon_server_certificate, timeout=30
        ) as client:
            async with client.stream(
                "POST", self.valves.lagoon_api_endpoint, json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                first_chunk_received = False
                async for chunk in response.aiter_text():
                    if chunk:
                        if not first_chunk_received and __event_emitter__:
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
                        await asyncio.sleep(0.02)

    async def _handle_error(
        self, exception: Exception, error_type: str, __event_emitter__: Callable
    ) -> Dict[str, Any]:
        error_msg = f"{error_type}: {str(exception)}"
        user_msg = (
            "An error occurred. Please try again."
            if self.valves.language == "en"
            else "Une erreur s'est produite. Veuillez réessayer."
        )
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "message",
                    "data": {"content": f"#### ❌ Error\n{user_msg}", "citations": []},
                }
            )
        return {"content": error_msg, "citations": []}

    def __call__(
        self,
        body: Dict[str, Any],
        __user__: Dict[str, Any] = None,
        __request__: Request = None,
        __event_emitter__: Optional[Callable] = None,
        __source_context__: Optional[List[Dict[str, Any]]] = None,
    ):
        return self.pipe(
            body, __user__, __request__, __event_emitter__, None, __source_context__
        )
