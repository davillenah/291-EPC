"""The words of the PV reports in English and Spanish (ADR-0043): one table, one function. A missing key is an error, never a silent blank."""
from epc_report.errors import ReportError

LANGS = ("en", "es")

T = {
    "pending_engine": ("not verified: the engine for this calculation is not built yet ({item})", "no verificado: el motor de este cálculo aún no existe ({item})"),
    "not_returned": ("not available: the engine does not return it", "no disponible: el motor no lo devuelve"),
    "complies": ("complies", "cumple"), "fails": ("does not comply", "no cumple"), "not_verified": ("not verified", "no verificado"),
    "edit_mode": ("EDIT MODE: norm values not verified, not for production", "MODO EDICIÓN: valores de norma sin verificar, no apto para producción"),
    "memo_title": ("PV calculation memorandum", "Memoria de cálculo fotovoltaica"),
    "summary_title": ("PV project summary", "Síntesis del proyecto fotovoltaico"),
    "h_input": ("1. Input data", "1. Datos de entrada"),
    "h_strings": ("2. Generator and strings", "2. Generador y strings"),
    "h_power": ("3. DC power and DC/AC ratio", "3. Potencia CC y relación CC/CA"),
    "h_energy": ("4. Energy production", "4. Producción de energía"),
    "h_pending": ("5. Other calculations", "5. Otros cálculos"),
    "h_summary": ("6. Summary of verifications", "6. Resumen de verificaciones"),
    "t_input": ("The input data fix the site, the module and the inverter. With them the number of modules in series and the strings per input are checked against the limits of the inverter.",
                "Los datos de entrada fijan el sitio, el módulo y el inversor. Con ellos se verifica el número de módulos en serie y los strings por entrada contra los límites del inversor."),
    "t_strings": ("With the generator layout validated, the DC power and its ratio to the AC power of the inverters follow.",
                  "Con la configuración del generador validada, se obtiene la potencia CC y su relación con la potencia CA de los inversores."),
    "t_power": ("From the power installed, the engine integrates the hourly simulation into the energy of the plant.",
                "A partir de la potencia instalada, el motor integra la simulación horaria en la energía de la planta."),
    "t_energy": ("The calculations below depend on the same data and are not yet done by an engine.",
                 "Los cálculos siguientes dependen de los mismos datos y todavía no los hace un motor."),
    "t_pending": ("All the results are gathered in one table.", "Todos los resultados se reúnen en una tabla."),
    "l_strings": ("Limits of the inverter against the modules in series and the strings per input (engine epc_pv).", "Límites del inversor frente a los módulos en serie y a los strings por entrada (motor epc_pv)."),
    "l_power": ("Power installed and its ratio to the AC power.", "Potencia instalada y su relación con la potencia CA."),
    "l_energy": ("Energy of the hourly simulation, from the engine.", "Energía de la simulación horaria, tomada del motor."),
    "data": ("Data", "Datos"), "formula": ("Formula", "Fórmula"), "subst": ("Substitution", "Sustitución"), "result": ("Result", "Resultado"),
    "criterion": ("Criterion", "Criterio"), "check": ("Verification", "Verificación"),
    "c_series": ("Modules in series", "Módulos en serie"), "c_mppt": ("Strings per MPPT input", "Strings por entrada MPPT"),
    "c_ratio": ("DC/AC ratio", "Relación CC/CA"), "c_energy": ("Annual energy and yield", "Energía anual y rendimiento"),
    "ratio_pending": ("the limit of the DC/AC ratio is pending the owner", "el límite de la relación CC/CA está pendiente del dueño"),
    "col_calc": ("Calculation", "Cálculo"), "col_mag": ("Quantity", "Magnitud"), "col_val": ("Value", "Valor"), "col_lim": ("Limit", "Límite"), "col_state": ("State", "Estado"),
    "pending_list": ("DC cables (C-16 to C-19), DC protections (C-20 to C-22), AC cables and protections (C-23 to C-26), short circuit and selectivity (C-27 to C-29), earthing (C-30, C-31), grid interface and structure.",
                     "Cables CC (C-16 a C-19), protecciones CC (C-20 a C-22), cables y protecciones CA (C-23 a C-26), cortocircuito y selectividad (C-27 a C-29), puesta a tierra (C-30, C-31), interfaz con la red y estructura."),
    "engine_line": ("Engine {name} {version}.", "Motor {name} {version}."),
    "problem": ("Problem", "Problema"), "solution": ("Proposed solution", "Solución propuesta"), "location": ("Location", "Ubicación"), "modules": ("Modules", "Módulos"),
    "strings": ("Strings", "Strings"), "inverters": ("Inverters", "Inversores"), "energy": ("Annual energy", "Energía anual"), "compliance": ("Compliance", "Cumplimiento"),
    "dc_cable": ("DC cable", "Cable CC"), "ac_cable": ("AC cable", "Cable CA"), "protections": ("Protections", "Protecciones"), "earthing": ("Earthing", "Puesta a tierra"),
    "n_a": ("not available", "no disponible"), "req": ("Requirement", "Requisito"), "tech": ("Technical data", "Dato técnico"), "obs": ("Observations", "Observaciones"),
    "plant": ("PV plant {kwp} kWp DC / {kw} kW AC", "Planta FV {kwp} kWp CC / {kw} kW CA"),
    "strings_line": ("{strings} strings of {n_series} modules in series; {mppt} strings per MPPT input (limit {limit})", "{strings} strings de {n_series} módulos en serie; {mppt} strings por entrada MPPT (límite {limit})"),
    "energy_line": ("{kwh} kWh/year · {yield_} kWh/kWp", "{kwh} kWh/año · {yield_} kWh/kWp"),
    "compl_line": ("{ok} comply · {no} do not comply · {nv} not verified", "{ok} cumplen · {no} no cumplen · {nv} no verificados"),
}


def tr(lang, key, **fmt):
    """The text of `key` in `lang` ('en' or 'es'), with the fields filled."""
    if lang not in LANGS:
        raise ReportError("err_language_unknown", options=", ".join(LANGS), lang=lang)
    return T[key][LANGS.index(lang)].format(**fmt)
