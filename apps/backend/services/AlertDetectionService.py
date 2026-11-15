from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlmodel import Session, col, select

from analytics.FireForecastService import haversine_km
from model.Alert import Alert, AlertRule, AlertRuleType
from model.EnvironmentalRecord import EnvironmentalRecord
from model.FireCluster import FireCluster
from repositories.DashboardRepository import DashboardRepository
from services.AlertManagementService import AlertManagementService
from services.AlertRuleService import AlertRuleService
from services.NotificationService import NotificationService

logger = logging.getLogger("firms.early_warning")


def _parse_dt(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=UTC) if val.tzinfo is None else val
    return datetime.fromisoformat(str(val).replace("Z", "+00:00")).replace(tzinfo=UTC)


class AlertDetectionService:
    """
    Motor de evaluación de reglas tempranas sobre hotspots, clusters, FRP,
    condiciones meteorológicas y proximidad configurada.
    """

    def __init__(
        self,
        session: Session,
        notifier: NotificationService | None = None,
    ) -> None:
        self.session = session
        self.rule_service = AlertRuleService(session)
        self.mgmt_service = AlertManagementService(session)
        self.dashboard_repo = DashboardRepository(session)
        self.notifier = notifier or NotificationService()
        bind = session.get_bind()
        self.dialect = bind.dialect.name if bind is not None else "postgresql"

    def _dt_param(self, dt: datetime) -> datetime:
        return dt if self.dialect == "postgresql" else dt.replace(tzinfo=None)

    def _find_matching_cluster_id(
        self,
        window_start: datetime,
        window_end: datetime,
    ) -> int | None:
        stmt = (
            select(FireCluster)
            .where(
                col(FireCluster.datetimeStart).is_not(None),
                col(FireCluster.datetimeStart) <= window_end,
            )
            .order_by(col(FireCluster.maxFrp).desc())
            .limit(20)
        )
        clusters = list(self.session.exec(stmt).all())
        start_naive = window_start.replace(tzinfo=None)
        for c in clusters:
            if c.datetimeStart is None or c.id is None:
                continue
            c_end = (c.datetimeEnd or c.datetimeStart).replace(tzinfo=None)
            if c_end >= start_naive:
                return c.id
        return None

    async def evaluate_rules(
        self,
        rule_ids: list[int] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        processed_at = now or datetime.now(UTC)
        received_at = processed_at
        rules = self.rule_service.get_active_rules(rule_ids=rule_ids)

        created_alerts: list[Alert] = []
        skipped_duplicates = 0
        errors: list[str] = []

        for rule in rules:
            if rule.id is None:
                continue
            try:
                conditions = json.loads(rule.conditionsJson or "{}")
                candidate = self._evaluate_single_rule(
                    rule=rule,
                    conditions=conditions,
                    received_at=received_at,
                    processed_at=processed_at,
                )
                self.rule_service.mark_executed(rule, processed_at)
                if candidate is None:
                    continue

                created = self.mgmt_service.create_alert_if_new(**candidate)
                if created is None:
                    skipped_duplicates += 1
                    continue

                created_alerts.append(created)
                await self.notifier.notify(
                    self.mgmt_service.to_read(created).model_dump(mode="json")
                )
            except Exception as exc:
                logger.exception("Error evaluando regla id=%s (%s): %s", rule.id, rule.name, exc)
                errors.append(f"rule:{rule.id}:{exc}")

        return {
            "status": "completed",
            "evaluated_rules": len(rules),
            "created_alerts": len(created_alerts),
            "skipped_duplicates": skipped_duplicates,
            "errors": errors,
        }

    def _region_filter(self, region: str | None) -> tuple[str, dict[str, Any]]:
        if region:
            return " AND LOWER(TRIM(country)) = LOWER(TRIM(:region))", {"region": region}
        return "", {}

    def _evaluate_single_rule(
        self,
        rule: AlertRule,
        conditions: dict[str, Any],
        received_at: datetime,
        processed_at: datetime,
    ) -> dict[str, Any] | None:
        assert rule.id is not None
        lookback_hours = float(conditions.get("lookback_hours", 24.0))
        window_start = processed_at - timedelta(hours=lookback_hours)
        bucket_tag = processed_at.strftime("%Y%m%d%H")
        region_sql, region_params = self._region_filter(rule.region)

        base_params: dict[str, Any] = {
            "start_dt": self._dt_param(window_start),
            "end_dt": self._dt_param(processed_at),
            **region_params,
        }
        cluster_id = self._find_matching_cluster_id(window_start, processed_at)

        if rule.ruleType == AlertRuleType.NEW_HOTSPOTS:
            min_count = int(conditions.get("min_count", 1))
            sql = text(
                f"""
                SELECT COUNT(*) AS cnt, MAX(acq_datetime) AS latest_dt,
                       MAX(frp) AS max_frp, MAX(instrument) AS inst, MAX(confidence) AS conf
                FROM hotspots
                WHERE acq_datetime >= :start_dt AND acq_datetime <= :end_dt
                {region_sql}
                """
            )
            row = self.session.execute(sql, base_params).mappings().one()
            cnt = int(row["cnt"] or 0)
            if cnt < min_count:
                return None
            return {
                "rule_id": rule.id,
                "dedup_key": f"rule:{rule.id}:new_hotspots:{rule.region or 'all'}:{bucket_tag}",
                "title": f"Posible actividad térmica satelital ({cnt} detecciones)",
                "message": (
                    f"Se detectaron {cnt} detecciones satelitales recientes en las últimas "
                    f"{lookback_hours:.0f}h (no confirmadas en campo)."
                ),
                "severity": rule.severity,
                "region": rule.region,
                "fire_cluster_id": cluster_id,
                "metadata": {"count": cnt, "max_frp": row["max_frp"], "lookback_hours": lookback_hours},
                "acquisition_at": _parse_dt(row["latest_dt"]),
                "received_at": received_at,
                "processed_at": processed_at,
                "source": f"NASA FIRMS / {row['inst'] or 'Multi-Sensor'}",
                "confidence_level": str(row["conf"]) if row["conf"] is not None else None,
            }

        if rule.ruleType == AlertRuleType.ACTIVITY_SPIKE:
            spike_ratio = float(conditions.get("spike_ratio", 2.0))
            min_recent = int(conditions.get("min_recent_count", 5))
            prev_start = window_start - timedelta(hours=lookback_hours)
            sql_recent = text(
                f"SELECT COUNT(*) AS cnt, MAX(acq_datetime) AS latest_dt, MAX(instrument) AS inst "
                f"FROM hotspots WHERE acq_datetime >= :start_dt AND acq_datetime <= :end_dt {region_sql}"
            )
            sql_prev = text(
                f"SELECT COUNT(*) AS cnt FROM hotspots "
                f"WHERE acq_datetime >= :prev_start AND acq_datetime < :start_dt {region_sql}"
            )
            r_row = self.session.execute(sql_recent, base_params).mappings().one()
            p_cnt = int(
                self.session.execute(
                    sql_prev, {**base_params, "prev_start": self._dt_param(prev_start)}
                ).scalar()
                or 0
            )
            r_cnt = int(r_row["cnt"] or 0)
            ratio = (r_cnt / p_cnt) if p_cnt > 0 else float(r_cnt)
            if r_cnt < min_recent or ratio < spike_ratio:
                return None
            return {
                "rule_id": rule.id,
                "dedup_key": f"rule:{rule.id}:spike:{rule.region or 'all'}:{bucket_tag}",
                "title": f"Aumento repentino de actividad térmica satelital ({ratio:.1f}x)",
                "message": (
                    f"Incremento de detecciones satelitales de {p_cnt} a {r_cnt} "
                    f"(razón {ratio:.2f}x, umbral {spike_ratio:.2f}x). Requiere verificación."
                ),
                "severity": rule.severity,
                "region": rule.region,
                "fire_cluster_id": cluster_id,
                "metadata": {"recent_count": r_cnt, "previous_count": p_cnt, "ratio": round(ratio, 3)},
                "acquisition_at": _parse_dt(r_row["latest_dt"]),
                "received_at": received_at,
                "processed_at": processed_at,
                "source": f"NASA FIRMS / {r_row['inst'] or 'Multi-Sensor'}",
                "confidence_level": None,
            }

        if rule.ruleType == AlertRuleType.HIGH_HOTSPOT_CONCENTRATION:
            min_per_cell = int(conditions.get("min_hotspots_per_cell", 5))
            cell_deg = float(conditions.get("cell_size_deg", 0.1))
            cells = self.dashboard_repo.get_spatial_density(
                cell_size_deg=cell_deg,
                start_date=window_start,
                end_date=processed_at,
                limit=5,
            )
            if not cells or cells[0]["count"] < min_per_cell:
                return None
            top = cells[0]
            return {
                "rule_id": rule.id,
                "dedup_key": f"rule:{rule.id}:conc:{top['cell_lat']}:{top['cell_lon']}:{bucket_tag}",
                "title": f"Alta concentración de detecciones térmicas ({top['count']} en celda)",
                "message": (
                    f"Se registró una concentración de {top['count']} detecciones satelitales "
                    f"alrededor de ({top['cell_lat']}, {top['cell_lon']}) (actividad no confirmada)."
                ),
                "severity": rule.severity,
                "region": rule.region,
                "fire_cluster_id": cluster_id,
                "metadata": top,
                "acquisition_at": processed_at,
                "received_at": received_at,
                "processed_at": processed_at,
                "source": "NASA FIRMS / Spatial Grid",
                "confidence_level": None,
            }

        if rule.ruleType == AlertRuleType.HIGH_FRP:
            min_frp = float(conditions.get("min_frp", 50.0))
            sql = text(
                f"""
                SELECT COUNT(*) AS cnt, MAX(frp) AS max_frp, MAX(acq_datetime) AS latest_dt,
                       MAX(instrument) AS inst, MAX(confidence) AS conf
                FROM hotspots
                WHERE acq_datetime >= :start_dt AND acq_datetime <= :end_dt
                  AND frp >= :min_frp
                {region_sql}
                """
            )
            row = self.session.execute(sql, {**base_params, "min_frp": min_frp}).mappings().one()
            cnt = int(row["cnt"] or 0)
            if cnt == 0:
                return None
            return {
                "rule_id": rule.id,
                "dedup_key": f"rule:{rule.id}:high_frp:{rule.region or 'all'}:{bucket_tag}",
                "title": f"FRP elevado detectado ({float(row['max_frp']):.1f} MW)",
                "message": (
                    f"Se registraron {cnt} detecciones con FRP >= {min_frp:.1f} MW "
                    f"(máximo {float(row['max_frp']):.1f} MW). Posible anomalía térmica intensa."
                ),
                "severity": rule.severity,
                "region": rule.region,
                "fire_cluster_id": cluster_id,
                "metadata": {"count": cnt, "max_frp": row["max_frp"], "threshold_frp": min_frp},
                "acquisition_at": _parse_dt(row["latest_dt"]),
                "received_at": received_at,
                "processed_at": processed_at,
                "source": f"NASA FIRMS / {row['inst'] or 'Multi-Sensor'}",
                "confidence_level": str(row["conf"]) if row["conf"] is not None else None,
            }

        if rule.ruleType in {AlertRuleType.NEAR_COMMUNITY, AlertRuleType.NEAR_PROTECTED_AREA}:
            target_lat = conditions.get("target_lat")
            target_lon = conditions.get("target_lon")
            radius_km = float(conditions.get("radius_km", 10.0))
            target_name = str(conditions.get("target_name", "zona sensible"))
            if target_lat is None or target_lon is None:
                return None
            lat_f, lon_f = float(target_lat), float(target_lon)
            dlat = radius_km / 111.0
            dlon = radius_km / max(1e-6, 111.0 * abs(math.cos(math.radians(lat_f))))
            sql = text(
                f"""
                SELECT latitude, longitude, acq_datetime, frp, instrument, confidence
                FROM hotspots
                WHERE acq_datetime >= :start_dt AND acq_datetime <= :end_dt
                  AND latitude BETWEEN :min_lat AND :max_lat
                  AND longitude BETWEEN :min_lon AND :max_lon
                {region_sql}
                LIMIT 500
                """
            )
            rows = self.session.execute(
                sql,
                {
                    **base_params,
                    "min_lat": lat_f - dlat,
                    "max_lat": lat_f + dlat,
                    "min_lon": lon_f - dlon,
                    "max_lon": lon_f + dlon,
                },
            ).mappings()
            matches = [
                r
                for r in rows
                if haversine_km(lat_f, lon_f, float(r["latitude"]), float(r["longitude"]))
                <= radius_km
            ]
            if not matches:
                return None
            acq_dates = [
                dt
                for m in matches
                if (dt := _parse_dt(m["acq_datetime"])) is not None
            ]
            latest = max(acq_dates, default=None)
            return {
                "rule_id": rule.id,
                "dedup_key": f"rule:{rule.id}:near:{target_name}:{bucket_tag}",
                "title": f"Actividad térmica cercana a {target_name} ({len(matches)} detecciones)",
                "message": (
                    f"Se observaron {len(matches)} detecciones satelitales dentro de "
                    f"{radius_km:.1f} km de {target_name} (requiere verificación en campo)."
                ),
                "severity": rule.severity,
                "region": rule.region,
                "fire_cluster_id": cluster_id,
                "metadata": {"target_name": target_name, "radius_km": radius_km, "matches": len(matches)},
                "acquisition_at": latest,
                "received_at": received_at,
                "processed_at": processed_at,
                "source": f"NASA FIRMS / {matches[0]['instrument'] or 'Multi-Sensor'}",
                "confidence_level": str(matches[0]["confidence"]) if matches[0]["confidence"] is not None else None,
            }

        if rule.ruleType == AlertRuleType.RISK_INDEX_INCREASE:
            min_risk = float(conditions.get("min_risk_score", 0.7))
            sql = text(
                f"SELECT COUNT(*) AS cnt, COALESCE(MAX(frp), 0.0) AS max_frp, MAX(acq_datetime) AS latest_dt "
                f"FROM hotspots WHERE acq_datetime >= :start_dt AND acq_datetime <= :end_dt {region_sql}"
            )
            row = self.session.execute(sql, base_params).mappings().one()
            cnt = int(row["cnt"] or 0)
            max_frp = float(row["max_frp"] or 0.0)
            env = self.session.exec(
                select(EnvironmentalRecord).order_by(col(EnvironmentalRecord.id).desc()).limit(1)
            ).first()
            temp = env.temperature if env and env.temperature is not None else 25.0
            hum = env.humidity if env and env.humidity is not None else 60.0
            wind = env.windSpeed if env and env.windSpeed is not None else 5.0

            # Índice compuesto normalizado [0, 1] basado en actividad, FRP y clima
            risk_score = min(
                1.0,
                0.35 * min(1.0, max_frp / 100.0)
                + 0.25 * min(1.0, cnt / 20.0)
                + 0.20 * min(1.0, max(0.0, (temp - 20.0) / 25.0))
                + 0.20 * min(1.0, max(0.0, (100.0 - hum) / 80.0)) * (1.0 + wind / 30.0),
            )
            if risk_score < min_risk or cnt == 0:
                return None
            return {
                "rule_id": rule.id,
                "dedup_key": f"rule:{rule.id}:risk:{rule.region or 'all'}:{bucket_tag}",
                "title": f"Incremento del índice de riesgo térmico ({risk_score:.2f})",
                "message": (
                    f"El índice compuesto de riesgo térmico alcanzó {risk_score:.2f} "
                    f"(umbral {min_risk:.2f}) con {cnt} detecciones satelitales recientes."
                ),
                "severity": rule.severity,
                "region": rule.region,
                "fire_cluster_id": cluster_id,
                "metadata": {"risk_score": round(risk_score, 4), "hotspots": cnt, "max_frp": max_frp},
                "acquisition_at": _parse_dt(row["latest_dt"]),
                "received_at": received_at,
                "processed_at": processed_at,
                "source": "NASA FIRMS + EnvironmentalRecord",
                "confidence_level": None,
            }

        return None
