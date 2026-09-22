# Salus iT600 for Home Assistant

[![CI](https://github.com/parfienczyk/homeassistant_salus/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/parfienczyk/homeassistant_salus/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/parfienczyk/homeassistant_salus?display_name=tag)](https://github.com/parfienczyk/homeassistant_salus/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.8%2B-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/parfienczyk/homeassistant_salus)](#license)

Lokalna integracja [Home Assistant](https://www.home-assistant.io/) dla urządzeń [Salus iT600](https://salus-controls.com/) przez bramkę UGE600 lub UG800 — termostaty, gniazdka, rolety, czujniki i inne, bez chmury.

This is [`parfienczyk/homeassistant_salus`](https://github.com/parfienczyk/homeassistant_salus), a personal fork of [`Jordi-14/homeassistant_salus`](https://github.com/Jordi-14/homeassistant_salus). Version **0.9.4**, client `salus-it600-client==0.6.1`. UI languages: English, Catalan, and **Polish**. Issues and HACS installs for this copy go here.

## This repository

- Domain stays `salus`. Existing UI config entries (gateway IP + EUID) should survive a folder swap and Home Assistant restart.
- YAML `climate:` / `binary_sensor:` platform config from the 2020 snapshot **no longer works**. Add the integration from **Settings → Devices & Services**.
- Install the inner `custom_components/salus` folder (or HACS). Do **not** clone this whole git repository into `config/custom_components/salus`.
- Protocol code lives in [`salus-it600-client`](https://github.com/Jordi-14/salus-it600-client). Upstream integration development is at [Jordi-14/homeassistant_salus](https://github.com/Jordi-14/homeassistant_salus).

## Features

### Climate

One climate entity per thermostat connected to the gateway. The Home Assistant
controls are adapted to the way each Salus device family models heating,
cooling, schedules, and hold states:

- **Standard heat-only iT600 thermostats and TRVs** — one HVAC mode menu with
  `Off`, `Heat`, and `Auto`. `Heat` maps to manual/permanent hold, `Auto` maps
  to Follow Schedule, and `Off` maps to the Salus off/standby state. These
  devices do not expose a separate preset menu.
- **SQ610 / SQ610RF Quantum thermostats** — separate HVAC and preset controls.
  HVAC modes are `Off` and `Heat`, with `Cool` added only when the gateway shows
  the thermostat supports cooling. Presets are `Permanent Hold`,
  `Follow Schedule`, and `Away`; `Schedule Override` is shown only while the
  thermostat is actively overriding the Salus schedule. Schedule is not exposed
  as HVAC `Auto` for SQ610, and standby is represented by HVAC `Off`, not by a
  separate preset.
- **FC600 fan-coil controllers** — separate HVAC, preset, and fan controls.
  HVAC modes are `Off`, `Heat`, and `Cool`; schedule is handled through presets,
  not HVAC `Auto`. Presets are `Follow Schedule`, `Permanent Hold`, and `Eco`
  when the device reports Eco support; `Schedule Override` is shown only while
  active. Fan modes are `auto`, `high`, `medium`, `low`, and `off`.

### Sensors

| Sensor | Description |
|---|---|
| **Temperature** | Current temperature reading (°C) |
| **Humidity** | Relative humidity (%) |
| **Battery** | Battery level for wireless thermostats and standalone sensors (%) |
| **Power** | Instantaneous power draw from smart plugs (W) |
| **Energy** | Cumulative energy consumption from smart plugs (kWh) |

### Binary sensors

| Binary sensor | Description |
|---|---|
| **Window / Door** | Open/closed state (SW600, OS600) |
| **Water leak** | Moisture detection (WLS600) |
| **Smoke** | Smoke alarm (SmokeSensor-EM) |
| **Low battery** | Battery warning for wireless sensors and TRVs (it600MINITRV via TRVError22) |
| **Thermostat problem** | Aggregated thermostat error flags with human-readable descriptions as attributes |
| **Battery problem** | Battery-specific thermostat error indicator |

### Covers

One cover entity per RS600 roller shutter or blind. Supports **open**, **close**, and **set position** (0-100 %).

### Switches

One switch entity per smart plug or relay (SP600, SPE600, SR600, and RS600 relay endpoints). Supports **on/off** control. Double-switch devices are exposed as separate entities.

### Locks

One lock entity per thermostat that supports child lock. Allows **locking/unlocking** the thermostat keypad.

## Installation

Minimum Home Assistant version: **2024.8.0**. Integration version: **0.9.4**.

### HACS (recommended)

1. Open HACS in your Home Assistant instance.
2. Go to **Integrations** → **⋮** → **Custom repositories**.
3. Add `https://github.com/parfienczyk/homeassistant_salus` as an **Integration**.
4. Search for **Salus iT600** and install it.
5. Restart Home Assistant.

If you previously used `konradb3/homeassistant_salus`, `epoplavskis/homeassistant_salus`, or `Jordi-14/homeassistant_salus` in HACS, remove that custom repository first, then add this one. See [docs/migration-from-older-forks.md](docs/migration-from-older-forks.md).

### Manual

1. Copy **only** `custom_components/salus` from this repository into Home Assistant `config/custom_components/salus`.
2. Restart Home Assistant.

The result must look like `config/custom_components/salus/manifest.json`, not `config/custom_components/salus/custom_components/salus/manifest.json`.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **Salus iT600**.
3. Enter your gateway's **IP address** and **EUID**.
4. The integration will discover all devices on the gateway and create entities automatically.

### Finding the EUID

The EUID is a 16-character hexadecimal string printed on the bottom of the gateway, under the micro-USB port. For example: `001E5E0D32906128`.

If the printed EUID does not work, try `0000000000000000` — some gateways accept a zeroed EUID instead of the physical one.

### Data updates

This is a local polling integration. Gateway data is refreshed every 20 seconds by default through one shared coordinator, then reused by all entity platforms. The regular poll interval is configurable in integration options.

After a Home Assistant command (e.g. changing a thermostat target temperature or turning on a switch), the integration requests one verification refresh after 5 s by default. This delay is configurable in integration options.

## Supported devices

For detailed support status, entity coverage, and known limitations, see
[docs/supported-devices.md](docs/supported-devices.md).

| Category | Devices |
|---|---|
| **Climate** | HTRP-RF(50), TS600, VS10WRF/VS10BRF, VS20WRF/VS20BRF, SQ610, SQ610RF, FC600, TRV3RF, it600MINITRV |
| **Binary sensors** | SW600, WLS600, OS600, SD600, TRV10RFM, RX10RF, SmokeSensor-EM |
| **Temperature sensors** | PS600 |
| **Switches** | SP600, SPE600, SR600, RS600 relay endpoints |
| **Covers** | RS600 |
| **Locks** | Any thermostat with child-lock support |

Known unsupported: SB600, CSB600 (button actions only work through the Salus Smart Home app).

### RS600 and SR600 notes

RS600 is a multifunction device. A shutter installation may expose one `cover`
entity, while relay endpoint payloads may also expose one or two `switch`
entities. These entities are grouped under the same Home Assistant device when
the gateway reports the same Salus `UniID`.

Use the `cover` entity for shutters or blinds. Use the `switch` entities for
independent relay channels. Disable the unused representation in Home Assistant
to avoid confusing automations, and do not assume the cover and switch entities
control independent hardware outputs.

SR600 is treated as a dry relay switch, not as a cover device.

### SQ610 notes

The SQ610 Quantum thermostat has additional handling:

- Separate HVAC and preset controls instead of collapsing schedule into HVAC `Auto`
- `Cool` mode exposure only when the gateway reports cooling support
- Direct standby handling via `HoldType`, exposed as HVAC `Off`
- Simplified preset controls: `Permanent Hold`, `Follow Schedule`, and `Away`
- `Schedule Override` exposed only as a reported active state
- Humidity exposed through the normalized client model
- Floor temperature from external probe (`OUTSensorProbe`)

Selecting **Follow Schedule** returns the thermostat to the schedule configured in the Salus Smart Home app.

## Troubleshooting

- If the gateway IP or EUID changes, use **Reconfigure** from the integration entry menu — no need to delete and recreate.
- Make sure **Local WiFi Mode** is enabled on your gateway:
  1. Open the Salus Smart Home app on your phone and sign in.
  2. Double-tap your gateway to open the info screen.
  3. Press the gear icon to enter configuration.
  4. Scroll down and check that **Disable Local WiFi Mode** is set to **No**.
  5. Scroll to the bottom, save settings, and restart the gateway by unplugging/plugging USB power.
- If polling fails repeatedly, Home Assistant creates a **Repairs** issue linking back to this section. The repair clears automatically after the gateway responds successfully again.

### Debugging

If you're having issues with the integration, there are two ways to enable debug logging.

**Option 1 — YAML configuration**

Add the following to your `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  default: info
  logs:
    custom_components.salus: debug
```

**Option 2 — Home Assistant UI**

1. Go to **Settings** → **Devices & Services**.
2. Find the **Salus iT600** integration and click the **⋮** menu.
3. Select **Enable debug logging**.
4. Reproduce the issue.
5. Click **Disable debug logging** — the browser will download a log file you can inspect or attach to a bug report.

This method is useful for one-off troubleshooting since it automatically reverts to the normal log level once you stop it.

### Diagnostics

1. Open **Settings** → **Devices & Services**.
2. Select the **Salus iT600** integration.
3. Open the three-dot menu → **Download diagnostics**.

Diagnostics include integration version, gateway health counters, device counts,
availability history, and shared climate diagnostics with normalized fields plus
whitelisted support fields for each thermostat. The gateway token is redacted
automatically.

Review the file before posting publicly — it may still contain your gateway IP,
device IDs, and the gateway unique id.

For support requests, include:

- Home Assistant version
- `homeassistant_salus` version
- `salus-it600-client` version (from `custom_components/salus/manifest.json`)
- Gateway model (UGE600 or UG800) if known
- Whether the gateway uses legacy or newer firmware if known
- Diagnostics file or the relevant redacted snippets
- Home Assistant logs around startup, reload, polling, or the failed command

## Encryption & protocol support

Salus gateways encrypt all local API traffic. Different gateway models and firmware versions use different encryption protocols. The integration **auto-detects** the correct protocol by trying each one in order during connection.

| | Legacy AES-CBC | AES-CCM (newer firmware) |
|---|---|---|
| **Gateways** | UGE600, older UG800 firmware | UG800 with newer firmware |
| **Cipher** | AES-256-CBC (fallback: AES-128-CBC) | AES-256-CCM (authenticated encryption) |
| **Key derivation** | `MD5("Salus-{euid}")` — static, derived from the gateway EUID | EUID bytes + hardcoded suffix — 32-byte key derived from the gateway EUID |
| **IV / nonce** | Fixed 16-byte IV | 8-byte random nonce (3 random + 2-byte counter + 3-byte timestamp) |
| **Authentication** | None | 8-byte MAC tag (CBC-MAC) |
| **Padding** | PKCS7 | None (CCM handles arbitrary lengths) |
| **Wire format** | Block-aligned encrypted HTTP body | `[ciphertext + 8-byte MAC][8-byte nonce]` |

Protocol auto-detection order:
1. **AES-256-CBC** — legacy iT600 / UGE600 gateways
2. **AES-128-CBC** — intermediate firmware variant
3. **AES-CCM** — newer UG800 firmware

A rejected attempt is identified by a characteristic 33-byte reject frame (trailer byte `0xAE`).

For full protocol implementation details, see the [`salus-it600-client`](https://github.com/Jordi-14/salus-it600-client) library documentation.

## Development and testing

See [CONTRIBUTING.md](CONTRIBUTING.md) for architecture, testing, and platform development details.

Release publishing is documented in [RELEASE.md](RELEASE.md).

## Migration from the 2020 snapshot / `pyit600`

This integration uses `salus-it600-client==0.6.1`, a maintained successor of `pyit600`. The Home Assistant domain is still `salus`.

If you are upgrading from this repository's 2020 layout (Python files in the repo root, `pyit600==0.1.3`, YAML platforms):

1. Remove YAML `climate:` / `binary_sensor:` `platform: salus` blocks.
2. Replace `config/custom_components/salus` with the inner `custom_components/salus` folder from this tree.
3. Restart Home Assistant. Add **Salus iT600** from the UI if it was YAML-only before.

If you are moving from another HACS fork, see
[docs/migration-from-older-forks.md](docs/migration-from-older-forks.md).

## Project origin

This repository is a fork of [`Jordi-14/homeassistant_salus`](https://github.com/Jordi-14/homeassistant_salus), which is a fork of [`epoplavskis/homeassistant_salus`](https://github.com/epoplavskis/homeassistant_salus), originally from [`konradb3/homeassistant_salus`](https://github.com/konradb3/homeassistant_salus).

It incorporates and reworks feature ideas from Leonard Pitzu's [`leonardpitzu/homeassistant_salus`](https://github.com/leonardpitzu/homeassistant_salus) fork, including broader device coverage, UG800/new-firmware support, TRV-related entities, SQ610 improvements, smart-plug metering, and thermostat lock support.

Protocol and parsing logic lives in the reusable [`salus-it600-client`](https://github.com/Jordi-14/salus-it600-client) library. This repository exposes those capabilities through Home Assistant entities, diagnostics, options, repairs, and translations.

## License

Licensed under either the Apache License, Version 2.0
([LICENSE-APACHE](LICENSE-APACHE)) or the MIT License
([LICENSE-MIT](LICENSE-MIT)), at your option. See [NOTICE](NOTICE) for
attribution details.
