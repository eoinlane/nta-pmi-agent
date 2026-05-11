"""Thin Claude client wrapper that handles structured extraction + audit logging.

Every call records (model, system, user, structured-output, usage,
duration, error) to the AuditLog. Structured output is enforced by
forcing a single tool call whose input_schema is the Pydantic-derived
JSON schema for the expected type.
"""

from __future__ import annotations

import os
import time
from typing import Any

from anthropic import Anthropic

from pmi_agent.audit import AuditLog


class LLMClient:
    def __init__(self, model: str | None = None) -> None:
        self.client = Anthropic()
        self.model = model or os.getenv("PMI_AGENT_MODEL", "claude-opus-4-7")

    def extract_structured(
        self,
        *,
        agent: str,
        tender_id: str,
        system_prompt: str,
        user_prompt: str,
        tool_name: str,
        tool_description: str,
        input_schema: dict[str, Any],
        audit: AuditLog,
        max_tokens: int = 16_000,
    ) -> tuple[dict[str, Any], str]:
        """Call Claude once with a forced tool call.

        Returns ``(tool_input, audit_record_id)`` so the caller can link the
        produced object back to the audit row.
        """
        started = time.perf_counter()
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                tools=[
                    {
                        "name": tool_name,
                        "description": tool_description,
                        "input_schema": input_schema,
                    }
                ],
                tool_choice={"type": "tool", "name": tool_name},
            )
            duration_ms = int((time.perf_counter() - started) * 1000)

            tool_use = next(
                (b for b in response.content if getattr(b, "type", None) == "tool_use"),
                None,
            )
            if tool_use is None:
                raise RuntimeError(
                    f"Model did not return a tool_use block "
                    f"(stop_reason={response.stop_reason})"
                )

            tool_input = dict(tool_use.input)  # type: ignore[arg-type]

            audit_id = audit.record(
                tender_id=tender_id,
                agent=agent,
                model=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tool_input=tool_input,
                response_meta={
                    "stop_reason": response.stop_reason,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                },
                duration_ms=duration_ms,
            )
            return tool_input, audit_id

        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            audit.record(
                tender_id=tender_id,
                agent=agent,
                model=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tool_input=None,
                response_meta=None,
                duration_ms=duration_ms,
                error=repr(exc),
            )
            raise
