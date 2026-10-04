import pytest
from packages.security.outputs import OutputValidator

def test_unsafe_output_rejected():
    with pytest.raises(ValueError):
        OutputValidator().validate("<script>alert(1)</script>")
