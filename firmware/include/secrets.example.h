#pragma once
// Copy this file to secrets.h and fill it from the TTN console (End device -> Overview).
// secrets.h is in .gitignore: never commit real keys.
#include <stdint.h>

static const uint64_t JOIN_EUI = 0x0000000000000000;   // also called AppEUI
static const uint64_t DEV_EUI  = 0x0000000000000000;   // MSB first, as shown in the console
static const uint8_t  APP_KEY[] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
static const uint8_t  NWK_KEY[] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,   // LoRaWAN 1.0.x:
                                    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };  // same as APP_KEY
