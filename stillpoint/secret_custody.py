from __future__ import annotations

import os
import select
import time
from typing import Mapping


MAX_SECRET_BYTES = 64 * 1024
SECRET_READ_TIMEOUT_SECONDS = 5.0


class SecretCustodyError(RuntimeError):
    pass


def read_secret(
    env: Mapping[str, str],
    *,
    value_name: str,
    fd_name: str,
) -> str:
    """Read a secret from an inherited FD, with direct env only as legacy fallback.

    Production launch wrappers pass only the descriptor number through the
    environment. The descriptor is consumed once and closed immediately.
    """

    fd_raw = str(env.get(fd_name) or "").strip()
    if fd_raw:
        try:
            fd = int(fd_raw)
        except ValueError as exc:
            raise SecretCustodyError(f"{fd_name} must be an integer file descriptor") from exc
        if fd < 0:
            raise SecretCustodyError(f"{fd_name} must be non-negative")
        try:
            # A descriptor is not necessarily a finished, finite file. A pipe
            # whose writer never closes would previously block startup forever.
            deadline = time.monotonic() + SECRET_READ_TIMEOUT_SECONDS
            chunks: list[bytes] = []
            total = 0
            while True:
                remaining_seconds = deadline - time.monotonic()
                if remaining_seconds <= 0:
                    raise SecretCustodyError(f"{fd_name} secret read timed out")
                readable, _, _ = select.select([fd], [], [], remaining_seconds)
                if not readable:
                    raise SecretCustodyError(f"{fd_name} secret read timed out")
                # Read one extra byte to detect oversized inputs without
                # buffering an arbitrary amount of credential material.
                part = os.read(fd, min(4096, MAX_SECRET_BYTES + 1 - total))
                if not part:
                    break
                total += len(part)
                if total > MAX_SECRET_BYTES:
                    raise SecretCustodyError(f"{fd_name} secret exceeds maximum size")
                chunks.append(part)
        except (OSError, ValueError) as exc:
            raise SecretCustodyError(f"cannot read secret from {fd_name}") from exc
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            secret = b"".join(chunks).decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise SecretCustodyError(f"{fd_name} secret must be UTF-8") from exc
        if not secret:
            raise SecretCustodyError(f"{fd_name} produced an empty secret")
        return secret

    # Compatibility for interactive/test callers. Production wrappers do not
    # use this path.
    direct = str(env.get(value_name) or "").strip()
    if len(direct.encode("utf-8")) > MAX_SECRET_BYTES:
        raise SecretCustodyError(f"{value_name} secret exceeds maximum size")
    return direct
