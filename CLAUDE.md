# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for GoCoax MoCA (Multimedia over Coax) adapters. It polls GoCoax/MaxLinear-based MoCA devices via HTTP, parses raw hex/binary responses, and exposes network diagnostic data as Home Assistant sensors.

## Development

There is no build system. The integration is pure Python and runs inside Home Assistant. There are no tests, no linting config, and no CI/CD.

**To test changes**, copy `custom_components/gocoax/` into a Home Assistant instance's `config/custom_components/` directory and restart HA (or reload the integration).

**To validate Python syntax locally:**
```bash
python3 -m py_compile custom_components/gocoax/*.py
```

**Minimum Home Assistant version:** 2023.2.0 (current code targets 2025.6+).

## Architecture

All integration code lives in `custom_components/gocoax/`:

- **`gocoax_api.py`** — Core API client. Handles HTTP auth (Basic or Digest), POSTs to 13 device endpoints, and parses raw hex/binary responses into human-readable values. Key methods: `validate_connection()`, `retrieve_device_info()`, `display_device_info()`, `get_phy_rates()`. SSL verification is intentionally disabled for local device access.

- **`sensor.py`** — Three entity classes and a coordinator:
  - `GoCoaxCoordinator` (DataUpdateCoordinator): fetches data every 60 seconds
  - `GoCoaxSensor`: static sensors defined in `MAIN_SENSORS` (SoC version, MAC, IP, link status, LOF, Ethernet counters)
  - `GoCoaxPhyRateSensor`: dynamically created per discovered node pair (PHY rate node X → node Y)
  - `GoCoaxPhyGcdRateSensor`: dynamically created per discovered node (GCD rate)

- **`config_flow.py`** — Single-step UI config flow collecting host, username, password. Validates connection before creating the config entry; uses host as unique_id to prevent duplicates.

- **`__init__.py`** — Lifecycle hooks (`async_setup_entry`, `async_unload_entry`). Forwards setup to the sensor platform using `async_forward_entry_setups` (HA 2025.6+ API).

- **`const.py`** — Domain name (`"gocoax"`), config key constants, default poll interval (60s).

- **`translations/en.json`** — UI strings for the config flow.

## Key Implementation Details

**Node discovery**: Up to 16 MoCA nodes are discovered dynamically at runtime via bitmask parsing. PHY rate sensors are created for all discovered node pairs — the sensor count scales with network size.

**PHY rate calculation**: Handles both MoCA 1.x and 2.x with different bandwidth handling (50 MHz vs 100 MHz). See `get_phy_rates()` in `gocoax_api.py`.

**Data format**: Device endpoints return raw hex-encoded binary data. `hex2mac()` and `byte2ascii()` helpers convert these to usable values.

**HA coordinator pattern**: All sensors share one `GoCoaxCoordinator` instance per config entry, so data is fetched once per poll interval regardless of sensor count.
