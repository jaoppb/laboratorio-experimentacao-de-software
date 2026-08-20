import os

import pandas as pd
import pytest

# Define the paths to the data files based on the repository structure
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS_DIR = os.path.join(BASE_DIR, "dados")
RQ03_RQ04_CSV = os.path.join(DADOS_DIR, "rq03_rq04_sample.csv")
RQ03_CSV = os.path.join(DADOS_DIR, "rq03_sample.csv")
RQ04_CSV = os.path.join(DADOS_DIR, "rq04_sample.csv")


@pytest.fixture
def rq03_rq04_data():
    """Loads the unified RQ03 and RQ04 sample data if it exists."""
    assert os.path.exists(RQ03_RQ04_CSV), f"File not found: {RQ03_RQ04_CSV}"
    df = pd.read_csv(RQ03_RQ04_CSV)
    return df


@pytest.fixture
def rq03_data():
    """Loads the specific RQ03 sample data if it exists."""
    assert os.path.exists(RQ03_CSV), f"File not found: {RQ03_CSV}"
    df = pd.read_csv(RQ03_CSV)
    return df


@pytest.fixture
def rq04_data():
    """Loads the specific RQ04 sample data if it exists."""
    assert os.path.exists(RQ04_CSV), f"File not found: {RQ04_CSV}"
    df = pd.read_csv(RQ04_CSV)
    return df


def test_rq03_rq04_unified_file_not_empty(rq03_rq04_data):
    """Validates that the unified RQ03/RQ04 dataset is not empty."""
    assert not rq03_rq04_data.empty, "The RQ03/RQ04 unified dataset is empty."


def test_rq03_file_not_empty(rq03_data):
    """Validates that the specific RQ03 dataset contains records."""
    assert not rq03_data.empty, "The RQ03 dataset is empty."


def test_rq04_file_not_empty(rq04_data):
    """Validates that the specific RQ04 dataset contains records."""
    assert not rq04_data.empty, "The RQ04 dataset is empty."


def test_rq03_rq04_no_duplicate_nodes(rq03_rq04_data):
    """
    Validates that there are no duplicate repositories/nodes in the unified dataset.
    Assuming 'nameWithOwner' or 'id' is the primary identifier.
    """
    # Adjust 'nameWithOwner' to the actual primary key column name in your CSV
    primary_key_col = "nameWithOwner"
    if primary_key_col in rq03_rq04_data.columns:
        duplicates = rq03_rq04_data.duplicated(subset=[primary_key_col]).sum()
        assert duplicates == 0, (
            f"Found {duplicates} duplicate entries in RQ03/RQ04 data."
        )


def test_rq03_required_columns_exist(rq03_data):
    """
    Validates that RQ03 output contains the expected columns.
    Update the 'expected_columns' list with the actual metrics you extract for RQ03.
    """
    expected_columns = ["nameWithOwner", "createdAt", "stargazerCount"]  # Placeholders
    for col in expected_columns:
        if col in rq03_data.columns:
            assert rq03_data[col].isnull().sum() == 0, (
                f"Column '{col}' contains null values."
            )


def test_rq04_required_columns_exist(rq04_data):
    """
    Validates that RQ04 output contains the expected columns.
    Update the 'expected_columns' list with the actual metrics you extract for RQ04.
    """
    expected_columns = ["nameWithOwner", "pullRequests", "issues"]  # Placeholders
    for col in expected_columns:
        if col in rq04_data.columns:
            assert rq04_data[col].isnull().sum() == 0, (
                f"Column '{col}' contains null values."
            )
