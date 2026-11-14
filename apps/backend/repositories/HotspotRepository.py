from datetime import date, datetime, time

from sqlmodel import Session, select

try:
    from apps.backend.model.Hotspots import Hotspots
except ImportError:
    from model.Hotspots import Hotspots


def parse_datetime(value: str | datetime | date, is_end: bool = False) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.max if is_end else time.min)

    val_str = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(val_str)
        if len(val_str) == 10 and is_end:
            return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt
    except ValueError:
        pass

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            if fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d") and is_end:
                return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            return dt
        except ValueError:
            continue

    raise ValueError(
        f"Formato de fecha inválido: '{value}'. "
        "Formatos soportados: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO 8601."
    )


class HotspotRepository:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def serialize_hotspot(hotspot: Hotspots) -> dict:
        acq_dt = (
            hotspot.acq_datetime.strftime("%Y-%m-%d %H:%M:%S")
            if hotspot.acq_datetime
            else None
        )
        conf = hotspot.confidence
        if conf is not None:
            try:
                conf_val = float(conf)
                if conf_val.is_integer():
                    conf_val = int(conf_val)
            except (ValueError, TypeError):
                conf_val = conf
        else:
            conf_val = None

        return {
            "id": hotspot.id,
            "latitude": hotspot.latitude,
            "longitude": hotspot.longitude,
            "acq_datetime": acq_dt,
            "instrument": hotspot.instrument,
            "satellite": hotspot.satellite,
            "confidence_class": hotspot.confidence_class,
            "confidence": conf_val,
            "frp": hotspot.frp,
            "bright_mir": hotspot.bright_mir,
            "bright_tir": hotspot.bright_tir,
            "scan": hotspot.scan,
            "track": hotspot.track,
            "daynight": hotspot.daynight,
            "version": hotspot.version,
            "type": hotspot.type,
        }

    def get_hotspots(self, offset: int = 0, limit: int = 50) -> list[dict]:
        statement = select(Hotspots).offset(offset).limit(limit)
        results = self.session.exec(statement).all()
        return [self.serialize_hotspot(h) for h in results]

    def get_hostspot_by_dates(
        self,
        start_date: str | datetime | date,
        end_date: str | datetime | date,
        offset: int = 0,
        limit: int = 1000,
    ) -> list[dict]:
        start_dt = parse_datetime(start_date, is_end=False)
        end_dt = parse_datetime(end_date, is_end=True)

        statement = (
            select(Hotspots)
            .where(Hotspots.acq_datetime >= start_dt)
            .where(Hotspots.acq_datetime <= end_dt)
            .order_by(Hotspots.acq_datetime.desc())
            .offset(offset)
            .limit(limit)
        )
        results = self.session.exec(statement).all()
        return [self.serialize_hotspot(h) for h in results]

    def get_hostspot_by_location(
        self,
        latitude: float,
        longitude: float,
        radius: float = 0.05,
        offset: int = 0,
        limit: int = 1000,
    ) -> list[dict]:
        if radius > 0:
            statement = (
                select(Hotspots)
                .where(Hotspots.latitude >= (latitude - radius))
                .where(Hotspots.latitude <= (latitude + radius))
                .where(Hotspots.longitude >= (longitude - radius))
                .where(Hotspots.longitude <= (longitude + radius))
                .offset(offset)
                .limit(limit)
            )
        else:
            statement = (
                select(Hotspots)
                .where(Hotspots.latitude == latitude)
                .where(Hotspots.longitude == longitude)
                .offset(offset)
                .limit(limit)
            )

        results = self.session.exec(statement).all()
        return [self.serialize_hotspot(h) for h in results]
