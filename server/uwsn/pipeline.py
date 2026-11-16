"""Whole process: uplink -> decode -> validate -> store."""
import logging
from .decoder import PayloadDecoder
from .models import Uplink
from .storage import Repository
from .validation import DataValidator

log = logging.getLogger(__name__)


class Pipeline:
    """
    Called for every message: save the raw message, decode it, validate it, save the result. 
    A malformed message is logged and skipped instead of crashing the program.
    """
    def __init__(self, repo: Repository, decoder: PayloadDecoder, validator: DataValidator):
        self.repo, self.decoder, self.validator = repo, decoder, validator

    def handle_uplink(self, up: Uplink) -> None:
        self.repo.save_uplink(up)                  # always keep the raw message
        try:
            m = self.decoder.decode(up)
        except ValueError as e:
            log.warning("bad payload from %s: %s", up.device_id, e)
            return
        self.repo.save_measurement(self.validator.validate(m))
