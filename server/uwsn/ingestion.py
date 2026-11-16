"""Talks to The Things Network (TTN) over MQTT: receives uplinks, queues downlinks.

Our sensors talk LoRaWAN to a gateway, the gateway forwards to TTN, and TTN
publishes every uplink as a JSON message on its MQTT broker. This module
subscribes to those messages and turns each one into an `Uplink`.
It also queues downlinks (calibration commands) for a node: send_downlink().

Only this file knows about TTN's JSON format.
"""
import base64
import json
import logging
import ssl
from datetime import datetime, timezone
from typing import Callable, Optional

import paho.mqtt.client as mqtt
import paho.mqtt.publish as mqtt_publish

from .config import SETTINGS
from .models import Uplink

log = logging.getLogger(__name__)


class TTNClient:
    """MQTT client for the TTN application. Calls `on_uplink` for every sensor message."""

    def __init__(self, on_uplink: Callable[[Uplink], None]):
        self._on_uplink = on_uplink
        self._topic = f"v3/{SETTINGS.ttn_app_id}@ttn/devices/+/up"

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.username_pw_set(f"{SETTINGS.ttn_app_id}@ttn", SETTINGS.ttn_api_key)
        self._client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        self._client.reconnect_delay_set(min_delay=1, max_delay=60)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def run(self) -> None:
        """
        Connect (TLS, port 8883) and listen forever (blocking).
        Reconnects automatically if the link drops.
        """
        log.info("Connecting to %s:%d", SETTINGS.ttn_host, SETTINGS.ttn_port)
        self._client.connect(SETTINGS.ttn_host, SETTINGS.ttn_port)
        self._client.loop_forever(retry_first_connection=True)

    def stop(self) -> None:
        """Disconnect; makes run() return."""
        self._client.disconnect()

    # --- MQTT callbacks -----------------------------------------------------

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """
        Subscribes to v3/<app-id>@ttn/devices/+/up.
        Done here so the subscription is renewed after every reconnect.
        Logs an error if TTN refuses the credentials.
        """
        if reason_code.is_failure:
            log.error("TTN refused the connection: %s (check TTN_APP_ID / TTN_API_KEY)", reason_code)
            return
        client.subscribe(self._topic)
        log.info("Connected, subscribed to %s", self._topic)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            log.warning("Lost connection to TTN (%s), reconnecting...", reason_code)

    def _on_message(self, client, userdata, msg):
        """
        Runs for each incoming message.
        Errors are logged and the message skipped, so one bad message never stops the service.
        """
        try:
            uplink = parse_ttn_uplink(msg.payload)
        except Exception:
            log.exception("Could not parse message on %s", msg.topic)
            return
        if uplink is None:
            return
        try:
            self._on_uplink(uplink)
        except Exception:
            log.exception("Error while processing uplink from %s", uplink.device_id)


def parse_ttn_uplink(raw: bytes) -> Optional[Uplink]:
    """Turn a TTN v3 uplink JSON message into an Uplink.
    Returns None for messages without application data (e.g. LoRaWAN MAC-only frames).

    Kept as a plain function so it can be unit-tested without a broker.
    """
    data = json.loads(raw)
    up = data["uplink_message"]
    if "frm_payload" not in up:
        return None

    meta = (up.get("rx_metadata") or [{}])[0]   # we have a single gateway
    return Uplink(
        device_id=data["end_device_ids"]["device_id"],
        received_at=_parse_time(data.get("received_at")),
        payload=base64.b64decode(up["frm_payload"]),
        rssi=meta.get("rssi"),
        snr=meta.get("snr"),
    )


def _parse_time(text: Optional[str]) -> datetime:
    """TTN gives ISO times with nanoseconds ('...:23.123456789Z'); Python only keeps microseconds."""
    if not text:
        return datetime.now(timezone.utc)
    text = text.replace("Z", "+00:00")
    if "." in text:
        main, rest = text.split(".", 1)
        digits = rest[:len(rest) - 6]          # fractional part, without the '+00:00'
        text = f"{main}.{digits[:6].ljust(6, '0')}{rest[-6:]}"
    return datetime.fromisoformat(text)


# --- downlinks ---------------------------------------------------------------

def ttn_downlink_message(payload: bytes, port: int = SETTINGS.downlink_port) -> str:
    """JSON that TTN expects on the .../down/push topic (plain function, testable without a broker)."""
    return json.dumps({"downlinks": [{
        "f_port": port,
        "frm_payload": base64.b64encode(payload).decode("ascii"),
        "priority": "NORMAL",
    }]})


def send_downlink(device_id: str, payload: bytes, port: int = SETTINGS.downlink_port) -> None:
    """Queue a downlink on TTN for one node (opens its own short MQTT connection).

    LoRaWAN class A: the node only listens right after it sends, so it receives this after
    its next uplink, up to one window (10 min) later. "push" adds to the queue; pushing twice
    sends both commands, one per uplink.
    The TTN API key needs the right "Write downlink application traffic".

        from uwsn.calibration import CalibrationManager
        from uwsn.ingestion import send_downlink
        cmd = CalibrationManager().build_downlink(gain=0.92, offset_ms=0.31,
                                                  dir_offset_deg=12.0, temp_offset_c=-0.4)
        send_downlink("uwsn-01", cmd)
    """
    topic = f"v3/{SETTINGS.ttn_app_id}@ttn/devices/{device_id}/down/push"
    mqtt_publish.single(topic, ttn_downlink_message(payload, port), qos=1,
                        hostname=SETTINGS.ttn_host, port=SETTINGS.ttn_port,
                        auth={"username": f"{SETTINGS.ttn_app_id}@ttn", "password": SETTINGS.ttn_api_key},
                        tls={})              # TLS with the system's certificates
    log.info("Downlink queued for %s on port %d: %s", device_id, port, payload.hex())
