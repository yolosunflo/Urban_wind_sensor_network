"""Analysis on stored data (pandas). Input = DataFrame from Repository.load_measurements()."""
import numpy as np
import pandas as pd


class Analyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def usable(self) -> pd.DataFrame:
        bad_mask = 0b1000100111      # OUT_OF_RANGE|STUCK|SENSOR_FAULT|DRIFT (adapt to QualityFlag)
        return self.df[(self.df["flags"] & bad_mask) == 0]

    def hourly(self) -> pd.DataFrame:
        """Mean speed, max gust, vector-mean direction per sensor per hour."""
        d = self.usable().set_index("ts")
        g = d.groupby("device_id").resample("1h")
        out = g.agg(mean_speed_ms=("mean_speed_ms", "mean"), gust_ms=("gust_ms", "max"))
        # TODO: direction via vector average (sin/cos), not arithmetic mean
        return out.reset_index()

    def wind_rose(self, device_id: str, n_sectors: int = 16) -> pd.DataFrame:
        """Frequency per direction sector and speed class."""
        raise NotImplementedError

    def low_wind_fraction(self, threshold_ms: float = 1.0) -> pd.DataFrame:
        """Share of time below threshold per sensor: key indicator of poor ventilation."""
        d = self.usable()
        return d.groupby("device_id")["mean_speed_ms"].apply(lambda s: (s < threshold_ms).mean())

    def compare_with_temperature(self, temp_df: pd.DataFrame) -> pd.DataFrame:
        """TODO: join with urban temperature data, correlate wind vs temperature by street."""
        raise NotImplementedError

    def availability(self, window_s: int = 600) -> pd.Series:
        """Received / expected windows per sensor (network health)."""
        raise NotImplementedError
