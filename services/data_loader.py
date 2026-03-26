"""Carga de datos — abstracción para cargar mock o datos reales."""

from services.scoring import cargar_scores, get_all_scores, get_kpis
from services.alerts import cargar_alertas, get_alertas_recientes, get_kpis_alertas
from services.zone_profile import cargar_perfiles, get_perfil
