"""Receives uplinks from the network server. Only this file knows about TTN.
To switch to another network (LTE-M, mesh gateway), implement a new Ingestor."""
import base64
import json
import ssl
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Callable

import paho.mqtt.client as mqtt

from .config import SETTINGS
from .models import Uplink


class Ingestor(ABC):
    @abstractmethod
    def start(self, on_uplink: Callable[[Uplink], None]) -> None: ...
    @abstractmethod
    def stop(self) -> None: ...


class TTNMqttIngestor(Ingestor):
    def __init__(self):
        self._client = mqtt.Client()
        self._client.username_pw_set(f"{SETTINGS.ttn_app_id}@ttn", SETTINGS.ttn_api_key)
        self._client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        self._callback = None

    def start(self, on_uplink):
        self._callback = on_uplink
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.connect(SETTINGS.ttn_host, SETTINGS.ttn_port)
        self._client.loop_forever()      # TODO: run in a thread / reconnect logic

    def stop(self):
        self._client.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        client.subscribe(f"v3/{SETTINGS.ttn_app_id}@ttn/devices/+/up")

    def _on_message(self, client, userdata, msg):
        data = json.loads(msg.payload)
        up = data["uplink_message"]
        meta = (up.get("rx_metadata") or [{}])[0]
        self._callback(Uplink(
            device_id=data["end_device_ids"]["device_id"],
            received_at=datetime.now(timezone.utc),
            payload=base64.b64decode(up["frm_payload"]),
            rssi=meta.get("rssi"),
            snr=meta.get("snr"),
        ))
