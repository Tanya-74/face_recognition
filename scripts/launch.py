"""Start the app on a free port and open the browser once the server is answering.

Used by run_app.bat. By hand, from the project folder:  python scripts/launch.py
Port 8000 is tried first. If another program is using it, the next free port is taken.
"""
import os
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "127.0.0.1"          # this laptop only
PORTS = range(8000, 8020)


def open_port():
    """Return (socket, port) for the first free port. The socket stays open and is handed to the server."""
    for port in PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.3)
            if probe.connect_ex((HOST, port)) == 0:      # something already answers here
                continue
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((HOST, port))
        except OSError:                                  # taken, or reserved by Windows
            sock.close()
            continue
        return sock, port
    return None, None


def open_browser_when_ready(server, url):
    while not server.started:
        if server.should_exit:
            return
        time.sleep(0.2)
    print(f"\nThe app is running at {url}\nKeep this window open while you use it. Close it to stop the app.\n",
          flush=True)
    webbrowser.open(url + ("/?demo=1" if os.environ.get("FACE_DEMO") else ""))


def main():
    sys.path.insert(0, ROOT)
    os.chdir(ROOT)
    sock, port = open_port()
    if sock is None:
        print(f"Ports {PORTS[0]} to {PORTS[-1]} are all in use. Close other programs and try again.")
        return 1
    if port != PORTS[0]:
        print(f"Port {PORTS[0]} is used by another program, so the app will use port {port}.")
    print("Starting...", flush=True)
    server = uvicorn.Server(uvicorn.Config("app.main:app", host=HOST, port=port))
    threading.Thread(target=open_browser_when_ready, args=(server, f"http://{HOST}:{port}"), daemon=True).start()
    try:
        server.run(sockets=[sock])
    except KeyboardInterrupt:                            # Ctrl+C
        pass
    return 0 if server.started else 1


if __name__ == "__main__":
    sys.exit(main())
