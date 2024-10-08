# -*- coding: utf-8 -*-
# Author      : ShiFan
# Created Date: 2024/4/29 上午9:14
import json
import logging
from pprint import pformat
from functools import partial, update_wrapper, wraps, lru_cache

log = logging.getLogger(__name__)
log.setLevel("INFO")


from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


try:
    from config import MaxContextLength
except ImportError:
    MaxContextLength = 4096


def content_policy(data: dict) -> dict:
    # 限制提示长度
    max_ctx = MaxContextLength
    if "num_ctx" in data:
        max_ctx = int(data["num_ctx"])
    if isinstance(messages := data.get("messages"), list):
        if len(messages) > 2:
            new_messages, content_len = [], 0
            for message in messages[::-1]:
                if (c_len := len(message.get("content", 0))) > 0:
                    # if content_len and (
                    #         content_len + c_len > max_ctx
                    # ):
                    #     break
                    # else:
                    new_messages.append(message)
                    content_len += c_len
                else:
                    new_messages.append(message)
            new_messages.reverse()
        else:
            new_messages = messages
            content_len = len(messages[0].get("content", 0))
        log.info(f"length of content: {content_len}")
        data["messages"] = new_messages
        # log.debug(f"new messages:\n{pformat(new_messages)}")
    return data


def gemini_policy(data: dict) -> dict:
    # Gemini 不支持的参数
    # if "num_ctx" in data:
    #     del data["num_ctx"]
    # if "frequency_penalty" in data:
    #     del data["frequency_penalty"]
    return data


def openai_policy(data: dict) -> dict:
    data["messages"] = data["messages"][-3:]
    # log.info(f"openai body:\n{pformat(data)}")
    return data


class PolicyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and (
                "/api/chat" in request.url.path
                or "/chat/completions" in request.url.path
        ):
            try:
                body = await request.body()
                body_str = body.decode("utf-8")
                log.info(f"url: {request.url.path}")
                data = json.loads(body_str) if body_str else {}
                data = content_policy(data)
                if data.get("model", "").startswith("gemini"):
                    data = gemini_policy(data)
                if "openai" in request.url.path:
                    data = openai_policy(data)
                request._body = json.dumps(data).encode("utf-8")
            except json.JSONDecodeError as e:
                log.error("Error loading request body into a dictionary:", e)

        return await call_next(request)
