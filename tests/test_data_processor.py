"""Tests for data processing functionality."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from uiGenerator.models.data_processor import LICPMSfunctions


class TestLICPMSfunctions:
    """Test suite for LICPMSfunctions class."""

    def test_import_data_generic_success(self, tmp_path):
        """Test successful CSV import."""
        # Create a mock view
        mock_view = Mock()
        processor = LICPMSfunctions(view=mock_view)

        # Create a test CSV file
        csv_file = tmp_path / "test_data.csv"
        csv_content = """Header
Time 56Fe;56Fe;Time 60Ni;60Ni
0;100;0;200
1;150;1;250
2;200;2;300
"""
        csv_file.write_text(csv_content)

        # Test import
        data = processor.importData_generic(str(csv_file))

        assert isinstance(data, pd.DataFrame)
        assert not data.empty

    def test_import_data_generic_file_not_found(self):
        """Test import with non-existent file."""
        mock_view = Mock()
        processor = LICPMSfunctions(view=mock_view)

        with pytest.raises(FileNotFoundError):
            processor.importData_generic("/nonexistent/file.csv")
