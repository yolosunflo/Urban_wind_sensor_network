"""Output in a clean, shareable form (the final goal of the project)."""
import pandas as pd


class DataExporter:
    def to_csv(self, df: pd.DataFrame, path: str) -> None:
        df.to_csv(path, index=False)

    def to_geojson(self, measurements: pd.DataFrame, sensors: pd.DataFrame, path: str) -> None:
        """One point per sensor with its latest/aggregated values (for GIS tools)."""
        raise NotImplementedError

    def to_report(self, df: pd.DataFrame, path: str) -> None:
        """TODO: summary report for municipalities (period, coverage, key stats)."""
        raise NotImplementedError
