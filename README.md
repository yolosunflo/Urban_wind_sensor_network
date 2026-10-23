# Urban Wind Sensor Network: code skeleton

- `firmware/`: C++ (PlatformIO/Arduino-style) running on each sensor node
- `server/`: Python backend (ingestion, validation, storage, analysis, dashboard)
- `docs/payload_format.md`: contract between the two

Data flow:
anemometer (analog) -> ADC -> Calibration -> Aggregator (10 min) -> PayloadCodec
-> LoRa -> gateway -> TTN -> Ingestor -> Decoder -> Validator -> Repository -> Analyzer -> Dashboard / Export

All files contain TODOs where real hardware or decisions are needed.

For more detailed explanation on functions and class see the document `docs/code_documentation`