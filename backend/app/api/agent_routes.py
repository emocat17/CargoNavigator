"""
Agent chat routes with SSE (Server-Sent Events) streaming.
"""
import json
import logging
import re
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.agent_service import agent_service
from app.services.chat_history import (
    create_session,
    save_message,
    get_session,
    list_sessions,
    delete_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent Chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息", min_length=1, max_length=20000)
    session_id: Optional[str] = Field(None, description="会话ID，不传则创建新会话")


@router.post("/chat")
async def agent_chat(request: ChatRequest):
    """
    Agent chat endpoint with SSE streaming.

    Events:
      - session_id: {"id": "会话ID"}
      - status:     {"message": "正在查询..."}
      - token:      {"content": "文本片段"}
      - route:      {"content": "路线规划结果"}
      - done:       {}
    """
    # ── Input sanitization ──
    raw_msg = request.message
    # Strip excessive whitespace (collapse multiple spaces/newlines)
    sanitized_msg = re.sub(r'[\s　]+', ' ', raw_msg).strip()

    # Reject empty messages after stripping
    if not sanitized_msg:
        raise HTTPException(status_code=400, detail="消息不能为空")

    # Manual size check (belt-and-suspenders with Pydantic max_length)
    if len(sanitized_msg) > 20000:
        raise HTTPException(status_code=400, detail="消息长度超过限制 (20000字符)")

    # Log the request (anonymized: only first 50 chars)
    preview = sanitized_msg[:50] + ("..." if len(sanitized_msg) > 50 else "")
    logger.info(f"Agent chat request: [{preview}]")

    # Resolve or create session
    sid = request.session_id or create_session()

    # Save user message before streaming
    save_message(sid, "user", sanitized_msg)

    # Accumulate full assistant response for saving
    full_response_parts: list[str] = []
    route_context_data: Optional[str] = None

    def _sse_error(msg: str) -> str:
        """Build a proper error SSE event."""
        return f"event: error\ndata: {json.dumps({'message': msg}, ensure_ascii=False)}\n\n"

    async def event_stream():
        nonlocal full_response_parts, route_context_data
        try:
            # Yield session_id first so client knows which session this belongs to
            yield f"event: session_id\ndata: {json.dumps({'id': sid})}\n\n"

            async for sse_chunk in agent_service.chat_stream(sanitized_msg):
                # Parse SSE chunk to accumulate token text
                lines = sse_chunk.strip().split("\n")
                event_type = None
                data_str = None
                for line in lines:
                    if line.startswith("event: "):
                        event_type = line[7:]
                    elif line.startswith("data: "):
                        data_str = line[6:]

                if event_type == "token" and data_str:
                    try:
                        token = json.loads(data_str)
                        full_response_parts.append(token)
                    except (json.JSONDecodeError, TypeError):
                        pass
                elif event_type == "route" and data_str:
                    try:
                        route_context_data = json.loads(data_str)
                    except (json.JSONDecodeError, TypeError):
                        pass

                yield sse_chunk

            # Save assistant message after streaming completes
            full_text = "".join(full_response_parts)
            if full_text:
                save_message(
                    sid,
                    "assistant",
                    full_text,
                    route_context=route_context_data,
                )
        except Exception as e:
            logger.error(f"Agent chat stream error: {e}", exc_info=True)
            yield _sse_error(f"服务内部错误: {e}")
            yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/sessions")
async def list_chat_sessions():
    """List all chat sessions."""
    return list_sessions()


@router.get("/chat/sessions/{session_id}")
async def get_chat_session(session_id: str):
    """Get a specific chat session with messages."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session."""
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}


@router.get("/health")
async def agent_health():
    """Check agent service health."""
    try:
        llm_configured = bool(agent_service.llm_key)
    except Exception as e:
        logger.warning(f"Failed to check LLM configuration: {e}")
        llm_configured = False
    return {
        "status": "ok",
        "llm_configured": llm_configured,
    }


@router.get("/debug")
async def agent_debug():
    """Return detailed service debug information."""
    import os
    from pathlib import Path

    # LLM status
    try:
        llm_configured = bool(agent_service.llm_key)
    except Exception as e:
        logger.warning(f"Failed to check LLM configuration: {e}")
        llm_configured = False

    # Bridge DB status
    bridge_db_status = "unknown"
    bridge_count = 0
    try:
        from app.bridge_db import query_one
        count_row = query_one("SELECT COUNT(*) as cnt FROM bridges")
        if count_row:
            bridge_count = count_row["cnt"]
            bridge_db_status = "ok"
    except Exception as e:
        bridge_db_status = f"error: {e}"

    # Influence line data count
    infl_count = 0
    try:
        from app.bridge_db import query_one as q1
        row = q1("SELECT COUNT(*) as cnt FROM bridge_influence_lines")
        if row:
            infl_count = row["cnt"]
    except Exception as e:
        logger.warning(f"Failed to count bridge influence lines: {e}")

    # Spider data counts
    spider_data_dir = Path(__file__).resolve().parent.parent.parent / "spider" / "data"
    spider_md_count = 0
    spider_exists = spider_data_dir.exists()
    if spider_exists:
        try:
            spider_md_count = len(list(spider_data_dir.rglob("*.md")))
        except Exception as e:
            logger.warning(f"Failed to count spider data files: {e}")

    return {
        "status": "ok",
        "llm_configured": llm_configured,
        "bridge_db": {
            "status": bridge_db_status,
            "bridge_count": bridge_count,
            "influence_line_count": infl_count,
        },
        "spider_data": {
            "exists": spider_exists,
            "markdown_file_count": spider_md_count,
        },
    }
