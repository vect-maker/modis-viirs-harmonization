from enum import Enum


class ClusterStatus(str, Enum):
    ACTIVO = "Activo"
    AISLADO = "Aislado"
    FINALIZADO = "Finalizado"