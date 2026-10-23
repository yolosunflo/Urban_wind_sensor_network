"""Bytes -> Measurement. Mirror of firmware/src/PayloadCodec.cpp (see docs/payload_format.md)."""
import struct
from .config import SETTINGS as S
from .models import Uplink, Measurement, QualityFlag

_FMT = ">BHHHHBhBB"          # 14 bytes, big-endian
_SIZE = struct.calcsize(_FMT)
_TEMP_NA = -32768


class PayloadDecoder:
    SUPPORTED_VERSIONS = {1}

    def decode(self, up: Uplink) -> Measurement:
        if len(up.payload) < _SIZE:
            raise ValueError(f"payload too short: {len(up.payload)} bytes")
        (ver, seq, mean, gust, direction,
         std, temp, batt, flags) = struct.unpack(_FMT, up.payload[:_SIZE])
        if ver not in self.SUPPORTED_VERSIONS:
            raise ValueError(f"unsupported payload version {ver}")
        return Measurement(
            device_id=up.device_id,
            ts=up.received_at,       # TODO: subtract airtime/window offset if needed
            seq=seq,
            mean_speed_ms=mean * S.speed_lsb_ms,
            gust_ms=gust * S.speed_lsb_ms,
            mean_dir_deg=direction * S.dir_lsb_deg,
            std_speed_ms=std * S.std_lsb_ms,
            temp_c=None if temp == _TEMP_NA else temp * S.temp_lsb_c,
            battery_v=S.battery_offset_v + batt * S.battery_lsb_v,
            flags=QualityFlag(flags),
        )
