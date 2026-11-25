# epc_plan (door)

The plan engine lives in `epc_draw.plan` since ADR-0042. This package only keeps the old names: `import epc_plan` and `import epc_plan.<module>` give the same objects as `epc_draw.plan`; `python -m epc_plan` still runs. New code imports `epc_draw.plan`. See `../draw/README.md`.
