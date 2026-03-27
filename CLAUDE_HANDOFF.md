# CLAUDE_HANDOFF — AgroBip

## Qué es esto
Radar de inteligencia comercial anticipada para banca agropecuaria (Banco Provincia).
Convierte señales territoriales, productivas y financieras en oportunidades comerciales accionables.

## Stack y estado
- Python + Streamlit, streamlit-folium para mapas
- Datos: MAGyP (producción), SENASA (bovinos), ORA (estrés hídrico)
- Scoring v2 activo — 4 dimensiones, bandas Alta/Media/Observar/Sin prioridad
- Páginas activas: Dashboard, Radar, Alertas, Producción, Scoring, Ficha de Zona

## Infraestructura compartida disponible (generada por LICITARG)

Estos archivos están en `C:\LICITARG\data\` y NO hay que regenerarlos:

| Archivo | Descripción |
|---|---|
| `C:\LICITARG\data\raw\sociedades\sociedades-ba-caba.csv` | **1.67M empresas BA/CABA** con CUIT + domicilio + actividad CLAE |
| `C:\LICITARG\data\processed\agro-proveedores-estado.parquet` | **120K empresas agro** BA/CABA con flag proveedor_estado + monto_adj |
| `C:\LICITARG\data\processed\proveedores.parquet` | 5,615 proveedores del estado con geo y adjudicaciones |

## Lo que estos datos habilitan para AgroBip

### 1. Capa empresa en Ficha de Zona (nueva sección)
Hoy la ficha muestra métricas agregadas por departamento.
Con `sociedades-ba-caba.csv` filtrado por CLAE agro + partido, podés mostrar:
- Top 10 empresas agropecuarias del partido (por tipo societario, calle, CUIT)
- Cuántas son SA vs SRL vs persona física
- Cuáles son también proveedoras del estado (481 en toda BA/CABA)

Cómo cargar (ejemplo):
```python
import pandas as pd
df = pd.read_csv(r"C:\LICITARG\data\raw\sociedades\sociedades-ba-caba.csv", dtype=str)
# Filtrar agro por partido
mask = (
    df["actividad_descripcion"].str.lower().str.contains("cultivo|ganado|soja|trigo", na=False) &
    df["dom_fiscal_localidad"].str.upper().str.contains("PEHUAJO|TRENQUE", na=False)
)
empresas_zona = df[mask]
```

### 2. Score bonus "presencia empresas estado" (nueva dimensión scoring)
En `services/scoring.py`, agregar dimensión:
- Si en el partido hay empresas proveedoras del estado → +5 puntos al score
- Señal de que la zona tiene operadores financieramente formalizados

### 3. Búsqueda de contacto individual
Dado un CUIT encontrado en la ficha → consultar BCRA:
```python
import requests
r = requests.get(f"https://api.bcra.gob.ar/CentralDeDeudores/v1.0/Deudas/{cuit}", timeout=10)
```

## Productos BP agro vigentes (marzo 2026)
- Préstamos Siembra (trigo, maíz, soja, girasol) — TNA 37% fija
- Préstamos Lechería — inversión + cap. trabajo
- Préstamos Ganados y Carnes
- Capital de Trabajo PIV/PAIV
- Procampo Digital (pesos y USD)
- Refinanciación emergencia/desastre
- Tarjetas Corporativas Procampo

## Scoring v2 — dimensiones actuales
| Dimensión | Peso | Fuente |
|---|---|---|
| Producción VBP USD | 40% | MAGyP |
| Variación superficie | 20% | MAGyP |
| Bovinos SENASA | 20% | SENASA |
| Emergencia activa | 20% | Decretos (manual) |

## Pendientes prioritarios
- [ ] Agregar sección "Empresas del sector" en page_ficha.py (leer agro-proveedores-estado.parquet)
- [ ] Agregar dimensión "proveedores_estado_partido" en scoring.py
- [ ] Conectar con NyPer: cuando encontrás una empresa agro con CUIT → generar campaña en NyPer
- [ ] Stress hídrico ORA: verificar si la URL del API sigue activa

## Cómo arrancar
```bash
cd C:\AgroBip
streamlit run app.py
```
