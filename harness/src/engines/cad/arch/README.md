# epc_arch (door)

The architecture recognition engine lives in `epc_draw.arch` since ADR-0042. This package only keeps the old names: `import epc_arch` and `import epc_arch.<module>` give the same objects as `epc_draw.arch`; `python -m epc_arch` still runs. New code imports `epc_draw.arch`. See `../draw/README.md`.
