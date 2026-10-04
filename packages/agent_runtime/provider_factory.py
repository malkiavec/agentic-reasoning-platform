import os
from .gateway import ModelGateway
from .routing import ModelRoute, ModelRouter
from .providers import OpenAIProvider, AnthropicProvider, GeminiProvider, OpenAICompatibleProvider

def build_gateway_from_env() -> ModelGateway:
    gateway=ModelGateway(); routes=[]
    if os.getenv("OPENAI_API_KEY"):
        gateway.register("openai", OpenAIProvider(os.environ["OPENAI_API_KEY"]))
        routes.append(ModelRoute("openai", os.getenv("OPENAI_MODEL","gpt-6-luna"), 1_000_000, frozenset({"reasoning","structured_output","tool_calling","vision"}), ("anthropic","gemini","local")))
    if os.getenv("ANTHROPIC_API_KEY"):
        gateway.register("anthropic", AnthropicProvider(os.environ["ANTHROPIC_API_KEY"]))
        routes.append(ModelRoute("anthropic", os.getenv("ANTHROPIC_MODEL","claude-opus-4-6"), 1_000_000, frozenset({"reasoning","structured_output","tool_calling","vision"}), ("gemini","local")))
    if os.getenv("GEMINI_API_KEY"):
        gateway.register("gemini", GeminiProvider(os.environ["GEMINI_API_KEY"]))
        routes.append(ModelRoute("gemini", os.getenv("GEMINI_MODEL","gemini-3.1-pro"), 1_000_000, frozenset({"reasoning","structured_output","tool_calling","vision","video","pdf"}), ("openai","local")))
    if os.getenv("LOCAL_MODEL"):
        gateway.register("local", OpenAICompatibleProvider(base_url=os.getenv("LOCAL_BASE_URL","http://localhost:11434/v1")))
        routes.append(ModelRoute("local", os.environ["LOCAL_MODEL"], int(os.getenv("LOCAL_CONTEXT_TOKENS","128000")), frozenset({"structured_output","tool_calling","vision"})))
    if not routes: raise RuntimeError("no_llm_provider_configured")
    gateway.router=ModelRouter(routes); return gateway
