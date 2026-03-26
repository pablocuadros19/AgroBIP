# CLAUDE.md — AgroBip

## Qué es AgroBip
Radar de inteligencia comercial anticipada para banca agropecuaria (Banco Provincia). Convierte señales territoriales, climáticas, productivas y financieras en oportunidades comerciales concretas, priorizadas y accionables.

## Propuesta de valor
"Sabé a dónde mirar antes que nadie."

## Stack
- **Python + Streamlit** (MVP)
- **streamlit-folium** para mapas coropléticos
- **geopandas** para GeoJSON
- Datos locales (JSON/CSV), sin DB compleja en MVP
- Estética Banco Provincia (sistema NyPer)

## Arquitectura
```
AgroBip/
├── app.py                  # entrada principal, navegación por páginas
├── services/
│   ├── geo_data.py         # GeoJSON departamentos, funciones geo
│   ├── scoring.py          # motor de scoring v1
│   ├── data_loader.py      # carga datos MAGyP, ORA
│   ├── alerts.py           # generación y gestión de alertas
│   └── zone_profile.py     # perfiles productivos por zona
├── ui/
│   ├── theme.py            # CSS centralizado, estética BP
│   ├── components.py       # componentes reutilizables
│   ├── page_dashboard.py   # home con KPIs
│   ├── page_radar.py       # mapa coroplético
│   ├── page_alertas.py     # feed de alertas
│   ├── page_ficha.py       # ficha de zona
│   └── page_scoring.py     # tabla de scoring
├── data/                   # datos y mocks
└── assets/                 # imágenes y logos
```

## Módulos del producto
1. **Dashboard:** KPIs principales, top 5 zonas calientes, alertas recientes
2. **Radar Territorial:** mapa coroplético por departamento, coloreado por score
3. **Alertas:** feed cronológico de señales (estrés hídrico, emergencia, cambio productivo)
4. **Scoring:** score 0-100 por departamento. Bandas: 80-100 alta, 60-79 media, 40-59 observar, 0-39 sin prioridad
5. **Ficha de Zona:** responde ¿qué pasa? ¿por qué importa? ¿qué producto ofrecer? ¿qué prioridad?

## Productos BP reales (vigentes marzo 2026)
- Préstamos Siembra (trigo, maíz, soja, girasol) — TNA 37% fija
- Préstamos Lechería — inversión + cap. trabajo
- Préstamos Ganados y Carnes — inversión + cap. trabajo
- Capital de Trabajo PIV/PAIV
- Procampo Digital (pesos y USD)
- Refinanciación emergencia/desastre
- Tarjetas Corporativas Procampo

## Scoring v1 (4 dimensiones)
| Dimensión | Peso | Fuente |
|---|---|---|
| Estrés hídrico | 35% | ORA |
| Perfil productivo | 25% | MAGyP |
| Dinámica de cambio | 20% | MAGyP |
| Emergencia/riesgo | 20% | Decretos |

## Identidad visual
Aplica sistema de diseño NyPer/BP (definido en CLAUDE.md global):
- Colores: primary #00A651, secondary #00B8D4
- Fuente: Montserrat
- Loader: perrito olfateando
- Cards, badges, gradientes, tabs según sistema BP

## Preferencias de código
- Python, snake_case, funciones cortas
- Comentarios en español solo si aclaran algo no obvio
- Sin clases innecesarias
- MVP primero, iterar rápido

## Cómo arrancar
```bash
cd AgroBip
pip install -r requirements.txt
streamlit run app.py
```
