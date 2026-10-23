"""Run with: streamlit run uwsn/dashboard/app.py"""
import streamlit as st
from uwsn.config import SETTINGS
from uwsn.storage import Repository
from uwsn.analysis import Analyzer

st.set_page_config(page_title="Urban Wind Sensor Network", layout="wide")
st.title("Street Microclimate Dashboard")

repo = Repository(SETTINGS.db_path)
df = repo.load_measurements()
sensors = repo.load_sensors()

# TODO: sidebar filters (sensors, date range, show only usable data)
# TODO: map with one marker per sensor (colour = mean speed, arrow = direction)
# TODO: time series of speed / gust per sensor
# TODO: wind rose, low-wind fraction per street
# TODO: network health panel (battery, last seen, availability, calibration due)
# TODO: CSV download button

if df.empty:
    st.info("No data yet.")
else:
    st.dataframe(Analyzer(df).hourly())
