from __future__ import annotations

import os
import unittest

from stillpoint.secret_custody import SecretCustodyError, read_secret


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


if __name__=="__main__":
    unittest.main()
