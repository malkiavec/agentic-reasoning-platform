from packages.agent_runtime.routing import ModelRoute, ModelRouter

def test_router_prefers_context_capacity():
    router = ModelRouter([
        ModelRoute("a", "small", 100_000, frozenset({"text"})),
        ModelRoute("b", "long", 1_000_000, frozenset({"text", "image"})),
    ])
    assert router.choose(required={"image"}).model == "long"
