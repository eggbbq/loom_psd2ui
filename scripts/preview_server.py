"""Serve the local example; bind before opening browser and stop with Ctrl+C."""
import argparse
import errno
import functools
import http.server
import sys
import webbrowser
from pathlib import Path


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_request(self, code="-", size="-"):
        if isinstance(code, int) and code >= 400:
            super().log_request(code, size)


def main():
    parser = argparse.ArgumentParser(description="PSD2UI 本地 LayaAir 3.4.1 预览")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true", help="仅打印地址，不自动打开浏览器")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("端口必须在 0–65535 之间")
    root = Path(__file__).resolve().parents[1]
    handler = functools.partial(Handler, directory=str(root))
    for port in range(args.port, min(args.port + 11, 65536)):
        try:
            server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
            break
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
    else:
        raise SystemExit("附近端口均已占用，请用 --port 指定其他端口")
    actual = server.server_address[1]
    url = f"http://127.0.0.1:{actual}/laya-project/release/web/"
    if actual != args.port and args.port != 0:
        print(f"端口 {args.port} 已占用，已使用 {actual}。", flush=True)
    print(f"\nPSD2UI 已启动：{url}\n按 Ctrl+C 停止服务。\n", flush=True)
    if not args.no_open:
        if not webbrowser.open(url):
            print("无法自动打开浏览器，请复制上面的地址。", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPSD2UI 预览已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

