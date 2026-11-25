# epc_titleblock (door)

The IRAM A0-A4 sheets and custom title blocks live in `epc_draw.titleblock` since ADR-0042. This package only keeps the old names: `import epc_titleblock` and `import epc_titleblock.<module>` give the same objects as `epc_draw.titleblock`. New code imports `epc_draw.titleblock`. See `../draw/README.md`.
