"""Analysis on stored data (pandas). Input = DataFrame from Repository.load_measurements()."""
import numpy as np
import pandas as pd


def vector_mean_direction(speed: pd.Series, direction_deg: pd.Series) -> float:
    """Mean wind direction (degrees, 0-360, direction the wind comes FROM) of a group of windows.

    Averages the speed-weighted sin/cos components, not the angles: the mean of 359 and 1
    degrees is 0, not 180. Returns NaN if there is no data or the winds cancel out exactly."""
    x, y = wind_components(speed, direction_deg)
    return compass_angle(x.mean(), y.mean())


def wind_components(speed, direction_deg):
    rad = np.deg2rad(direction_deg)
    return speed * np.sin(rad), speed * np.cos(rad)


def compass_angle(x, y):
    """Compass angle of the vector (x = east part, y = north part). Works on scalars and arrays."""
    ang = np.rad2deg(np.arctan2(x, y)) % 360
    return np.where(np.hypot(x, y) < 1e-9, np.nan, ang)[()]


class Analyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def usable(self) -> pd.DataFrame:
        bad_mask = 0b1000100111      # SPIKE|OUT_OF_RANGE|STUCK|SENSOR_FAULT|DRIFT
        return self.df[(self.df["flags"] & bad_mask) == 0]

    def hourly(self) -> pd.DataFrame:
        """Mean speed, max gust, vector-mean direction per sensor per hour.
        Hours without usable data stay in the table as NaN rows (so charts show the gap)."""
        cols = ["device_id", "ts", "mean_speed_ms", "gust_ms", "mean_dir_deg", "temp_c"]
        d = self.usable()
        if d.empty:
            return pd.DataFrame(columns=cols)
        d = d.copy()
        d.loc[(d["flags"] & 128) != 0, "temp_c"] = np.nan      # ignore faulty temperatures
        d["_x"], d["_y"] = wind_components(d["mean_speed_ms"], d["mean_dir_deg"])
        g = d.set_index("ts").groupby("device_id").resample("1h")
        out = g.agg(mean_speed_ms=("mean_speed_ms", "mean"), gust_ms=("gust_ms", "max"),
                    temp_c=("temp_c", "mean"), _x=("_x", "mean"), _y=("_y", "mean"))
        out["mean_dir_deg"] = compass_angle(out.pop("_x"), out.pop("_y"))
        return out.reset_index()[cols]

    def wind_rose(self, device_id: str, n_sectors: int = 16,
                  speed_bins: tuple = (0, 1, 2, 4, 6, np.inf)) -> pd.DataFrame:
        """Frequency per direction sector and speed class, from usable data.

        One row per (sector, speed class), zeros included, so the table is always complete:
          sector_deg   centre of the sector (0 = north, sectors are centred on the compass points)
          speed_class  label such as "1-2 m/s" (ordered categorical, calm to strong)
          count        number of 10-min windows
          frequency    share of all windows of this sensor, in percent (sums to 100)
        """
        d = self.usable()
        d = d[d["device_id"] == device_id]
        width = 360 / n_sectors
        labels = [f"{lo:g}-{hi:g} m/s" if np.isfinite(hi) else f">{lo:g} m/s"
                  for lo, hi in zip(speed_bins[:-1], speed_bins[1:])]
        sector = np.floor(((d["mean_dir_deg"] + width / 2) % 360) / width).astype(int) % n_sectors
        speed_class = pd.cut(d["mean_speed_ms"], bins=list(speed_bins), labels=labels, right=False)
        counts = (pd.DataFrame({"sector": sector, "speed_class": speed_class})
                  .groupby(["sector", "speed_class"], observed=False).size()
                  .reindex(pd.MultiIndex.from_product([range(n_sectors), speed_class.cat.categories],
                                                      names=["sector", "speed_class"]), fill_value=0)
                  .rename("count").reset_index())
        counts["speed_class"] = pd.Categorical(counts["speed_class"], categories=labels, ordered=True)
        counts["sector_deg"] = counts["sector"] * width
        counts["frequency"] = 100 * counts["count"] / max(len(d), 1)
        return counts[["sector_deg", "speed_class", "count", "frequency"]]

    def low_wind_fraction(self, threshold_ms: float = 1.0) -> pd.DataFrame:
        """Share of time below threshold per sensor: key indicator of poor ventilation."""
        d = self.usable()
        return d.groupby("device_id")["mean_speed_ms"].apply(lambda s: (s < threshold_ms).mean())

    def wind_temperature_correlation(self) -> pd.Series:
        """Correlation between wind speed and the node's own temperature, per sensor.
        A negative value suggests wind brings cooler air (ventilation helps)."""
        d = self.usable()
        d = d[(d["flags"] & 128) == 0].dropna(subset=["temp_c"])
        return d.groupby("device_id").apply(lambda g: g["mean_speed_ms"].corr(g["temp_c"]))

    def compare_with_temperature(self, temp_df: pd.DataFrame) -> pd.DataFrame:
        """TODO: join with urban temperature data, correlate wind vs temperature by street."""
        raise NotImplementedError

    def availability(self, window_s: int = 600) -> pd.Series:
        """Received / expected windows per sensor (network health), between 0 and 1.

        Expected windows run from the sensor's first message to the LAST message of any sensor
        in the data, so a node that stopped sending loses availability instead of looking
        perfect. All received rows count, flagged or not: this measures radio reception."""
        if self.df.empty:
            return pd.Series(dtype=float, name="availability")
        last = self.df["ts"].max()
        g = self.df.groupby("device_id")["ts"]
        expected = ((last - g.min()).dt.total_seconds() // window_s) + 1
        return (g.count() / expected).clip(upper=1.0).rename("availability")
