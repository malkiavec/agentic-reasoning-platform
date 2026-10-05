from packages.tools.catalog import build_default_registry

REAL_INTEGRATIONS={"gitlab","slack","discord","gmail","google_drive","notion","linear","jira","databases","webhooks","mcp"}

def test_real_integrations_are_registered_and_placeholder_families_are_absent():
    registry=build_default_registry()
    names={spec.name for spec in registry.list()}
    assert REAL_INTEGRATIONS <= names
    assert not any(name.startswith("placeholder.") for name in names)

def test_high_impact_integrations_are_approval_gated():
    registry=build_default_registry()
    for name in {"gmail","databases","webhooks","mcp"}:
        assert registry.get(name).requires_approval is True
