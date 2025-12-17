"""Tests for calibration functionality."""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
from uiGenerator.models.calibration import CalibrateFunctions


class TestCalibrateFunctions:
    """Test suite for CalibrateFunctions class."""

    def test_initialization(self):
        """Test CalibrateFunctions initialization."""
        mock_calview = Mock()
        mock_mainview = Mock()

        cal_funcs = CalibrateFunctions(calview=mock_calview, mainview=mock_mainview)

        assert cal_funcs._calview == mock_calview
        assert cal_funcs._mainview == mock_mainview
        assert cal_funcs.ntime == True
