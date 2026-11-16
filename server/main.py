"""Entry point of the ingestion service: python main.py"""
import logging
from uwsn.config import SETTINGS
from uwsn.decoder import PayloadDecoder
from uwsn.ingestion import TTNClient
from uwsn.pipeline import Pipeline
from uwsn.storage import Repository
from uwsn.validation import DataValidator

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    pipeline = Pipeline(Repository(SETTINGS.db_path), PayloadDecoder(), DataValidator())
    client = TTNClient(on_uplink=pipeline.handle_uplink)
    try:
        client.run()            # blocks forever, reconnects on its own
    except KeyboardInterrupt:   # Ctrl+C
        client.stop()