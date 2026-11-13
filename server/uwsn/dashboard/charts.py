"""Plotly figures for the dashboard. Each function takes DataFrames and returns a Figure."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.colors as pc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# One colour per sensor, the same in every chart (Okabe-Ito based, readable in light and dark).
# Grey is reserved for flagged data.
SENSOR_COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#7A5195",
                 "#B8860B"]
FLAGGED_COLOR = "#9AA0A6"
SPEED_SCALE = "Viridis"
_M_PER_DEG = 111_320.0


def sensor_color_map(device_ids) -> dict[str, str]:
    return {d: SENSOR_COLORS[i % len(SENSOR_COLORS)] for i, d in enumerate(sorted(device_ids))}


def short_id(device_id: str) -> str:
    return device_id.split("-")[-1]


# ---------------------------------------------------------------- map

def _offset(lat, lon, bearing_deg, dist_m):
    b = math.radians(bearing_deg)
    return (lat + dist_m * math.cos(b) / _M_PER_DEG,
            lon + dist_m * math.sin(b) / (_M_PER_DEG * math.cos(math.radians(lat))))


def _fit_view(lats, lons, width_px=560, height_px=460):
    """Centre and zoom that show all points with some margin; also the extent in metres."""
    lat_c, lon_c = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
    d_lat = max(max(lats) - min(lats), 0.004)
    d_lon = max(max(lons) - min(lons), 0.004)
    z_lon = math.log2(0.55 * width_px * 360 / (512 * d_lon))
    z_lat = math.log2(0.55 * height_px * 360 * math.cos(math.radians(lat_c)) / (512 * d_lat))
    extent_m = max(d_lat * _M_PER_DEG, d_lon * _M_PER_DEG * math.cos(math.radians(lat_c)))
    return lat_c, lon_c, float(np.clip(min(z_lon, z_lat), 3, 17)), extent_m


def _arrow_lines(rows: pd.DataFrame, arrow_len_m: float):
    """Line coordinates (None-separated) of one arrow per row: from the sensor towards where the
    wind blows TO, with a small head. rows needs columns lat, lon, direction (wind comes FROM)."""
    lats, lons = [], []
    for _, r in rows.iterrows():
        to = (r["direction"] + 180) % 360
        tip = _offset(r["lat"], r["lon"], to, arrow_len_m)
        h1 = _offset(*tip, to + 180 - 28, 0.35 * arrow_len_m)
        h2 = _offset(*tip, to + 180 + 28, 0.35 * arrow_len_m)
        lats += [r["lat"], tip[0], None, h1[0], tip[0], h2[0], None]
        lons += [r["lon"], tip[1], None, h1[1], tip[1], h2[1], None]
    return lats, lons


def sensor_map(summary: pd.DataFrame, dark: bool = False, height: int = 460) -> go.Figure:
    """One marker per sensor: colour = mean speed, arrow = where the wind blows TO.

    summary: index device_id, columns site, lat, lon, mean_speed, direction, max_gust,
    availability. Sensors without position are left out; sensors without data are grey."""
    s = summary.dropna(subset=["lat", "lon"])
    fig = go.Figure()
    if s.empty:
        return fig
    lat_c, lon_c, zoom, extent_m = _fit_view(s["lat"].tolist(), s["lon"].tolist(), height_px=height)
    ink = "#F1F5F9" if dark else "#1E293B"

    arrow_len = 0.15 * extent_m
    lats, lons = _arrow_lines(s.dropna(subset=["direction"]), arrow_len)
    fig.add_trace(go.Scattermap(lat=lats, lon=lons, mode="lines", line=dict(width=3, color=ink),
                                hoverinfo="skip", showlegend=False))

    def custom(df):
        return np.column_stack([
            df.index, df["site"], df["mean_speed"].round(2), df["direction"].round(0),
            df["max_gust"].round(1), (100 * df["availability"]).round(0)])

    template = ("<b>%{customdata[0]}</b> %{customdata[1]}<br>"
                "Mean speed: %{customdata[2]} m/s<br>Wind from: %{customdata[3]}°<br>"
                "Max gust: %{customdata[4]} m/s<br>Availability: %{customdata[5]}%<extra></extra>")
    with_data = s.dropna(subset=["mean_speed"])
    if not with_data.empty:
        cmax = max(2.0, math.ceil(with_data["mean_speed"].max()))
        fig.add_trace(go.Scattermap(
            lat=with_data["lat"], lon=with_data["lon"], mode="markers+text",
            marker=dict(size=20, color=with_data["mean_speed"], colorscale=SPEED_SCALE,
                        cmin=0, cmax=cmax, opacity=1,
                        colorbar=dict(title=dict(text="Mean speed<br>(m/s)"), thickness=12,
                                      len=0.6, x=0.99, xanchor="right", y=0.5)),
            text=[short_id(i) for i in with_data.index], textposition="bottom right",
            textfont=dict(size=12, color=ink), customdata=custom(with_data),
            hovertemplate=template, showlegend=False))
    no_data = s[s["mean_speed"].isna()]
    if not no_data.empty:
        fig.add_trace(go.Scattermap(
            lat=no_data["lat"], lon=no_data["lon"], mode="markers+text",
            marker=dict(size=20, color=FLAGGED_COLOR), text=[short_id(i) for i in no_data.index],
            textposition="bottom right", textfont=dict(size=12, color=ink),
            hovertemplate="<b>%{text}</b>: no usable data in this period<extra></extra>",
            showlegend=False))
    fig.update_layout(
        map=dict(style="carto-darkmatter" if dark else "carto-positron",
                 center=dict(lat=lat_c, lon=lon_c), zoom=zoom),
        margin=dict(l=0, r=0, t=0, b=0), height=height)
    return fig


def sensor_map_animated(steps: pd.DataFrame, positions: pd.DataFrame, step_hours: int,
                        dark: bool = False, height: int = 520) -> go.Figure:
    """The sensor map over time: a slider (and Play button) moves through the time steps.
    It runs in the browser, so dragging is instant and does not rerun the app.

    steps      one row per (step_ts, device_id): mean_speed_ms, gust_ms, direction (from data.map_steps)
    positions  index device_id, columns site, lat, lon
    The colour scale and arrow length are fixed, so frames can be compared with each other."""
    pos = positions.dropna(subset=["lat", "lon"])
    fig = go.Figure()
    if pos.empty or steps.empty:
        return fig
    slider_px = 90
    lat_c, lon_c, zoom, extent_m = _fit_view(pos["lat"].tolist(), pos["lon"].tolist(),
                                             height_px=height - slider_px)
    ink = "#F1F5F9" if dark else "#1E293B"
    arrow_len = 0.15 * extent_m
    cmax = max(2.0, math.ceil(steps["mean_speed_ms"].max()))
    by_step = {t: g.set_index("device_id") for t, g in steps.groupby("step_ts")}
    times = pd.date_range(steps["step_ts"].min(), steps["step_ts"].max(), freq=f"{step_hours}h")
    fmt = "%d %b %Y" if step_hours >= 24 else "%d %b %Y  %H:%M"
    unit = "" if step_hours >= 24 else " UTC"
    hover = ("<b>%{customdata[0]}</b> %{customdata[1]}<br>Mean speed: %{customdata[2]} m/s<br>"
             "Wind from: %{customdata[3]}°<br>Max gust: %{customdata[4]} m/s<extra></extra>")

    def snapshot(t):
        have = pos.join(by_step.get(t, pd.DataFrame(columns=["mean_speed_ms", "gust_ms", "direction"])),
                        how="left")
        have = have.dropna(subset=["mean_speed_ms"]) if "mean_speed_ms" in have else have.iloc[0:0]
        missing = pos.drop(have.index)
        a_lat, a_lon = _arrow_lines(have.dropna(subset=["direction"]), arrow_len)
        custom = np.column_stack([have.index, have["site"], have["mean_speed_ms"].round(2),
                                  have["direction"].round(0), have["gust_ms"].round(1)]) if len(have) else []
        return dict(
            arrows=dict(lat=a_lat, lon=a_lon),
            data=dict(lat=have["lat"], lon=have["lon"], marker=dict(color=have["mean_speed_ms"]),
                      text=[short_id(i) for i in have.index], customdata=custom),
            missing=dict(lat=missing["lat"], lon=missing["lon"], text=[short_id(i) for i in missing.index]))

    def label(t):
        return f"{t:{fmt}}{unit}"

    frames = []
    for t in times:
        snap = snapshot(t)
        frames.append(go.Frame(name=label(t), traces=[0, 1, 2],
                               data=[go.Scattermap(**snap["arrows"]), go.Scattermap(**snap["data"]),
                                     go.Scattermap(**snap["missing"])]))
    first = snapshot(times[0])           # the map starts at the beginning, so Play runs straight away
    fig.add_trace(go.Scattermap(**first["arrows"], mode="lines", line=dict(width=3, color=ink),
                                hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scattermap(
        lat=first["data"]["lat"], lon=first["data"]["lon"], mode="markers+text", showlegend=False,
        marker=dict(size=20, colorscale=SPEED_SCALE, cmin=0, cmax=cmax, opacity=1,
                    color=first["data"]["marker"]["color"],
                    colorbar=dict(title=dict(text="Mean speed<br>(m/s)"), thickness=12, len=0.6,
                                  x=0.99, xanchor="right", y=0.5)),
        text=first["data"]["text"], textposition="bottom right", textfont=dict(size=12, color=ink),
        customdata=first["data"]["customdata"], hovertemplate=hover))
    fig.add_trace(go.Scattermap(
        **first["missing"], mode="markers+text", showlegend=False,
        marker=dict(size=20, color=FLAGGED_COLOR), textposition="bottom right",
        textfont=dict(size=12, color=ink),
        hovertemplate="<b>%{text}</b>: no usable data in this step<extra></extra>"))
    fig.frames = frames

    def anim(duration, redraw=True):
        return dict(frame=dict(duration=duration, redraw=redraw), transition=dict(duration=0),
                    mode="immediate")

    invisible = "rgba(0,0,0,0)"
    fig.update_layout(
        map=dict(style="carto-darkmatter" if dark else "carto-positron",
                 center=dict(lat=lat_c, lon=lon_c), zoom=zoom),
        margin=dict(l=0, r=0, t=0, b=slider_px), height=height,
        updatemenus=[dict(
            type="buttons", direction="left", x=0, xanchor="left", y=-0.01, yanchor="top",
            pad=dict(t=22, l=0), showactive=False, bgcolor="rgba(128,128,128,0.18)",
            bordercolor="rgba(128,128,128,0.4)", font=dict(color=ink),
            buttons=[dict(label="▶ Play", method="animate", args=[None, dict(anim(120), fromcurrent=True)]),
                     dict(label="❚❚ Pause", method="animate", args=[[None], anim(0, redraw=False)])])],
        sliders=[dict(
            active=0, x=0.2, len=0.8, xanchor="left", y=-0.01, yanchor="top",
            pad=dict(t=8, b=0, l=0, r=0), ticklen=0, tickcolor=invisible, bgcolor="rgba(128,128,128,0.35)",
            bordercolor=invisible, activebgcolor="#2563EB", font=dict(color=invisible, size=1),
            currentvalue=dict(prefix="", font=dict(size=14, color=ink), xanchor="left"),
            steps=[dict(method="animate", label=f.name, args=[[f.name], anim(0)]) for f in frames])])
    return fig


# ---------------------------------------------------------------- time series

_ROWS = [("mean_speed_ms", "Mean speed (m/s)"), ("gust_ms", "Gust (m/s)"), ("temp_c", "Temperature (°C)")]


def _axis_range(values: pd.Series, from_zero: bool):
    """y-axis range that fits the (reliable) line data, so a few flagged outliers cannot squash it."""
    v = values.dropna()
    if v.empty:
        return None
    lo, hi = (0.0 if from_zero else v.min()), v.max()
    pad = max(hi - lo, 1.0) * 0.08
    return [lo if from_zero else lo - pad, hi + pad]


def timeseries_figure(lines: pd.DataFrame, flagged: dict[str, pd.DataFrame], colors: dict[str, str],
                      height: int = 760) -> go.Figure:
    """Speed, gust and temperature of every sensor, stacked with a shared time axis.
    `lines`: device_id, ts, mean_speed_ms, gust_ms, temp_c (NaN = break in the line).
    `flagged`: rows to draw as grey points, per column (may be empty). Flagged values outside the
    axis range are drawn on the edge as triangles; hover shows the real value."""
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05)
    for dev, d in lines.groupby("device_id"):
        for row, (col, label) in enumerate(_ROWS, start=1):
            fig.add_trace(go.Scattergl(
                x=d["ts"], y=d[col], mode="lines", name=dev, legendgroup=dev,
                showlegend=(row == 1), line=dict(width=1, color=colors.get(dev)), opacity=0.85,
                connectgaps=False, hovertemplate=f"{dev}: %{{y:.1f}}<extra></extra>"), row=row, col=1)

    first = True
    for row, (col, label) in enumerate(_ROWS, start=1):
        rng = _axis_range(lines[col], from_zero=(col != "temp_c"))
        if rng:
            fig.update_yaxes(range=rng, row=row, col=1)
        f = flagged.get(col)
        if f is None or f.empty:
            continue
        lo, hi = rng if rng else (f[col].min(), f[col].max())
        shown = f[col].clip(lo, hi)
        symbol = np.where(f[col] > hi, "triangle-up", np.where(f[col] < lo, "triangle-down", "circle"))
        fig.add_trace(go.Scattergl(
            x=f["ts"], y=shown, mode="markers", name="Flagged (unreliable)", legendgroup="flagged",
            showlegend=first, marker=dict(size=6, color=FLAGGED_COLOR, symbol=symbol, opacity=0.9),
            customdata=np.column_stack([f["device_id"], f["flags_text"], f[col].round(1)]),
            hovertemplate="%{customdata[0]}: %{customdata[2]}<br>%{customdata[1]}<extra></extra>"),
            row=row, col=1)
        first = False
    for row, (_, label) in enumerate(_ROWS, start=1):
        fig.update_yaxes(title_text=label, row=row, col=1, zeroline=False)
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), hovermode="x",
                      legend=dict(orientation="h", y=1.04, yanchor="bottom", x=0), dragmode="zoom")
    return fig


# ---------------------------------------------------------------- mean speed over time

_NETWORK_COLOR = "#8892A0"


def daily_cycle_figure(cycle: pd.DataFrame, colors: dict[str, str], height: int = 380) -> go.Figure:
    """Mean wind speed by hour of the day, one line per sensor."""
    fig = go.Figure()
    for dev, d in cycle.groupby("device_id"):
        fig.add_trace(go.Scatter(x=d["hour"], y=d["mean_speed_ms"], mode="lines+markers", name=dev,
                                 line=dict(width=2, color=colors.get(dev)), marker=dict(size=5),
                                 hovertemplate=f"{dev}: %{{y:.2f}} m/s<extra></extra>"))
    fig.update_xaxes(title_text="Hour of day (local time)", dtick=3, range=[-0.5, 23.5])
    fig.update_yaxes(title_text="Mean speed (m/s)", rangemode="tozero")
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified",
                      legend=dict(orientation="h", y=1.04, yanchor="bottom", x=0))
    return fig


def daily_mean_figure(daily: pd.DataFrame, colors: dict[str, str], height: int = 380) -> go.Figure:
    """Mean wind speed per day, one line per sensor and a thick grey line for the network mean."""
    fig = go.Figure()
    for dev, d in daily.groupby("device_id"):
        network = dev == "Network"
        fig.add_trace(go.Scatter(
            x=d["day"], y=d["mean_speed_ms"], mode="lines+markers", name="Network mean" if network else dev,
            line=dict(width=4 if network else 1.5, color=_NETWORK_COLOR if network else colors.get(dev),
                      dash="dot" if network else "solid"),
            marker=dict(size=6 if network else 4), opacity=1 if network else 0.8,
            hovertemplate=f"{dev}: %{{y:.2f}} m/s<extra></extra>"))
    fig.update_yaxes(title_text="Mean speed (m/s)", rangemode="tozero")
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified",
                      legend=dict(orientation="h", y=1.04, yanchor="bottom", x=0))
    return fig


def hour_by_day_figure(grid: pd.DataFrame, height: int = 380) -> go.Figure:
    """Heatmap of the network mean speed: days left to right, hours of the day top to bottom."""
    fig = go.Figure(go.Heatmap(
        x=grid.columns, y=grid.index, z=grid.to_numpy(), colorscale=SPEED_SCALE, zmin=0,
        colorbar=dict(title=dict(text="m/s"), thickness=12), xgap=1, ygap=1,
        hovertemplate="%{x|%d %b} %{y}:00<br>%{z:.2f} m/s<extra></extra>"))
    fig.update_yaxes(title_text="Hour of day (local time)", autorange="reversed", dtick=3)
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0))
    return fig


# ---------------------------------------------------------------- wind roses

def wind_rose_figure(roses: dict[str, pd.DataFrame], titles: dict[str, str], n_cols: int = 4,
                     row_height: int = 330) -> go.Figure:
    """One wind rose per sensor in a grid. All roses share the same radial scale so they can
    be compared. `roses`: device_id -> Analyzer.wind_rose() table."""
    ids = list(roses)
    n_rows = max(1, math.ceil(len(ids) / n_cols))
    fig = make_subplots(rows=n_rows, cols=n_cols, specs=[[{"type": "polar"}] * n_cols] * n_rows,
                        subplot_titles=[titles.get(i, i) for i in ids],
                        horizontal_spacing=0.04, vertical_spacing=0.14 / n_rows ** 0.5)
    classes = list(next(iter(roses.values()))["speed_class"].cat.categories) if ids else []
    palette = pc.sample_colorscale(SPEED_SCALE, [i / max(len(classes) - 1, 1) for i in range(len(classes))])
    rmax = max((r.groupby("sector_deg")["frequency"].sum().max() for r in roses.values()), default=1)
    rmax = max(5.0, math.ceil(rmax * 1.1 / 5) * 5)

    for k, dev in enumerate(ids):
        row, col = divmod(k, n_cols)
        for cls, color in zip(classes, palette):
            r = roses[dev][roses[dev]["speed_class"] == cls]
            fig.add_trace(go.Barpolar(
                theta=r["sector_deg"], r=r["frequency"], name=cls, legendgroup=cls, showlegend=(k == 0),
                marker=dict(color=color, line=dict(width=0)), width=[360 / len(r)] * len(r),
                hovertemplate="from %{theta}°: %{r:.1f}%<extra>" + cls + "</extra>"),
                row=row + 1, col=col + 1)
    polar = dict(
        angularaxis=dict(direction="clockwise", rotation=90, tickmode="array",
                         tickvals=[0, 90, 180, 270], ticktext=["N", "E", "S", "W"]),
        radialaxis=dict(range=[0, rmax], ticksuffix="%", angle=45, tickangle=45, showline=False),
        bgcolor="rgba(0,0,0,0)", hole=0.04)
    fig.update_layout(**{f"polar{'' if i == 0 else i + 1}": polar for i in range(len(ids))})
    fig.update_layout(height=row_height * n_rows + 40, margin=dict(l=20, r=20, t=40, b=0),
                      legend=dict(orientation="h", y=-0.02, yanchor="top", x=0.5, xanchor="center",
                                  title=dict(text="Wind speed")))
    fig.update_annotations(font_size=13)
    return fig
