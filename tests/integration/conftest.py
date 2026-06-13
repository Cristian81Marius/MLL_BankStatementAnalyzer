import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_content_validator():
    """Integration tests use minimal_pdf which has no text — skip the validator."""
    with patch(
        "statement_analysis.api.routes.validate_statement_content",
        return_value=(True, ""),
    ):
        yield
