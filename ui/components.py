"""Componentes reutilizables — cards, badges, loader, score, alertas."""

import base64
import streamlit as st
from pathlib import Path
from ui.theme import get_score_band, ALERT_TYPES, COLORS


def render_header():
    """Header con gradiente BP y branding AgroBip."""
    logo_path = Path("assets/agrobip.png")
    if logo_path.exists():
        img_bytes = logo_path.read_bytes()
        img_b64 = base64.b64encode(img_bytes).decode()
        logo_html = f'<img src="data:image/png;base64,{img_b64}" alt="AgroBip" style="max-height:60px;">'
    else:
        logo_html = '<h1>AgroBip</h1>'

    st.markdown(f"""
    <div class="header-gradient">
        {logo_html}
        <p>Radar de inteligencia comercial agropecuaria</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar_brand():
    """Logo y marca en sidebar."""
    logo_path = Path("assets/agrobip.png")
    if logo_path.exists():
        img_bytes = logo_path.read_bytes()
        img_b64 = base64.b64encode(img_bytes).decode()
        st.sidebar.markdown(f"""
        <div class="sidebar-logo">
            <img src="data:image/png;base64,{img_b64}" alt="AgroBip">
        </div>
        """, unsafe_allow_html=True)
    else:
        st.sidebar.markdown("""
        <div class="sidebar-brand">
            <h2>AgroBip</h2>
            <p>Inteligencia comercial agro</p>
        </div>
        """, unsafe_allow_html=True)


def render_metric_card(value, label, col=None):
    """Card de métrica."""
    html = f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """
    target = col if col else st
    target.markdown(html, unsafe_allow_html=True)


def render_score_badge(score):
    """Badge de score coloreado según banda."""
    band = get_score_band(score)
    return (
        f'<span class="score-badge" style="background:{band["bg"]}; '
        f'color:{band["color"]};">{score} — {band["label"]}</span>'
    )


def render_badge(text, color=None, bg=None):
    """Badge/tag genérico."""
    c = color or COLORS["tag_text"]
    b = bg or COLORS["tag_bg"]
    return f'<span class="bp-badge" style="background:{b}; color:{c};">{text}</span>'


def render_alert_badge(alert_type):
    """Badge para tipo de alerta."""
    info = ALERT_TYPES.get(alert_type, {"icon": "📌", "color": "#666", "bg": "#f5f5f5", "label": alert_type})
    return f'<span class="bp-badge" style="background:{info["bg"]}; color:{info["color"]};">{info["icon"]} {info["label"]}</span>'


def render_section_highlight(content):
    """Sección destacada con borde verde."""
    st.markdown(f'<div class="section-highlight">{content}</div>', unsafe_allow_html=True)


def render_divider():
    """Divider decorativo con gradiente."""
    st.markdown('<div class="bp-divider"></div>', unsafe_allow_html=True)


def render_section_label(text):
    """Label de sección."""
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def render_perrito_loader(message="Olfateando oportunidades..."):
    """Loader del perrito con animación."""
    perrito_path = Path("assets/perrito_bp.png")
    if perrito_path.exists():
        img_bytes = perrito_path.read_bytes()
        img_b64 = base64.b64encode(img_bytes).decode()
        img_tag = f'<img src="data:image/png;base64,{img_b64}" alt="Cargando...">'
    else:
        img_tag = '<div style="font-size:3rem;">🐕</div>'

    st.markdown(f"""
    <div class="perrito-loader">
        {img_tag}
        <p>{message}</p>
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    """Footer con firma."""
    firma_path = Path("assets/firma_pablo.png")
    if firma_path.exists():
        img_bytes = firma_path.read_bytes()
        img_b64 = base64.b64encode(img_bytes).decode()
        firma_tag = f'<img src="data:image/png;base64,{img_b64}" alt="@Pablocuadros19" style="max-width:180px; opacity:0.85;">'
    else:
        firma_tag = '<span style="font-style:italic; color:#999;">@Pablocuadros19</span>'

    st.markdown(f"""
    <div style="text-align:center; padding:2rem 0 1rem; margin-top:3rem;
                border-top:1px solid #e0e5ec;">
        {firma_tag}
        <p style="font-size:0.7rem; color:#999; margin-top:0.5rem;">
            AgroBip — Banco Provincia
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_alert_card(alerta):
    """Card de alerta completa."""
    info = ALERT_TYPES.get(alerta["tipo"], {"icon": "📌", "color": "#666", "label": alerta["tipo"]})
    border_color = info["color"]

    st.markdown(f"""
    <div class="alert-card" style="border-left-color:{border_color};">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <span class="alert-title">{info["icon"]} {alerta["titulo"]}</span>
                <br><span class="alert-zone">📍 {alerta["zona"]} — {alerta.get("provincia", "")}</span>
            </div>
            <div>
                {render_score_badge(alerta.get("score", 0))}
            </div>
        </div>
        <div class="alert-action">→ {alerta.get("accion", "")}</div>
        <div style="margin-top:0.3rem; font-size:0.75rem; color:#999;">
            {alerta.get("producto_bp", "")}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_zone_summary_card(zona):
    """Mini-card de zona para listados (top 5, etc.)."""
    band = get_score_band(zona["score"])
    etiqueta = zona.get("etiqueta", "")
    etiqueta_html = f'<span class="bp-badge" style="background:{band["bg"]}; color:{band["color"]}; font-size:0.7rem;">{etiqueta}</span>' if etiqueta else ""

    st.markdown(f"""
    <div class="zone-card">
        <div>
            <span class="zone-name">{zona["nombre"]}</span>
            <br><span class="zone-detail">{zona.get("provincia", "")} · {zona.get("cultivo_principal", "")}</span>
        </div>
        <div style="text-align:right;">
            <span style="font-size:1.2rem; font-weight:700; color:{band['color']};">{zona["score"]}</span>
            <br>{etiqueta_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_score_breakdown(componentes):
    """Barras de desglose de score por dimensión."""
    colors = ["#00A651", "#00B8D4", "#1565c0", "#e65100"]
    for i, (label, valor) in enumerate(componentes.items()):
        color = colors[i % len(colors)]
        width = min(valor, 100)
        st.markdown(f"""
        <div class="score-bar-container">
            <div class="score-bar-label">{label}: {valor}/100</div>
            <div class="score-bar-track">
                <div class="score-bar-fill" style="width:{width}%; background:{color};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_producto_sugerido(producto):
    """Card de producto BP sugerido."""
    st.markdown(f"""
    <div class="producto-sugerido">
        <h4>💼 Producto BP sugerido</h4>
        <div class="producto-nombre">{producto["nombre"]}</div>
        <div class="producto-detalle">{producto.get("detalle", "")}</div>
        <div style="margin-top:0.5rem; font-size:0.78rem; color:#00A651; font-weight:600;">
            {producto.get("condicion", "")}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_ficha_pregunta(pregunta, respuesta):
    """Card de pregunta/respuesta para ficha de zona."""
    st.markdown(f"""
    <div class="ficha-pregunta">
        <h4>{pregunta}</h4>
        <p>{respuesta}</p>
    </div>
    """, unsafe_allow_html=True)


# --- Componentes Radar Agro ---

def render_clasificacion_badge(clasificacion):
    from ui.theme import CLASIFICACION_COLORS
    info = CLASIFICACION_COLORS.get(clasificacion, CLASIFICACION_COLORS["pendiente"])
    st.markdown(
        f'<span style="background:{info["bg"]};color:{info["color"]};font-size:0.78rem;'
        f'font-weight:600;padding:0.2rem 0.7rem;border-radius:20px;white-space:nowrap">'
        f'{info["icon"]} {info["label"]}</span>',
        unsafe_allow_html=True,
    )


def render_semaforo_badge(semaforo):
    from ui.theme import SEMAFORO_COLORS
    info = SEMAFORO_COLORS.get(semaforo, SEMAFORO_COLORS["pendiente"])
    st.markdown(
        f'<span style="background:{info["bg"]};color:{info["color"]};font-size:0.78rem;'
        f'font-weight:600;padding:0.2rem 0.7rem;border-radius:20px;white-space:nowrap">'
        f'{info["icon"]} {info["label"]}</span>',
        unsafe_allow_html=True,
    )


def render_prospect_card(prospecto):
    """Card de prospecto para Top 5 del día."""
    from ui.theme import CLASIFICACION_COLORS, SEMAFORO_COLORS

    clas_info = CLASIFICACION_COLORS.get(prospecto.get("clasificacion", ""), CLASIFICACION_COLORS["pendiente"])
    sem_info = SEMAFORO_COLORS.get(prospecto.get("semaforo", ""), SEMAFORO_COLORS["pendiente"])
    score = prospecto.get("score_total", 0)
    cuit = prospecto.get("cuit", "")
    if len(cuit) == 11:
        cuit_fmt = f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"
    else:
        cuit_fmt = cuit

    cliente_bp = ' <span style="background:#e8f5ee;color:#00A651;font-size:0.6rem;font-weight:700;padding:0.1rem 0.4rem;border-radius:10px">BP</span>' if prospecto.get("es_cliente_bp") else ""

    st.markdown(f"""
    <div style="background:#f7f9fc;border:1px solid {clas_info['color']}30;border-left:4px solid {clas_info['color']};
                border-radius:10px;padding:0.8rem 1rem;margin:0.3rem 0">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-size:0.9rem;font-weight:700;color:#1a1a2e">
                {prospecto.get('razon_social', 'Sin nombre')}{cliente_bp}
            </span>
            <span style="font-size:1.3rem;font-weight:900;color:{clas_info['color']}">{score}</span>
        </div>
        <div style="font-size:0.75rem;color:#888;margin-top:0.2rem">
            {cuit_fmt} · {prospecto.get('partido', '')}
            <span style="margin-left:0.5rem;background:{clas_info['bg']};color:{clas_info['color']};
                         font-size:0.65rem;font-weight:600;padding:0.1rem 0.5rem;border-radius:20px">
                {clas_info['icon']} {clas_info['label']}</span>
            <span style="margin-left:0.3rem;background:{sem_info['bg']};color:{sem_info['color']};
                         font-size:0.65rem;font-weight:600;padding:0.1rem 0.5rem;border-radius:20px">
                {sem_info['icon']} {sem_info['label']}</span>
        </div>
        <div style="font-size:0.78rem;color:#555;margin-top:0.3rem;font-style:italic">
            "{prospecto.get('clasificacion_motivo', '')}"
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_evolucion_badge(evolucion):
    estilos = {
        "mejorando": ("↑", "#00A651", "#e8f5ee"),
        "estable": ("→", "#1565c0", "#e3f2fd"),
        "empeorando": ("↓", "#c62828", "#fce4ec"),
        "sin_historial": ("—", "#999", "#f5f5f5"),
    }
    flecha, color, bg = estilos.get(evolucion, ("—", "#999", "#f5f5f5"))
    st.markdown(
        f'<span style="background:{bg};color:{color};font-size:0.85rem;font-weight:700;'
        f'padding:0.15rem 0.5rem;border-radius:8px">{flecha} {evolucion or "sin datos"}</span>',
        unsafe_allow_html=True,
    )
