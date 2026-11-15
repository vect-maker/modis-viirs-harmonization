from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any

import httpx
from fastapi import WebSocket

logger = logging.getLogger("firms.notifications")


class WebSocketConnectionManager:
    """Gestor desacoplado de conexiones WebSocket para alertas en tiempo real."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast_json(self, payload: dict[str, Any]) -> int:
        sent = 0
        disconnected: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
                sent += 1
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)
        return sent


ws_manager = WebSocketConnectionManager()


class NotificationService:
    """
    Servicio desacoplado de notificaciones para correo electrónico, WebSockets,
    registro interno e integraciones externas (webhooks). Solo envía por un canal
    cuando existe configuración válida.
    """

    def __init__(self, websocket_manager: WebSocketConnectionManager = ws_manager) -> None:
        self.ws_manager = websocket_manager
        self.smtp_host = os.getenv("SMTP_HOST", "").strip()
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "").strip()
        self.smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
        self.email_from = os.getenv("ALERT_EMAIL_FROM", "").strip()
        self.email_to = [
            addr.strip()
            for addr in os.getenv("ALERT_EMAIL_TO", "").split(",")
            if addr.strip()
        ]
        self.webhook_url = os.getenv("ALERT_WEBHOOK_URL", "").strip()

    @property
    def email_configured(self) -> bool:
        return bool(self.smtp_host and self.email_from and self.email_to)

    @property
    def webhook_configured(self) -> bool:
        return bool(self.webhook_url.startswith(("http://", "https://")))

    async def notify(self, alert_payload: dict[str, Any]) -> dict[str, str]:
        outcomes: dict[str, str] = {}

        # 1. Notificación interna (siempre activa vía logging estructurado)
        logger.info(
            "ALERTA [%s] (%s): %s",
            alert_payload.get("severity"),
            alert_payload.get("source"),
            alert_payload.get("title"),
        )
        outcomes["internal"] = "logged"

        # 2. WebSocket (si hay clientes conectados)
        try:
            sent_ws = await self.ws_manager.broadcast_json(
                {"type": "early_warning_alert", "data": alert_payload}
            )
            outcomes["websocket"] = f"sent:{sent_ws}" if sent_ws > 0 else "no_clients"
        except Exception as exc:
            logger.warning("Error enviando alerta por WebSocket: %s", exc)
            outcomes["websocket"] = "error"

        # 3. Correo electrónico (solo si SMTP está configurado)
        if self.email_configured:
            try:
                self._send_email(alert_payload)
                outcomes["email"] = "sent"
            except Exception as exc:
                logger.warning("Error enviando alerta por correo: %s", exc)
                outcomes["email"] = "error"
        else:
            outcomes["email"] = "skipped_unconfigured"

        # 4. Integración externa webhook (solo si ALERT_WEBHOOK_URL es válido)
        if self.webhook_configured:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(self.webhook_url, json=alert_payload)
                    outcomes["webhook"] = f"http_{resp.status_code}"
            except Exception as exc:
                logger.warning("Error enviando alerta a webhook externo: %s", exc)
                outcomes["webhook"] = "error"
        else:
            outcomes["webhook"] = "skipped_unconfigured"

        return outcomes

    def _send_email(self, alert_payload: dict[str, Any]) -> None:
        msg = EmailMessage()
        msg["Subject"] = f"[NASA FIRMS Early Warning - {alert_payload.get('severity')}] {alert_payload.get('title')}"
        msg["From"] = self.email_from
        msg["To"] = ", ".join(self.email_to)
        msg.set_content(
            f"{alert_payload.get('message', '')}\n\n"
            f"Región: {alert_payload.get('region') or 'Global'}\n"
            f"Fuente: {alert_payload.get('source')}\n"
            f"Confianza: {alert_payload.get('confidenceLevel') or 'N/D'}\n"
            f"Adquisición: {alert_payload.get('acquisitionAt')}\n"
            f"Procesamiento: {alert_payload.get('processedAt')}\n"
        )
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as smtp:
            if self.smtp_user and self.smtp_password:
                smtp.starttls()
                smtp.login(self.smtp_user, self.smtp_password)
            smtp.send_message(msg)
