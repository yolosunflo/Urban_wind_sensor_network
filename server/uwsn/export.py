"""Output in a clean, shareable form (the final goal of the project)."""
import pandas as pd
from typing import Optional
from .models import UNUSABLE_WIND_MASK, flag_text

class DataExporter:
    @staticmethod
    def prepare(df: pd.DataFrame) -> pd.DataFrame:
        """Measurements with readable columns added."""
        out = df.copy()
        out["usable"] = (out["flags"] & UNUSABLE_WIND_MASK) == 0
        out["flags_text"] = out["flags"].map(flag_text)
        out["ts"] = out["ts"].map(lambda t: t.isoformat())
        return out

    def csv_text(self, df: pd.DataFrame) -> str:
        """CSV as text (for st.download_button)."""
        return self.prepare(df).to_csv(index=False)

    def save_csv(self, df: pd.DataFrame, path: str) -> None:
        """Write the CSV to a file (overwritten if it exists)."""
        self.prepare(df).to_csv(path, index=False)