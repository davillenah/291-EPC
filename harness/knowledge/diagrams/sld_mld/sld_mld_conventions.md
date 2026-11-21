# SLD and MLD: definitions, minimum content and drawing conventions

Research for the harness SLD/MLD generator. Facts only, sourced on 2026-11-20. No PDF or protected text is stored; short citations and URLs only.

Status vocabulary: `unverified` = sourced, not checked by a person; `typical` = generic industry practice without a source; `not_found` = not found in sources, never guessed; `pending review` = value quoted from a norm, waits for a person. Nothing is `verified`.

Machine-readable data: `devices/*.json` (43 devices), `schemes/*.json` (9 typical schemes), `decision_rules.json` (24 rules). Schemas in `schema/`.

## 1. What each diagram is

| Diagram | Meaning | Lines drawn | Typical use |
|---|---|---|---|
| SLD (single-line diagram, unifilar) | One line stands for all phases. Shows the power path: source, protection, switching, transformers, boards, loads | Single line with device symbols and rating labels | Power distribution overview, MV and LV |
| MLD (multi-line diagram, multifilar) | Each phase and neutral/earth drawn separately | Three phase lines (plus N and PE where used) | Detail of a connection, starter, transfer, control wiring, phase-sensitive items |

Source: the SLD definition and typical content are summarised in the cited wiki and vendor guide (`viox_sld`, unverified). The MLD definition is `typical` (generic industry practice); no fetched source defined it in this run. IEC 61082-1 is the cited standard for drawing rules; its text was not fetched, so its rules are not quoted here.

## 2. Minimum content of an SLD

Sourced from the guide `viox_sld` (unverified):

1. Source (utility, generator, UPS, inverter, tie) at the top.
2. Upstream protective device and MV/LV transformer (kVA, voltage ratio, vector group, impedance, earthing, tap).
3. Main breaker or switching device, and the main bus (may be split into sections).
4. Outgoing feeders with their protective devices, down to panels, MCCs, motors and loads.
5. Bus ties or transfer paths, normally open (N.O.) where applicable.

Data labels on each element (from the same guide):

| Element | Labels |
|---|---|
| Transformer | kVA, voltage ratio, phases and frequency, winding connection, % impedance, earthing, tap |
| Bus | nominal voltage, continuous current, withstand or short-circuit rating if stated |
| Breaker | frame and trip rating (e.g. "800 AF / 630 AT"), breaking capacity (Icu). Trip settings are often not shown |
| Fuse | role (overcurrent); no specific label set in the source |
| CT | primary-to-secondary ratio |
| Feeder | conductor count, size, material where notated |
| Motor or load | power rating |
| Switch | normal position (N.O. / N.C.) |

Items not sourced and therefore `typical` for the harness: cable section and length per feeder, earth-leakage setting, cable installation method, and the board schedule (circuit list). Cable sizing is a calculation (AEA 90364 / IEC 60364 workflow) and is not covered by this research.

## 3. Naming and tags

- Each device carries a tag that links to its schedule, nameplate and settings. Examples from the guide: `QF-101`, `52-MAIN`, `T1`, `MDB-1` (`viox_sld`, unverified). The tag format is a project choice; the harness must keep one tag per device.
- Record each feeder tag with its destination.
- If a bus section has no identifier, assign a temporary one.
- Check that drawing tags match field labels before relying on the SLD (`viox_sld`).
- ANSI/IEEE function numbers (for example 50, 51, 52, 27, 59) identify protective functions. The project legend controls their meaning (`viox_sld`, `control_ansi`).

## 4. Drawing conventions (typical)

| Convention | Status | Source |
|---|---|---|
| Flow from source at top to loads at bottom | unverified | `viox_sld` |
| Upstream to downstream reading order | unverified | `viox_sld` |
| Show N.O./N.C. state of switches | unverified | `viox_sld` |
| Show CT ratio beside the metering point | typical | generic practice |
| Show interlocks between disconnector and earthing switch on MV cells | typical | generic practice; SafeRing/SafePlus functions list the disconnector with earthing switch (`abb_safering_doc`) |
| Show busbar voltage and current rating | unverified | `viox_sld` |
| Symbols per IEC 60617 | not_found for identifiers | the public IEC 60617 page (`iec60617_db`) lists no identifiers; the database itself needs a subscription (about 1,900 symbols). Symbol work is covered by another agent |

## 5. Sheet and title block

The harness uses the IRAM title block and the nomenclature of the project. This research did not fetch IRAM or IEC 61082 text, so no title block rules are stated here.

## 6. What this research did not cover

- The IEC 61082-1 document rules (text not fetched in this run).
- Electrical-installation.org pages on single-line diagrams, ATS and coordination returned server errors in this run. Their content is not used.

## 7. Sources

- `viox_sld`: How to read a single line diagram, https://viox.com/how-to-read-a-single-line-diagram/ (third-party guide)
- `iec60617_db`: IEC 60617 database, https://std.iec.ch/iec60617 (public summary)
- `control_ansi`: ANSI/IEEE Function Number Codes, https://control.com/textbook/electric-power-measurement-and-control/ansiieee-function-number-codes/
- `abb_safering_cat`: 1VDD006104 SafeRing SafePlus 12-24 kV catalogue, https://library.e.abb.com/public/bb38f74c9b404b4b89745cde2a4b0dba/1VDD006104_Catalogue_SR-SP_12-24kV_EN_07-2022.pdf
- `abb_safering_doc`: SafeRing SafePlus product documentation, https://library.e.abb.com/public/207cafdaa3d4bfc2482578070000fce2/12-24kV_SafeRing_SafePlus_EN.pdf
