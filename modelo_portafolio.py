import os
import json
import pandas as pd
import numpy as np
import sys

# === RUTAS ===
INPUT_JSON = "criptos_predichas.json"

# === CARGAR DATOS ===
def cargar_criptos():
    if not os.path.exists(INPUT_JSON):
        raise FileNotFoundError(f"No se encontró el archivo: {INPUT_JSON}")
    
    with open(INPUT_JSON, encoding="utf-8") as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)

    obligatorias = ["name", "symbol", "current_price", "price_change_24h", "price_change_30d", "score"]
    for col in obligatorias:
        if col not in df.columns:
            raise KeyError(f"Falta la columna obligatoria: {col}")

    df = df[df["price_change_30d"] < 300]
    df = df[df["current_price"] > 0]
    df = df[df["score"] > 0]

    return df

# === RECOMENDADOR PRINCIPAL ===
def recomendar_portafolio(capital: float, riesgo: str, plazo: str, top_n: int = 5):
    if capital < 10:
        raise ValueError("El capital mínimo debe ser al menos $10")

    df = cargar_criptos()

    # === FILTROS DIFERENCIADOS ===
    if riesgo == "leve":
        if plazo == "1a":
            # Menos estricto: permite price_change_30d hasta 35 y score > 0.35
            filtro = (df["price_change_30d"] > 0) & (df["price_change_30d"] < 35) & (df["score"] > 0.35)
        else:
            # Menos estricto: permite price_change_30d hasta 25 y score > 0.4
            filtro = (df["price_change_30d"] > 0) & (df["price_change_30d"] < 25) & (df["score"] > 0.4)
    elif riesgo == "moderado":
        # Más intermedio: price_change_30d > -15 y < 40, score > 0.3
        filtro = (df["price_change_30d"] > -15) & (df["price_change_30d"] < 40) & (df["score"] > 0.3)
    elif riesgo == "volatil":
        filtro = (df["price_change_30d"] > -30) & (df["price_change_30d"] < 60) & (df["score"] > 0.2)
    else:
        raise ValueError("Riesgo inválido: leve, moderado o volatil")

    if plazo == "24h":
        col = "price_change_24h"
        puntos = 24
        escala = "horas"
    elif plazo == "30d":
        col = "price_change_30d"
        puntos = 30
        escala = "días"
    elif plazo == "1a":
        col = "price_change_30d"
        puntos = 12
        escala = "meses"
    else:
        raise ValueError("Plazo inválido: 24h, 30d o 1a")

    candidatos = df[filtro]
    if not isinstance(candidatos, pd.DataFrame):
        candidatos = pd.DataFrame(candidatos)
    candidatos = candidatos.copy()
    if candidatos.shape[0] == 0:
        print(json.dumps([]))
        return

    candidatos = candidatos.sort_values("score", ascending=False).head(top_n)
    total_score = float(candidatos["score"].sum())
    candidatos["peso"] = candidatos["score"] / total_score if total_score > 0 else 0
    candidatos["monto_invertido"] = candidatos["peso"] * capital

    resumen = []
    x_range = list(range(puntos + 1))

    for _, row in candidatos.iterrows():
        try:
            monto = float(row["monto_invertido"])
            precio = float(row["current_price"])
            unidades = monto / precio
            cambio_pct = float(row[col]) / 100

            # === AJUSTE DE PROYECCIÓN SEGÚN RIESGO ===
            if riesgo == "leve":
                # Limita el crecimiento anual a +/-5% para conservador
                cambio_pct_limitado = max(min(cambio_pct, 0.05), -0.05)
            elif riesgo == "moderado":
                # Limita el crecimiento anual a +/-15%
                cambio_pct_limitado = max(min(cambio_pct, 0.15), -0.15)
            elif riesgo == "volatil":
                # Permite hasta +/-40%
                cambio_pct_limitado = max(min(cambio_pct, 0.4), -0.4)
            else:
                cambio_pct_limitado = cambio_pct

            rendimiento_diario = (1 + cambio_pct_limitado) ** (1 / 30) - 1
            rendimiento_anual = (1 + rendimiento_diario) ** 365 - 1

            if escala == "horas":
                crecimiento = [(1 + rendimiento_diario) ** (h / 24) for h in x_range]
            elif escala == "días":
                crecimiento = [(1 + rendimiento_diario) ** d for d in x_range]
            elif escala == "meses":
                factor_30d = 1 + cambio_pct_limitado
                factor_diario = factor_30d ** (1/30)
                crecimiento = [(factor_diario ** (m * 30)) for m in x_range]
            else:
                crecimiento = [1] * len(x_range)

            proyeccion = [round(float(c) * monto, 2) for c in crecimiento]
        except Exception:
            continue

        resumen.append({
            "image": row.get("image", ""),
            "nombre": row["name"],
            "symbol": str(row["symbol"]).upper(),
            "precio_actual": round(float(precio), 4),
            "unidades": round(float(unidades), 6),
            "valor_usd": round(float(unidades) * float(precio), 2),
            "score": round(float(row["score"]), 3),
            "reason": row.get("reason", ""),
            "plazo": plazo,
            "probabilidad_subida": f"{round(float(row['score']) * 100, 1)}%",
            "proyeccion": proyeccion
        })

    print(json.dumps(resumen, ensure_ascii=False))

# === EJECUCIÓN DESDE TERMINAL ===
if __name__ == "__main__":
    if len(sys.argv) in (4, 5):
        try:
            capital = float(sys.argv[1])
            riesgo = sys.argv[2].lower()
            plazo = sys.argv[3].lower()
            top_n = int(sys.argv[4]) if len(sys.argv) == 5 else 5
            recomendar_portafolio(capital, riesgo, plazo, top_n)
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Uso: python modelo_portafolio.py <capital> <riesgo> <plazo> [top_n]")
    else:
        print("Modo de uso:")
        print("python modelo_portafolio.py 1000 moderado 30d [top_n]")
