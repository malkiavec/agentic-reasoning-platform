import os

def test_provider_factory_module_imports():
    from packages.agent_runtime.provider_factory import build_gateway_from_env
    assert callable(build_gateway_from_env)
