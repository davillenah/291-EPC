# epc_mld (door)

The multi-line diagram generator lives in `epc_draw.mld` since ADR-0042. This package only keeps the old names: `import epc_mld` and `import epc_mld.<module>` give the same objects as `epc_draw.mld`. New code imports `epc_draw.mld`. See `../draw/README.md`.
