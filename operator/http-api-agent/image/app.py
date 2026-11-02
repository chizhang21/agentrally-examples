"""Minimal HTTP agent used by the AgentRally quick start."""
import os
import secrets

from fastapi import FastAPI, Header, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openai import OpenAIProvider

api_key = os.getenv("OPENAI_API_KEY", "")
api_token = os.getenv("API_TOKEN", "")
model_name = os.getenv("AGENTRALLY_MODEL_NAME", "")
mode = "model" if api_key else "demo"

if api_key:
    if not api_token or not model_name:
        raise RuntimeError("Model mode requires API_TOKEN and AGENTRALLY_MODEL_NAME")
    model = OpenAIChatModel(model_name, provider=OpenAIProvider(openai_client=AsyncOpenAI(
        api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL"), max_retries=0, timeout=20,
    )))
else:
    model = TestModel(custom_output_text="AgentRally demo agent is ready.")

# No filesystem, shell, browser or other tools are registered.
agent = Agent(model, instructions="Answer briefly and clearly.", retries=0,
              model_settings={"max_tokens": 256})
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4096)


@app.get("/healthz")
async def health():
    return {"status": "ok", "mode": mode}


@app.post("/chat")
async def chat(request: ChatRequest, authorization: str = Header(default="")):
    if api_token and not secrets.compare_digest(authorization.encode(), ("Bearer " + api_token).encode()):
        raise HTTPException(status_code=401, detail="Authentication required",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        result = await agent.run(request.message)
    except Exception:
        # Provider errors can contain request details; return no credentials or prompts.
        raise HTTPException(status_code=502, detail="Model request failed") from None
    return {"response": result.output, "mode": mode}
