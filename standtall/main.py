"""StandTall process entry point."""

from __future__ import annotations

import argparse
import ctypes
import logging
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from standtall import __version__
from standtall.app import StandTallApp, configure_application
from standtall.services.logging_setup import setup_logging
from standtall.services.paths import data_dir
from standtall.services.single_instance import SingleInstance
from standtall.ui.icons import make_icon

log = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="坐直 · 可调时间的坐姿提醒")
    parser.add_argument("--smoke-test", action="store_true", help="启动后自动退出，用于打包验证")
    parser.add_argument("--version", action="version", version=__version__)
    return parser.parse_args(argv)


def _prepare_smoke_dir() -> Path:
    if not os.environ.get("STANDTALL_DATA_DIR"):
        os.environ["STANDTALL_DATA_DIR"] = tempfile.mkdtemp(prefix="standtall-smoke-")
    return data_dir()


def _install_exception_hook(smoke_test: bool) -> None:
    def hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        if smoke_test:
            print(f"SMOKE_FAILED: {exc_type.__name__}: {exc_value}", file=sys.stderr, flush=True)
            QApplication.exit(2)
            return
        QMessageBox.critical(
            None,
            "坐直遇到了问题",
            "程序遇到了未预期的错误，需要重新启动。\n"
            "详细信息已写入本地日志。",
        )

    sys.excepthook = hook


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("StandTall.Desktop.1")
    except Exception:
        pass


def _start_smoke_exit(app: QApplication) -> None:
    marker = data_dir() / "smoke-ok.txt"

    def finish() -> None:
        try:
            marker.write_text(
                f"ok\nversion={__version__}\npid={os.getpid()}\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        print("SMOKE_OK", flush=True)
        app.exit(0)

    QTimer.singleShot(1500, finish)
    QTimer.singleShot(15_000, lambda: app.exit(4))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.smoke_test:
        _prepare_smoke_dir()
    setup_logging()
    _set_windows_app_id()

    app = QApplication([sys.argv[0]])
    app.setApplicationName("StandTall")
    app.setApplicationDisplayName("坐直")
    app.setOrganizationName("StandTall")
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(make_icon("active"))
    configure_application(app)
    _install_exception_hook(args.smoke_test)

    instance: SingleInstance | None = None
    if not args.smoke_test:
        instance = SingleInstance()
        if not instance.is_primary:
            instance.close()
            return 0

    controller: StandTallApp | None = None
    try:
        controller = StandTallApp(app, smoke_test=args.smoke_test)
        if instance is not None:
            instance.activation_requested.connect(controller.show_main)
        if args.smoke_test:
            _start_smoke_exit(app)
        return app.exec()
    except Exception as exc:
        log.critical("Startup failed", exc_info=True)
        if args.smoke_test:
            print(f"SMOKE_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            return 2
        QMessageBox.critical(
            None,
            "坐直没有启动成功",
            "启动时遇到了问题。\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            "详细信息已写入本地日志。",
        )
        return 1
    finally:
        if instance is not None:
            instance.close()


if __name__ == "__main__":
    raise SystemExit(main())
