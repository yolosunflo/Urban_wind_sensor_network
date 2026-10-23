#include "Transport.h"

namespace uwsn {
// TODO: implement with RadioLib (or MCCI LMIC). Keep the keys in a separate
// secrets.h that is NOT committed to git.
bool LoRaWANTransport::begin() { return false; }
bool LoRaWANTransport::send(const uint8_t*, size_t) { return false; }
bool LoRaWANTransport::pollDownlink(uint8_t*, size_t& n) { n = 0; return false; }
void LoRaWANTransport::sleep() {}
}  // namespace uwsn
