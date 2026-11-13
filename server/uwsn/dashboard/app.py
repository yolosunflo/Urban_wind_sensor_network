"""Street microclimate dashboard.

    cd server
    python scripts/seed_fake_data.py      # once: fake data, if you have no real sensors yet
    streamlit run uwsn/dashboard/app.py
"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))      # so "import uwsn" works

import pandas as pd                                                # noqa: E402
import streamlit as st                                             # noqa: E402

from uwsn.analysis import Analyzer                                 # noqa: E402
from uwsn.config import SETTINGS                                   # noqa: E402
from uwsn.dashboard import charts, data                            # noqa: E402
from uwsn.models import QualityFlag                                # noqa: E402
from uwsn.storage import Repository                                # noqa: E402

st.set_page_config(page_title="Street microclimate", page_icon=":material/air:", layout="wide")

REFRESH = "1m"          # how often new measurements are picked up from the database
FLAGGED_MODES = {"Hide": "hide", "Grey out": "grey", "Show": "show"}


# ---------------------------------------------------------------- data loading (cached)

@st.cache_resource
def get_repo() -> Repository:
    return Repository(SETTINGS.db_path)


@st.cache_data(ttl=REFRESH)
def load_sensors() -> pd.DataFrame:
    return get_repo().load_sensors()


@st.cache_data(ttl=REFRESH)
def load_measurements(device_ids: tuple | None, start: date | None = None, end: date | None = None,
                      usable_only: bool = False) -> pd.DataFrame:
    return get_repo().load_measurements(None if device_ids is None else list(device_ids),
                                        start, end, usable_only)


@st.cache_data(ttl=REFRESH)
def analyse_hourly(df_ok: pd.DataFrame) -> pd.DataFrame:
    return Analyzer(df_ok).hourly()


def dark_theme() -> bool:
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


# ---------------------------------------------------------------- page

everything = load_measurements(device_ids=None)                    # all sensors, all time
if everything.empty:
    st.title("Street microclimate")
    st.info("No measurements in the database yet.", icon=":material/database:")
    st.markdown("For a demo with fake data, run `python scripts/seed_fake_data.py` "
                f"from the `server` folder (database: `{SETTINGS.db_path}`).")
    st.stop()

sensors = load_sensors()
all_ids = sorted(everything["device_id"].unique())
sites = (sensors.set_index("device_id")["site_description"].to_dict() if not sensors.empty else {})
first_day, last_day = everything["ts"].min().date(), everything["ts"].max().date()

with st.sidebar:
    st.header("Filters")
    selected = st.multiselect(
        "Sensors", all_ids, default=all_ids, key="sensors",
        help="Site names are shown on the map and in the tables.")
    period = st.date_input("Period", key="period", value=(first_day, last_day), min_value=first_day,
                           max_value=last_day, format="YYYY-MM-DD")
    flagged_label = st.segmented_control(
        "Flagged data", list(FLAGGED_MODES), default="Grey out", key="flagged",
        help="Windows the server marked as unreliable (spike, stuck sensor, out of range, "
             "sensor fault). Statistics, the map and wind roses always ignore them.")
    resolution = st.segmented_control("Time series resolution", ["10 min", "Hourly"], default="10 min", key="resolution",
                                      help="Hourly values use usable data only.")
    low_wind_ms = st.slider("Calm threshold (m/s)", 0.5, 3.0, 1.0, 0.1, key="low_wind",
                            help="Wind below this speed counts as calm: a sign of poor ventilation.")

flagged_mode = FLAGGED_MODES[flagged_label or "Grey out"]
resolution = resolution or "10 min"

if not selected:
    st.title("Street microclimate")
    st.warning("Select at least one sensor in the sidebar.", icon=":material/sensors:")
    st.stop()
if not isinstance(period, tuple) or len(period) != 2:
    st.title("Street microclimate")
    st.info("Pick an end date to complete the period.", icon=":material/date_range:")
    st.stop()

start_day, end_day = period
start, end = start_day, end_day + timedelta(days=1)                # end is exclusive
ids = tuple(selected)
df_all = load_measurements(ids, start, end)                         # everything received
df_ok = load_measurements(ids, start, end, usable_only=True)        # reliable wind data only

st.title("Street microclimate")
st.caption(f"{len(selected)} of {len(all_ids)} sensors · {start_day:%d %b %Y} – {end_day:%d %b %Y} · "
           f"latest message {everything['ts'].max():%d %b %Y %H:%M} UTC")

if df_all.empty:
    st.warning("No measurements for this selection and period.", icon=":material/search_off:")
    st.stop()

availability = Analyzer(df_all).availability()
summary = data.sensor_summary(df_ok, df_all, sensors, list(selected), low_wind_ms)
health = data.network_health(everything, sensors, list(selected), availability)
colors = charts.sensor_color_map(all_ids)
hourly_ok = analyse_hourly(df_ok)          # reliable data, hourly: feeds map slider and trend charts

# ---- key indicators
with st.container(horizontal=True):
    if df_ok.empty:
        st.metric("Mean wind speed", "–", border=True)
    else:
        peak = df_ok.loc[df_ok["gust_ms"].idxmax()]
        temp_ok = df_ok[(df_ok["flags"] & int(QualityFlag.TEMP_FAULT)) == 0]["temp_c"]
        st.metric("Mean wind speed", f"{df_ok['mean_speed_ms'].mean():.1f} m/s", border=True,
                  help="Average over all selected sensors and windows, reliable data only.")
        st.metric(f"Strongest gust ({charts.short_id(peak['device_id'])})", f"{peak['gust_ms']:.1f} m/s",
                  border=True, help=f"Measured by {peak['device_id']} on {peak['ts']:%d %b %Y at %H:%M} UTC.")
        st.metric(f"Calm (< {low_wind_ms:g} m/s)", f"{100 * (df_ok['mean_speed_ms'] < low_wind_ms).mean():.0f}% of time",
                  border=True, help="Share of 10-minute windows with mean wind below the calm threshold.")
        st.metric("Mean temperature", f"{temp_ok.mean():.1f} °C" if len(temp_ok) else "–", border=True)
    st.metric("Network availability", f"{100 * availability.mean():.0f}%", border=True,
              help="Messages received / messages expected, averaged over the selected sensors.")

# ---- map + network health
map_col, health_col = st.columns([5, 4])
with map_col, st.container(border=True):
    st.subheader("Sensor map")
    map_view = st.segmented_control("Map view", ["Over time", "Period average"], default="Over time",
                                    key="map_view", label_visibility="collapsed")
    positions = summary[["site", "lat", "lon"]]
    if not summary["lat"].notna().any():
        st.info("The sensors have no position stored yet (sensors table is empty).",
                icon=":material/location_off:")
    elif map_view == "Period average":
        st.caption("Colour = mean wind speed over the period. Arrow = direction the wind blows to.")
        st.plotly_chart(charts.sensor_map(summary, dark=dark_theme()), config={"displayModeBar": False},
                        key="map_avg", alt="Map of the selected sensors, coloured by mean wind speed, "
                                           "with arrows for wind direction")
    else:
        steps, step_h = data.map_steps(hourly_ok)
        if steps.empty:
            st.info("No reliable wind data in this period.", icon=":material/air:")
        else:
            st.caption(f"Drag the slider or press Play. Each step is a {step_h}-hour average. Colour = mean "
                       "speed, arrow = direction the wind blows to, grey = no data.")
            st.plotly_chart(charts.sensor_map_animated(steps, positions, step_h, dark=dark_theme()),
                            config={"displayModeBar": False}, key="map_time",
                            alt="Map of the selected sensors that changes with a time slider: marker colour is "
                                "mean wind speed and arrows show wind direction")

with health_col, st.container(border=True):
    st.subheader("Network health")
    with st.container(horizontal=True):
        st.metric("Online", f"{(health['status'] == 'Online').sum()} / {len(health)}")
        st.metric("Low battery", int(health["low_battery"].sum()))
        st.metric("Calibration due", int(health["calibration_due"].sum()))
    table = health.assign(
        sensor=health["device_id"].map(charts.short_id),
        availability=100 * health["availability"])[
        ["sensor", "status", "last_seen_text", "battery_v", "availability", "calibration"]]
    status_colors = {"Online": "#059669", "Delayed": "#D97706", "Offline": "#DC2626", "No data": "#64748B"}
    styled = (table.style
              .map(lambda v: f"color: {status_colors.get(v, 'inherit')}; font-weight: 600", subset=["status"])
              .map(lambda v: "color: #DC2626; font-weight: 600" if v == "Due" else "", subset=["calibration"]))
    st.dataframe(
        styled, hide_index=True, height="content",
        alt="Network health per sensor: status, last message, battery, availability and calibration",
        column_config={
            "sensor": st.column_config.TextColumn("Sensor", width="small"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "last_seen_text": st.column_config.TextColumn("Last seen", width="small"),
            "battery_v": st.column_config.ProgressColumn(
                "Battery", format="%.2f V", min_value=3.0, max_value=4.2, width="small",
                help=f"Last reported voltage. Low below {SETTINGS.low_battery_v} V."),
            "availability": st.column_config.ProgressColumn(
                "Availability", format="%.0f%%", min_value=0, max_value=100, width="small",
                help="Messages received / expected in the selected period."),
            "calibration": st.column_config.TextColumn(
                "Calibration", width="small",
                help=f"Due when the node reports it, or {SETTINGS.recalibration_days} days after installation."),
        })
    problems = data.attention_items(health)
    if problems:
        st.markdown("\n\n".join(problems))
    else:
        st.markdown(":green[:material/check_circle:] All selected sensors are healthy.")

# ---- time series
with st.container(border=True):
    st.subheader("Time series")
    if resolution == "Hourly":
        lines, flagged = hourly_ok[["device_id", "ts", "mean_speed_ms", "gust_ms", "temp_c"]], {}
        st.caption("Hourly values from reliable data only. Gaps are hours without any.")
    else:
        lines, flagged = data.series_frames(df_all, flagged_mode)
        st.caption({"hide": "Unreliable values are hidden.",
                    "grey": "Unreliable values are shown as grey points.",
                    "show": "All values are shown, including unreliable ones."}[flagged_mode]
                   + " Lines break where messages are missing. Drag to zoom, double-click to reset.")
    st.plotly_chart(charts.timeseries_figure(lines, flagged, colors), key="timeseries",
                    alt="Mean wind speed, gust and temperature over time for each selected sensor")

# ---- mean speed over time
with st.container(border=True):
    st.subheader("Mean wind speed over time")
    view = st.segmented_control("View", ["Daily cycle", "Daily average", "Hour × day"], default="Daily cycle",
                                key="trend_view", label_visibility="collapsed")
    if hourly_ok["mean_speed_ms"].notna().sum() == 0:
        st.info("No reliable wind data in this period.", icon=":material/air:")
    elif view == "Daily average":
        st.caption("Average speed of each day (local time). The dotted line is the mean of all selected sensors.")
        st.plotly_chart(charts.daily_mean_figure(data.daily_mean(hourly_ok), colors), key="daily_mean",
                        alt="Mean wind speed per day for each selected sensor and for the network")
    elif view == "Hour × day":
        st.caption("Network mean speed for every hour of every day: shows when it is windy or calm, "
                   "and how that changes from day to day.")
        st.plotly_chart(charts.hour_by_day_figure(data.hour_by_day(hourly_ok)), key="hour_by_day",
                        alt="Heatmap of network mean wind speed by hour of day and day")
    else:
        st.caption("Average speed at each hour of the day over the whole period (local time): "
                   "the typical daily pattern of each street.")
        st.plotly_chart(charts.daily_cycle_figure(data.daily_cycle(hourly_ok), colors), key="daily_cycle",
                        alt="Mean wind speed by hour of day for each selected sensor")

# ---- wind roses
with st.container(border=True):
    st.subheader("Wind roses")
    st.caption("How often the wind comes from each direction, split by speed. "
               "All roses use the same scale, so they can be compared.")
    analyzer = Analyzer(df_ok)
    roses = {dev: analyzer.wind_rose(dev) for dev in selected if (df_ok["device_id"] == dev).any()}
    if roses:
        titles = {d: f"{charts.short_id(d)} · {sites.get(d, '').split(',')[0]}" for d in roses}
        st.plotly_chart(charts.wind_rose_figure(roses, titles), key="roses",
                        alt="Wind rose of each selected sensor: frequency of wind direction by speed class")
    else:
        st.info("No reliable wind data in this period.", icon=":material/air:")

# ---- sensor comparison + downloads
with st.container(border=True):
    st.subheader("Sensor comparison")
    comp = summary.reset_index().assign(
        sensor=lambda x: x["device_id"].map(charts.short_id) + " · " + x["site"].str.split(",").str[0], low_wind=lambda x: 100 * x["low_wind"],
        availability=lambda x: 100 * x["availability"], usable_share=lambda x: 100 * x["usable_share"])
    st.dataframe(
        comp[["sensor", "mean_speed", "max_gust", "direction", "low_wind", "mean_temp",
              "wind_temp_corr", "availability", "usable_share"]],
        hide_index=True,
        alt="Per-sensor comparison of wind speed, gusts, calm share, temperature, availability and data quality",
        column_config={
            "sensor": st.column_config.TextColumn("Sensor", width=170),
            "mean_speed": st.column_config.NumberColumn("Mean speed", format="%.2f m/s"),
            "max_gust": st.column_config.NumberColumn("Max gust", format="%.1f m/s"),
            "direction": st.column_config.NumberColumn(
                "Prevailing from", format="%.0f°", help="Vector-averaged direction the wind comes from."),
            "low_wind": st.column_config.ProgressColumn(
                f"Calm (< {low_wind_ms:g} m/s)", format="%.0f%%", min_value=0, max_value=100),
            "mean_temp": st.column_config.NumberColumn("Mean temp.", format="%.1f °C"),
            "wind_temp_corr": st.column_config.NumberColumn(
                "Wind–temp. corr.", format="%.2f",
                help="Negative: windier periods are cooler, so ventilation helps."),
            "availability": st.column_config.ProgressColumn(
                "Availability", format="%.0f%%", min_value=0, max_value=100),
            "usable_share": st.column_config.ProgressColumn(
                "Usable data", format="%.0f%%", min_value=0, max_value=100,
                help="Share of received windows without an unreliable-data flag."),
        })

    export_all = df_ok if flagged_mode == "hide" else df_all
    name = f"uwsn_{start_day:%Y%m%d}_{end_day:%Y%m%d}"
    with st.container(horizontal=True):
        st.download_button(
            "Download 10-min data (CSV)", data.export_frame(export_all).to_csv(index=False).encode(),
            file_name=f"{name}_10min.csv", mime="text/csv", icon=":material/download:",
            help="Selected sensors and period. Includes flags; unreliable rows are left out when "
                 "'Flagged data' is set to Hide.")
        hourly_csv = hourly_ok.to_csv(index=False).encode()
        st.download_button("Download hourly data (CSV)", hourly_csv, file_name=f"{name}_hourly.csv",
                           mime="text/csv", icon=":material/download:",
                           help="Hourly mean speed, max gust, vector-mean direction and mean temperature.")
