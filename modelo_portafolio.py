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

    # === FILTROS ===
    if riesgo == "leve":
        filtro = (df["price_change_30d"] > 0) & (df["price_change_30d"] < 20) & (df["score"] > 0.6)
    elif riesgo == "moderado":
        filtro = (df["price_change_30d"] > -10) & (df["price_change_30d"] < 30) & (df["score"] > 0.35)
    elif riesgo == "volatil":
        filtro = (df["price_change_30d"] > -20) & (df["price_change_30d"] < 50)
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

    candidatos = df[filtro].copy()
    if candidatos.empty:
        print("No hay criptomonedas que cumplan los criterios.")
        return

    print(f"\n[DEBUG] {len(candidatos)} criptos pasaron el filtro ({riesgo})")
    print(f"Valores de price_change_30d: {candidatos['price_change_30d'].tolist()}")

    candidatos = candidatos.sort_values("score", ascending=False).head(top_n)
    total_score = candidatos["score"].sum()
    candidatos["peso"] = candidatos["score"] / total_score
    candidatos["monto_invertido"] = candidatos["peso"] * capital

    resumen = []
    x_range = list(range(puntos + 1))

    print(f"\n=== RECOMENDACIÓN DE PORTAFOLIO ({riesgo.upper()}, {plazo.upper()}) ===\n")

    for i, (_, row) in enumerate(candidatos.iterrows(), start=1):
        try:
            monto = row["monto_invertido"]
            precio = row["current_price"]
            unidades = monto / precio
            cambio_pct = row[col] / 100
            rendimiento_diario = (1 + cambio_pct) ** (1 / 30) - 1
            rendimiento_anual = (1 + rendimiento_diario) ** 365 - 1

            if escala == "horas":
                crecimiento = [(1 + rendimiento_diario) ** (h / 24) for h in x_range]
            elif escala == "días":
                crecimiento = [(1 + rendimiento_diario) ** d for d in x_range]
            elif escala == "meses":
                # Limitar el cambio de 30 días a +/-10% para proyección anual
                cambio_pct_limitado = max(min(cambio_pct, 0.1), -0.1)
                factor_30d = 1 + cambio_pct_limitado
                factor_diario = factor_30d ** (1/30)
                crecimiento = [(factor_diario ** (m * 30)) for m in x_range]
            else:
                crecimiento = [1] * len(x_range)

            proyeccion = [round(c * monto, 2) for c in crecimiento]
        except Exception as e:
            print(f"Error al procesar {row['symbol']}: {e}")
            continue

        resumen.append({
            "image": row.get("image", ""),
            "nombre": row["name"],
            "symbol": row["symbol"].upper(),
            "precio_actual": round(precio, 4),
            "unidades": round(unidades, 6),
            "valor_usd": round(unidades * precio, 2),
            "score": round(row["score"], 3),
            "reason": row.get("reason", ""),
            "plazo": plazo,
            "probabilidad_subida": f"{round(row['score'] * 100, 1)}%",
            "proyeccion": proyeccion
        })

        print(f"Crypto {i}: {row['name']} ({row['symbol'].upper()})")
        print(f"    Precio actual: ${precio:.4f}")
        print(f"    Unidades sugeridas: {unidades:.6f}")
        print(f"    Inversión en USD: ${unidades * precio:.2f}")
        print(f"    Score: {row['score']:.3f}")
        print(f"    Motivo: {row.get('reason', '')}")
        print(f"    Rendimiento anual estimado: {rendimiento_anual * 100:.2f}%\n")

    total_final = 0
    print("\n[DEBUG] Proyección final por cripto:")
    for r in resumen:
        print(f"  {r['symbol']}: {r['proyeccion'][-1]}")
        total_final += r['proyeccion'][-1]
    print(f"[DEBUG] Suma total proyectada: {total_final}")

print(json.dumps(resumen, indent=2, ensure_ascii=False))
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
