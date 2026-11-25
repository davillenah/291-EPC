# epc_sld (door)

The single-line diagram generator lives in `epc_draw.sld` since ADR-0042. This package only keeps the old names: `import epc_sld` and `import epc_sld.<module>` give the same objects as `epc_draw.sld`. New code imports `epc_draw.sld`. See `../draw/README.md`.
