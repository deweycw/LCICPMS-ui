"""Pytest configuration and fixtures."""

import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_icpms_data():
    """Create sample ICP-MS data for testing."""
    data = {
        'Time 56Fe': np.arange(0, 100, 1),
        '56Fe': np.random.randint(100, 1000, 100),
        'Time 60Ni': np.arange(0, 100, 1),
        '60Ni': np.random.randint(100, 1000, 100),
        'Time 63Cu': np.arange(0, 100, 1),
        '63Cu': np.random.randint(100, 1000, 100),
    }
    return pd.DataFrame(data)
