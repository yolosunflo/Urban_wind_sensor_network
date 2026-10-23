"""Entry point of the ingestion service: python main.py"""
import logging
from uwsn.config import SETTINGS
from uwsn.decoder import PayloadDecoder
from uwsn.ingestion import TTNMqttIngestor
from uwsn.pipeline import Pipeline
from uwsn.storage import Repository
from uwsn.validation import DataValidator

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    pipeline = Pipeline(Repository(SETTINGS.db_path), PayloadDecoder(), DataValidator())
    TTNMqttIngestor().start(pipeline.handle_uplink)
