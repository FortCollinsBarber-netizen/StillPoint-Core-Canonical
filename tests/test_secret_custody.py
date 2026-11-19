from __future__ import annotations

import os
import unittest
import tempfile
from unittest.mock import patch

from stillpoint.secret_custody import MAX_SECRET_BYTES, SecretCustodyError, read_secret


class SecretCustodyTests(unittest.TestCase):
    def test_inherited_fd_is_consumed_once_and_closed(self):
        read_fd,write_fd=os.pipe()
        os.write(write_fd,b"super-secret\n")
        os.close(write_fd)
        value=read_secret(
            {"SECRET_FD":str(read_fd)},
            value_name="SECRET_VALUE",
            fd_name="SECRET_FD",
        )
        self.assertEqual(value,"super-secret")
        with self.assertRaises(OSError):
            os.read(read_fd,1)

    def test_fd_takes_precedence_over_legacy_environment_value(self):
        read_fd,write_fd=os.pipe()
        os.write(write_fd,b"fd-secret")
        os.close(write_fd)
        value=read_secret(
            {"SECRET_FD":str(read_fd),"SECRET_VALUE":"environment-secret"},
            value_name="SECRET_VALUE",
            fd_name="SECRET_FD",
        )
        self.assertEqual(value,"fd-secret")

    def test_direct_environment_value_remains_compatibility_fallback(self):
        self.assertEqual(
            read_secret(
                {"SECRET_VALUE":"legacy-secret"},
                value_name="SECRET_VALUE",
                fd_name="SECRET_FD",
            ),
            "legacy-secret",
        )

    def test_invalid_fd_fails_closed(self):
        with self.assertRaises(SecretCustodyError):
            read_secret(
                {"SECRET_FD":"not-an-int"},
                value_name="SECRET_VALUE",
                fd_name="SECRET_FD",
            )


    def test_stalled_pipe_fails_closed_and_closes_fd(self):
        read_fd, write_fd = os.pipe()
        try:
            with patch("stillpoint.secret_custody.select.select", return_value=([], [], [])):
                with self.assertRaisesRegex(SecretCustodyError, "timed out"):
                    read_secret(
                        {"SECRET_FD": str(read_fd), "SECRET_VALUE": "legacy-fallback"},
                        value_name="SECRET_VALUE",
                        fd_name="SECRET_FD",
                    )
            with self.assertRaises(OSError):
                os.read(read_fd, 1)
        finally:
            os.close(write_fd)

    def test_oversized_descriptor_fails_closed_and_closes_fd(self):
        with tempfile.TemporaryFile() as source:
            source.write(b"x" * (MAX_SECRET_BYTES + 1))
            source.flush()
            source.seek(0)
            read_fd = os.dup(source.fileno())
            with self.assertRaisesRegex(SecretCustodyError, "exceeds maximum"):
                read_secret(
                    {"SECRET_FD": str(read_fd)},
                    value_name="SECRET_VALUE",
                    fd_name="SECRET_FD",
                )
            with self.assertRaises(OSError):
                os.read(read_fd, 1)

    def test_non_utf8_descriptor_is_rejected_with_bounded_error(self):
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"\\xff")
        os.close(write_fd)
        with self.assertRaisesRegex(SecretCustodyError, "must be UTF-8"):
            read_secret(
                {"SECRET_FD": str(read_fd)},
                value_name="SECRET_VALUE",
                fd_name="SECRET_FD",
            )

    def test_legacy_environment_fallback_is_size_bounded(self):
        with self.assertRaisesRegex(SecretCustodyError, "exceeds maximum"):
            read_secret(
                {"SECRET_VALUE": "x" * (MAX_SECRET_BYTES + 1)},
                value_name="SECRET_VALUE",
                fd_name="SECRET_FD",
            )


if __name__=="__main__":
    unittest.main()
