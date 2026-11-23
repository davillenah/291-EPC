"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_impedance_zero": {
        "en": "Total impedance is zero: Ik'' is infinite (add a network, a transformer or a cable)",
        "es": "Impedancia total nula: Ik'' infinita (agregar red, transformador o cable)",
    },
    "err_kappa_range": {
        "en": "kappa must be between 1 and 2",
        "es": "κ debe estar entre 1 y 2",
    },
    "err_kt_needs_transformer": {
        "en": "aplicar_kt requires a transformer",
        "es": "aplicar_kt requiere un transformador",
    },
    "err_mu_q_range": {
        "en": "0 < mu*q < 1 is required",
        "es": "se requiere 0 < μ·q < 1",
    },
    "err_parallel_count": {
        "en": "n_paralelo must be an integer >= 1",
        "es": "n_paralelo debe ser entero ≥ 1",
    },
    "err_pcu_uk": {
        "en": "Pcu is incompatible with uk: R_T >= Z_T (copper losses >= uk*Sn)",
        "es": "Pcu incompatible con uk: R_T ≥ Z_T (pérdidas en el cobre ≥ uk·Sn)",
    },
    "err_r_x_zero": {
        "en": "R and X cannot both be zero",
        "es": "R y X no pueden ser ambos cero",
    },
    "err_sk_or_ik": {
        "en": "Give exactly one of sk_va (short-circuit power) or ik_a (current)",
        "es": "Indicar exactamente uno de sk_va (potencia de cortocircuito) o ik_a (corriente)",
    },
    "err_tolerance_without_c": {
        "en": "Tolerance {tolerancia_pct!r} % has no predefined c (only 6 or 10); enter c explicitly",
        "es": "Tolerancia {tolerancia_pct!r} % sin c predefinido (solo 6 o 10); ingresar c explícito",
    },
    "err_uk_range": {
        "en": "uk_pct must be < 100",
        "es": "uk_pct debe ser < 100",
    },
    "err_xd_or_sin_phi": {
        "en": "give x_d_pu ([43]) or sen_fi_rg ([45b])",
        "es": "indicar x_d_pu ([43]) o sen_fi_rg ([45b])",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
