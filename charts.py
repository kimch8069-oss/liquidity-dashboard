"""plotly 그래프. 휴대폰에서도 읽기 쉽게 범례는 아래, 여백은 작게."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PERIODS = {"1년": 365, "3년": 365 * 3, "5년": 365 * 5, "전체": None}
COLORS = ["#2563eb", "#f97316", "#10b981", "#a855f7", "#e11d48"]
UP, DOWN = "#3b82f6", "#ef4444"  # 금리차 막대: 정상 / 역전
STATIC = {"displayModeBar": False}


def cut(s: pd.Series, period: str) -> pd.Series:
    s = s.dropna()
    days = PERIODS.get(period)
    if days is None or s.empty:
        return s
    return s[s.index >= s.index.max() - pd.Timedelta(days=days)]


def _layout(fig: go.Figure, title: str, unit: str = "", height: int = 340) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        height=height,
        margin=dict(l=8, r=8, t=44, b=8),
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, font=dict(size=11)),
        hovermode="x unified",
        font=dict(size=12),
    )
    fig.update_xaxes(tickfont=dict(size=11))
    fig.update_yaxes(tickfont=dict(size=11), title_text=unit, title_font=dict(size=11))
    return fig


def _latest_marker(fig, s: pd.Series, color: str, decimals: int, **kw):
    fig.add_trace(go.Scatter(
        x=[s.index[-1]], y=[s.iloc[-1]], mode="markers+text",
        marker=dict(size=8, color=color), text=[f"{s.iloc[-1]:,.{decimals}f}"],
        textposition="top left", textfont=dict(size=11, color=color),
        showlegend=False, hoverinfo="skip"), **kw)


def line(series: list[tuple[str, pd.Series]], title: str, period: str, unit: str = "",
         refs: list[tuple[float, str]] = (), decimals: int = 2) -> go.Figure:
    fig = go.Figure()
    for i, (name, s) in enumerate(series):
        s = cut(s, period)
        if s.empty:
            continue
        color = COLORS[i % len(COLORS)]
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name=name,
                                 line=dict(color=color, width=2)))
        _latest_marker(fig, s, color, decimals)
    for y, label in refs:
        fig.add_hline(y=y, line_dash="dot", line_color="gray", opacity=0.7,
                      annotation_text=label, annotation_position="bottom right",
                      annotation_font_size=10)
    fig.update_layout(showlegend=len(series) > 1)
    return _layout(fig, title, unit)


def spread_bar(name: str, s: pd.Series, title: str, period: str, unit: str = "%p",
               decimals: int = 2) -> go.Figure:
    s = cut(s, period)
    fig = go.Figure(go.Bar(x=s.index, y=s.values, name=name,
                           marker_color=[DOWN if v < 0 else UP for v in s.values],
                           marker_line_width=0))
    if not s.empty:
        _latest_marker(fig, s, DOWN if s.iloc[-1] < 0 else UP, decimals)
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(showlegend=False, bargap=0)
    return _layout(fig, title, unit)


def dual(left: tuple[str, pd.Series, str], right: tuple[str, pd.Series, str], title: str,
         period: str) -> go.Figure:
    """왼쪽 축과 오른쪽 축에 서로 다른 단위의 시리즈를 겹쳐 그린다."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for (name, s, unit), sec, color in ((left, False, COLORS[0]), (right, True, COLORS[1])):
        s = cut(s, period)
        if s.empty:
            continue
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name=name,
                                 line=dict(color=color, width=2)), secondary_y=sec)
        _latest_marker(fig, s, color, 2 if abs(s.iloc[-1]) < 100 else 0, secondary_y=sec)
        fig.update_yaxes(title_text=unit, title_font=dict(size=11), tickfont=dict(size=11),
                         secondary_y=sec, showgrid=not sec)
    _layout(fig, title)
    fig.update_yaxes(title_text=left[2], secondary_y=False)
    fig.update_yaxes(title_text=right[2], secondary_y=True)
    return fig


def sparkline(s: pd.Series, days: int = 365) -> go.Figure:
    s = s.dropna()
    s = s[s.index >= s.index.max() - pd.Timedelta(days=days)]
    up = len(s) > 1 and s.iloc[-1] >= s.iloc[0]
    fig = go.Figure(go.Scatter(x=s.index, y=s.values, mode="lines",
                               line=dict(color=COLORS[0] if up else COLORS[1], width=1.5),
                               hoverinfo="skip"))
    fig.update_layout(height=50, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig
