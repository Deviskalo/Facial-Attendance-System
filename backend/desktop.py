from __future__ import annotations

import asyncio
import socket
import threading
import time
from collections.abc import Callable
from typing import Protocol

_STARTUP_TIMEOUT_SECONDS = 60
_SHUTDOWN_TIMEOUT_SECONDS = 15


class UvicornServer(Protocol):
    started: bool
    should_exit: bool

    async def serve(self, sockets: list[socket.socket]) -> None: ...


class WebviewAPI(Protocol):
    def create_window(
        self,
        title: str,
        url: str,
        *,
        width: int,
        height: int,
        min_size: tuple[int, int],
        text_select: bool,
    ) -> object: ...

    def start(self, *, debug: bool) -> None: ...


def _create_local_listener() -> tuple[socket.socket, int]:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen(socket.SOMAXCONN)
        listener.setblocking(False)
        return listener, int(listener.getsockname()[1])
    except OSError:
        listener.close()
        raise


def _serve(server: UvicornServer, listener: socket.socket) -> None:
    asyncio.run(server.serve(sockets=[listener]))


def _wait_for_server(
    server: UvicornServer,
    thread: threading.Thread,
    startup_error: list[Exception],
    timeout: float = _STARTUP_TIMEOUT_SECONDS,
) -> None:
    deadline = time.monotonic() + timeout
    while not server.started and thread.is_alive():
        if time.monotonic() >= deadline:
            server.should_exit = True
            thread.join(_SHUTDOWN_TIMEOUT_SECONDS)
            raise TimeoutError(
                f"The local attendance server did not start within {timeout} seconds."
            )
        time.sleep(0.05)

    if startup_error:
        raise RuntimeError("The local attendance server failed to start.") from startup_error[0]
    if not server.started:
        raise RuntimeError("The local attendance server stopped before becoming ready.")


def run_desktop(
    webview_loader: Callable[[], WebviewAPI] | None = None,
) -> None:
    if webview_loader is None:
        try:
            import webview
        except ImportError as exc:
            raise RuntimeError(
                "Desktop support is not installed. Run desktop.bat to install it."
            ) from exc
        webview_module: WebviewAPI = webview
    else:
        webview_module = webview_loader()

    from backend.face_engine import ensure_models

    print("Checking local face-recognition model...")
    ensure_models()

    import uvicorn

    listener, port = _create_local_listener()
    server = uvicorn.Server(
        uvicorn.Config(
            "backend.main:app",
            host="127.0.0.1",
            port=port,
            log_level="info",
            access_log=False,
        )
    )
    startup_error: list[Exception] = []

    def serve() -> None:
        try:
            _serve(server, listener)
        except Exception as exc:
            startup_error.append(exc)

    server_thread = threading.Thread(
        target=serve, name="attendance-local-server", daemon=True
    )
    server_thread_started = False
    try:
        server_thread.start()
        server_thread_started = True
        _wait_for_server(server, server_thread, startup_error)
        url = f"http://127.0.0.1:{port}/kiosk"
        print(f"Opening desktop kiosk at {url}")
        webview_module.create_window(
            "Face Attendance Kiosk",
            url,
            width=1280,
            height=800,
            min_size=(960, 640),
            text_select=True,
        )
        webview_module.start(debug=False)
    finally:
        server.should_exit = True
        if server_thread_started:
            server_thread.join(_SHUTDOWN_TIMEOUT_SECONDS)
        listener.close()
        if server_thread_started and server_thread.is_alive():
            raise RuntimeError(
                "The local attendance server did not shut down cleanly."
            )


def main() -> None:
    run_desktop()


if __name__ == "__main__":
    main()
