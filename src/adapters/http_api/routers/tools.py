"""OpenAI Function Calling 格式工具定义 — HTTP API 端点。"""

from fastapi import APIRouter
from pydantic import BaseModel
from ...openai.tools import get_openai_tools, execute_tool

router = APIRouter()


@router.get("")
def list_tools():
    """返回 OpenAI Function Calling 格式的工具列表。"""
    return {"tools": get_openai_tools()}


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict


@router.post("/execute")
def execute_tool_call(body: ToolCallRequest):
    """执行一个工具调用并返回结果。"""
    result = execute_tool(body.name, body.arguments)
    return {"name": body.name, "result": result}
