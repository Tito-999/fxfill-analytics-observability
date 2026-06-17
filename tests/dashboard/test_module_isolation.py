"""Verify Plotly and Streamlit modules are real after all tests."""

import unittest.mock

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def test_plotly_modules_are_not_magic_mocks():
    assert not isinstance(px, unittest.mock.MagicMock)
    assert not isinstance(go, unittest.mock.MagicMock)
    assert not isinstance(st, unittest.mock.MagicMock)


def test_plotly_express_returns_real_figure():
    figure = px.bar({"category": ["A", "B"], "value": [1, 2]}, x="category", y="value")
    assert isinstance(figure, go.Figure)
