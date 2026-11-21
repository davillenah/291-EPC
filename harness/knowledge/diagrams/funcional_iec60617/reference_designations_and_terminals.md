# Reference designations (IEC 81346 / IEC 61346) and terminal numbering (IEC 60445, EN 50005, IEC 60947-5-1)

Status tags: `unverified` = from a cited source (secondary articles or manufacturer documents); `typical` = generic practice, no source; `not_found` = not located. Nothing is `verified`.

Note on sources: the terminal and letter rules below come from secondary sources read in this research (industrial and control blogs, and an IEC 81346 summary). The standards themselves (IEC 60445, EN 50005, IEC 60947-5-1, IEC 81346-2) were not read. They appeared only as titles in search results (public catalogue and preview pages); no text was copied.

## 1. Reference designation (IEC 81346-2, the successor to IEC 61346-2)

Reference designations are built from an aspect prefix (function `=`, product `-`, location `+`) plus a class letter and a number, for example `-Q1`, `-KM1`, `-K2`, `-F3`.

| Letter | Class (IEC 81346-2, as summarized) | Examples in this set | Status |
|---|---|---|---|
| Q | Switches or varies energy or signal flow | Power contactors, breakers, motor starters | unverified |
| K | Processes signals or information | Control relays, time relays | unverified |
| F | Direct self-acting protection | Fuses, miniature breakers, thermal overload releases | unverified |
| S | Converts manual operation into a signal | Pushbuttons, selector switches | unverified |
| M | Motor function (suffix in the article, class in typical IEC use) | Motors, drives | typical |
| T | Timing function (suffix in the article: K1T) and transformers | Transformers, CTs | typical (transformer class) |
| G | Generation of energy | Generators | typical |
| H | Signalling | Lamps, horns | typical |
| B | Sensors (level floats) | Float switches | typical |
| X | Terminals | Terminal blocks | typical |
| A | Assemblies and controllers | PLC, soft starter | typical |
| R | Reversing function (suffix in the article: K1R) | Reversing relays | unverified (suffix) |
| C | Converting energy (contactors in North American practice, not in IEC 81346-2) | Contactors (NA) | unverified (NA) |

Numbering practice in the sources:

- Q-series devices are numbered in sequence (Q1, Q2 ...). One example scheme given in the article: breakers Q1 to Q10, power contactors from Q11 onward (typical, not a rule).
- K-series relays are numbered in sequence (K1, K2 ...). The article notes that no universal rule requires K1 to K8 for contactors or K9+ for relays. `typical`.
- Suffixes: function letters after the number (K1T timing, K1R reversing, Q21M motor). Some manufacturers omit the second letter (K1T becomes K1). `unverified` (article).
- North American practice (IEEE 315 style): C for contactors, K for relays, and CR/MR prefixes. `unverified` (article).
- EN 81714 is not covered by the sources read. The relation between EN 81714 and IEC 81346 was not found and is `not_found`.

## 2. Terminal numbering (IEC 60947-5-1 contact marking, IEC 60445 and EN 50005 practice)

### 2.1 Contacts

Each contact has a two-digit number: the first digit is the contact sequence (1, 2, 3 ...), the second digit is the function.

| Second digit | Meaning | Examples | Status |
|---|---|---|---|
| 1 | Common of an NC (break) set | 1, 21 (pair) | unverified |
| 2 | NC (break) output | 2, 22 | unverified |
| 3 | Common of an NO (make) set | 3, 13 | unverified |
| 4 | NO (make) output | 4, 14 | unverified |

Main contacts (power poles): 1/2, 3/4, 5/6 in and out of the pole. Power pole numbering in the sources read was not explicit; the pattern is `typical`.

Auxiliary contacts (examples):

| Terminals | Type | Usage | Status |
|---|---|---|---|
| 13/14 | NO (make) | start / self-holding | unverified (article) |
| 21/22 | NC (break) | interlock / stop | unverified (article) |
| 22/23 | NC (break) | stop contact in some designs | unverified (article) |
| 31/32 | NO (make) | additional NO | unverified (article) |
| 41/42 | NC (break) | additional NC | unverified (article) |
| 95/96 | NC (break) overload trip | in series with control circuit | unverified (article) |
| 97/98 | NO (make) overload alarm | signal | unverified (article) |
| 33/34 | NO (make) additional | alarm/protection (article) | unverified |
| 15/16 and 15/18 | timer contacts | delayed contacts (IEC 60947-5-1 timer series) | typical |

Timed contacts commonly use 15/16 (break) and 15/18 (make). The contact type is marked on the symbol. `typical`.

### 2.2 Coils

- Contactor and relay coils: A1 and A2 (article, unverified).

### 2.3 Relay numbering (control.com summary)

- The first digit identifies the contact set, counting up from 1.
- The second digit identifies the function: 1 common (NC), 2 NC, 3 common (NO), 4 NO.
- Double-throw contacts skip one common: 11 (common), 12 (NC), 14 (NO). `unverified` (source: control.com).
- NEMA numbering is different (1 to 14 on larger units). The source notes EN was not covered. `unverified`.

### 2.4 Panel wire and terminal conventions

| Item | Typical convention | Status |
|---|---|---|
| Terminal strip designation | X1, X2 (X-class); individual terminals 1, 2, 3 ... | typical |
| Power terminals of a motor | U1, V1, W1 (start), U2, V2, W2 (end) | typical |
| Earth conductor | PE | typical |
| Neutral | N | typical |
| Phase conductors | L1, L2, L3 (supply); U, V, W (motor) | typical |
| Wire numbering | sequence starting from the terminal, numbers repeated for the same potential | typical |

Wire numbering and cross-reference rules (sheet number and cross-reference box) follow the drawing standard in use. Not sourced in this research.

## 3. Drawing criteria

| Criterion | Rule used in this set | Status |
|---|---|---|
| Control circuit orientation | Ladder (rungs) top to bottom, supply rails vertical, left to right = sequence | typical |
| Power circuit orientation | Three poles vertical, supply at top, load at bottom | typical |
| Cross reference | Contact of a device shows its designation and the rung/sheet where it is used | typical |
| Interlock | Shown in the other rung as the NC contact of the coil's device | unverified (manufacturer doc, ABB) |
| Symbol orientation | Symbols are drawn vertical or horizontal according to the sheet; keep consistent | typical |

## 4. Not found / open

- Exact text of IEC 60445, EN 50005 and IEC 60947-5-1 was not read. Terminal numbers above are summaries from secondary sources.
- A power-pole numbering table from a manufacturer document was not located; the 1/2, 3/4, 5/6 scheme is `typical`.
- Wire numbering rules from the standards: not located.
- EN 81714 relation to IEC 81346: not located.
