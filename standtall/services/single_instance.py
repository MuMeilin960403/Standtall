"""Per-session single-instance endpoint for StandTall."""

from __future__ import annotations

import getpass
import hashlib
import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger(__name__)


def _socket_name() -> str:
    user = (getpass.getuser() or "user").encode("utf-8", "replace")
    digest = hashlib.sha256(user).hexdigest()[:10]
    return f"StandTall-Reminder-{digest}-v1"


class SingleInstance(QObject):
    activation_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server: QLocalServer | None = None
        self.is_primary = True
        name = _socket_name()

        probe = QLocalSocket(self)
        probe.connectToServer(name)
        if probe.waitForConnected(250):
            probe.write(b"show\n")
            probe.flush()
            probe.waitForBytesWritten(200)
            probe.disconnectFromServer()
            self.is_primary = False
            return

        QLocalServer.removeServer(name)
        server = QLocalServer(self)
        if server.listen(name):
            server.newConnection.connect(self._accept)
            self._server = server
        else:
            log.warning("Single-instance server unavailable: %s", server.errorString())

    def _accept(self) -> None:
        if self._server is None:
            return
        while self._server.hasPendingConnections():
            connection = self._server.nextPendingConnection()
            if connection is not None:
                connection.waitForReadyRead(80)
                try:
                    connection.readAll()
                except Exception:
                    pass
                connection.disconnectFromServer()
                connection.deleteLater()
        self.activation_requested.emit()

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None
