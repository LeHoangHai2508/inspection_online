from __future__ import annotations

import json
import mimetypes
import uuid
from urllib import error, parse, request


def api_get(base_url: str, path: str) -> dict:
    url = _join(base_url, path)
    with request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def api_post_form(base_url: str, path: str, data: dict[str, str]) -> dict:
    payload = parse.urlencode(data).encode("utf-8")
    req = request.Request(_join(base_url, path), data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    return _load_json(req)


def api_put_json(base_url: str, path: str, payload: dict) -> dict:
    req = request.Request(
        _join(base_url, path),
        data=json.dumps(payload).encode("utf-8"),
        method="PUT",
    )
    req.add_header("Content-Type", "application/json")
    return _load_json(req)


def api_post_multipart(
    base_url: str,
    path: str,
    data: dict[str, str],
    files: dict[str, tuple[str, bytes, str]],
) -> dict:
    boundary = f"----codex-{uuid.uuid4().hex}"
    body = bytearray()

    for key, value in data.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode(
                "utf-8"
            )
        )

    for field_name, (filename, content, media_type) in files.items():
        guessed_type = media_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
                f"Content-Type: {guessed_type}\r\n\r\n"
            ).encode("utf-8")
        )
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    req = request.Request(_join(base_url, path), data=bytes(body), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    return _load_json(req)


def _load_json(req: request.Request) -> dict:
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:  # pragma: no cover - network path
        payload = exc.read().decode("utf-8", errors="ignore")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            raise RuntimeError(payload or str(exc)) from exc
        raise RuntimeError(data.get("detail", payload)) from exc


def _join(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path
