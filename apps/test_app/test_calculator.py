# /// script
# requires-python = ">=3.8"
# dependencies = ["pytest"]
# ///
"""Tests for calculator module."""

from calculator import add, subtract, multiply, divide
import pytest


def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5


def test_multiply():
    assert multiply(3, 4) == 12
    assert multiply(0, 100) == 0
    assert multiply(-2, 3) == -6


def test_divide():
    assert divide(10, 2) == 5.0
    assert divide(7, 2) == 3.5


def test_divide_by_zero():
    """This test WILL FAIL because calculator.py has no zero-division guard."""
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(10, 0)
