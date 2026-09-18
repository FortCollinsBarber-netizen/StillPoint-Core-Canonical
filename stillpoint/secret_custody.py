from __future__ import annotations

import os
from typing import Mapping


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
            chunks: list[bytes] = []
            while True:
                part = os.read(fd, 4096)
                if not part:
                    break
                chunks.append(part)
        except OSError as exc:
            raise SecretCustodyError(f"cannot read secret from {fd_name}") from exc
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
        secret = b"".join(chunks).decode("utf-8").strip()
        if not secret:
            raise SecretCustodyError(f"{fd_name} produced an empty secret")
        return secret

    # Compatibility for interactive/test callers. Production wrappers do not
    # use this path.
    direct = str(env.get(value_name) or "").strip()
    return direct
