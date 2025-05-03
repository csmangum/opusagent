"""
Handler for conversation item events.

Conversation items represent messages, function calls, and function call outputs
in the conversation. The following events are supported:

- conversation.item.create: Create a new conversation item
- conversation.item.retrieve: Retrieve a specific conversation item
- conversation.item.truncate: Truncate an existing item's content
- conversation.item.delete: Delete a conversation item

Conversation items can be of type:
- message: Regular message in the conversation
- function_call: A function call made by the model
- function_call_output: The output of a function call

Each item has a role (system, user, assistant, or function) and content.
"""

import time
from typing import Any, Awaitable, Callable, Dict, Optional, List

from fastagent.models.openai_api import (
    ConversationItemCreateEvent,
    ConversationItemDeleteEvent,
    ConversationItemTruncateEvent,
    ConversationItemRetrieveEvent,
)


class ConversationItemHandler:
    def __init__(
        self, send_event_callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """
        Initialize the conversation item handler.

        Args:
            send_event_callback: Callback function to send events back to the server
        """
        self.send_event = send_event_callback
        self.conversation_items: Dict[str, Dict[str, Any]] = (
            {}
        )  # Store conversation items by ID
        self.conversation_order: List[str] = []  # Maintain order of conversation items

    async def handle_create(self, event: Dict[str, Any]) -> None:
        """
        Handle the conversation.item.create event.

        This creates a new conversation item.

        Args:
            event: The conversation.item.create event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "conversation.item.create"
                - item: The conversation item parameters
                - previous_item_id: Optional ID of the item after which to insert the new item
        """
        try:
            create_event = ConversationItemCreateEvent(**event)

            # Check previous_item_id first
            previous_item_id = event.get("previous_item_id")
            if previous_item_id is not None and previous_item_id != "root":
                if previous_item_id not in self.conversation_items:
                    await self._send_error_response(
                        event.get("event_id"),
                        "invalid_request_error",
                        f"Previous item {previous_item_id} not found",
                    )
                    return

            # Get item ID from the event if provided
            item_id = event["item"].get("id")
            if not item_id:
                item_id = f"item_{len(self.conversation_items) + 1}"

            # Convert content items to dictionaries
            content = []
            if create_event.item.content:
                for item in create_event.item.content:
                    content_dict = {
                        "type": item.type,
                    }
                    if item.text is not None:
                        content_dict["text"] = item.text
                    if item.audio is not None:
                        content_dict["audio"] = item.audio
                    if "audio_duration_ms" in event["item"]["content"][0]:
                        content_dict["audio_duration_ms"] = event["item"]["content"][0][
                            "audio_duration_ms"
                        ]
                    content.append(content_dict)

            # Create the conversation item
            new_item = {
                "id": item_id,
                "object": "realtime.item",
                "type": create_event.item.type,
                "status": "completed",
                "role": create_event.item.role,
                "content": content,
                "created_at": int(
                    time.time() * 1000
                ),  # Current timestamp in milliseconds
            }

            self.conversation_items[item_id] = new_item

            # Handle item positioning
            if previous_item_id == "root":
                # Insert at the beginning
                self.conversation_order.insert(0, item_id)
            elif previous_item_id is not None:
                # Insert after the specified item
                index = self.conversation_order.index(previous_item_id)
                self.conversation_order.insert(index + 1, item_id)
            else:
                # Append to the end
                self.conversation_order.append(item_id)

            await self.send_event(
                {
                    "type": "conversation.item.created",
                    "event_id": event.get("event_id"),
                    "item": new_item,
                }
            )
        except Exception as e:
            await self._send_error_response(
                event.get("event_id"),
                "invalid_request_error",
                f"Failed to create conversation item: {str(e)}",
            )

    async def handle_retrieve(self, event: Dict[str, Any]) -> None:
        """
        Handle the conversation.item.retrieve event.

        This retrieves a conversation item by ID.

        Args:
            event: The conversation.item.retrieve event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "conversation.item.retrieve"
                - item_id: The ID of the item to retrieve
        """
        try:
            retrieve_event = ConversationItemRetrieveEvent(**event)
            item_id = retrieve_event.item_id

            if item_id not in self.conversation_items:
                await self._send_error_response(
                    event.get("event_id"),
                    "invalid_request_error",
                    f"Conversation item {item_id} not found",
                )
                return

            await self.send_event(
                {
                    "type": "conversation.item.retrieved",
                    "event_id": event.get("event_id"),
                    "item": self.conversation_items[item_id],
                }
            )
        except Exception as e:
            await self._send_error_response(
                event.get("event_id"),
                "internal_error",
                f"Failed to retrieve conversation item: {str(e)}",
            )

    async def handle_truncate(self, event: Dict[str, Any]) -> None:
        """
        Handle the conversation.item.truncate event.

        This truncates a conversation item's audio content.

        Args:
            event: The conversation.item.truncate event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "conversation.item.truncate"
                - item_id: The ID of the item to truncate
                - content_index: Index of the content part to truncate
                - audio_end_ms: Inclusive duration up to which audio is truncated, in milliseconds
        """
        try:
            truncate_event = ConversationItemTruncateEvent(**event)
            item_id = truncate_event.item_id
            content_index = event.get("content_index", 0)
            audio_end_ms = event.get("audio_end_ms")

            if item_id not in self.conversation_items:
                await self._send_error_response(
                    event.get("event_id"),
                    "invalid_request_error",
                    f"Conversation item {item_id} not found",
                )
                return

            item = self.conversation_items[item_id]

            # Check if it's an assistant message (only those can be truncated according to docs)
            if item["role"] != "assistant" or item["type"] != "message":
                await self._send_error_response(
                    event.get("event_id"),
                    "invalid_request_error",
                    "Only assistant message items can be truncated",
                )
                return

            # Check if content index is valid
            if content_index >= len(item["content"]):
                await self._send_error_response(
                    event.get("event_id"),
                    "invalid_request_error",
                    f"Content index {content_index} is out of bounds",
                )
                return

            # Check if audio exists and truncate it
            content_part = item["content"][content_index]
            if "audio" in content_part:
                # If actual audio duration is less than requested truncation point
                audio_duration = content_part.get("audio_duration_ms", 0)
                if audio_end_ms and audio_end_ms > audio_duration:
                    await self._send_error_response(
                        event.get("event_id"),
                        "invalid_request_error",
                        f"audio_end_ms {audio_end_ms} exceeds audio duration {audio_duration}",
                    )
                    return

                # Truncate the audio
                if audio_end_ms is not None:
                    content_part["audio_truncated_ms"] = audio_end_ms
                    # Delete the text transcript to ensure consistency
                    if "text" in content_part:
                        del content_part["text"]

            await self.send_event(
                {
                    "type": "conversation.item.truncated",
                    "event_id": event.get("event_id"),
                    "item": item,
                }
            )
        except Exception as e:
            await self._send_error_response(
                event.get("event_id"),
                "internal_error",
                f"Failed to truncate conversation item: {str(e)}",
            )

    async def handle_delete(self, event: Dict[str, Any]) -> None:
        """
        Handle the conversation.item.delete event.

        This deletes a conversation item.

        Args:
            event: The conversation.item.delete event data containing:
                - event_id: Optional client-generated ID for the event
                - type: Must be "conversation.item.delete"
                - item_id: The ID of the item to delete
        """
        try:
            delete_event = ConversationItemDeleteEvent(**event)
            item_id = delete_event.item_id

            if item_id not in self.conversation_items:
                await self._send_error_response(
                    event.get("event_id"),
                    "invalid_request_error",
                    f"Conversation item {item_id} not found",
                )
                return

            # Delete the item
            del self.conversation_items[item_id]

            # Remove from conversation order
            if item_id in self.conversation_order:
                self.conversation_order.remove(item_id)

            await self.send_event(
                {
                    "type": "conversation.item.deleted",
                    "event_id": event.get("event_id"),
                    "item_id": item_id,
                }
            )
        except Exception as e:
            await self._send_error_response(
                event.get("event_id"),
                "internal_error",
                f"Failed to delete conversation item: {str(e)}",
            )

    async def _send_error_response(
        self, event_id: Optional[str], code: str, message: str
    ) -> None:
        """Send an error response."""
        await self.send_event(
            {"type": "error", "event_id": event_id, "code": code, "message": message}
        )
