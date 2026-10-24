"""VowSig S02: read Windows Credential Manager GENERIC credentials (CurrentUser).

Keys are entered ONCE via Control Panel > Credential Manager > Windows
Credentials > Add a generic credential, NEVER via PowerShell, .env, arguments,
or GitHub. Windows Credential Manager uses Windows-managed encryption
associated with the signed-in Windows account (not off-host secret custody).

Only CredReadW for four exact, fixed target names. No enumeration, update,
export, console printing, SDK, cloud/network or import-time credential access.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Callable

TARGETS = {
    "aws_writer": "VowSig.S02.AWS.Writer.v1",
    "aws_reader": "VowSig.S02.AWS.Reader.v1",
    "b2_writer": "VowSig.S02.B2.Writer.v1",
    "b2_reader": "VowSig.S02.B2.Reader.v1",
}
BACKUP_ROLES = ("aws_writer", "aws_reader", "b2_writer", "b2_reader")
RESTORE_ROLES = ("aws_reader", "b2_reader")
GENERIC_TYPE = 1
MAX_BLOB = 2048


class WindowsVaultRejected(RuntimeError):
    """Sanitized error; never include the actual username or credential data."""


@dataclass(frozen=True, repr=False)
class ScopedSecret:
    access_id: str = field(repr=False)
    secret: str = field(repr=False)

    def __repr__(self) -> str:
        return "<ScopedSecret REDACTED>"

    def as_tuple(self) -> tuple[str, str]:
        return (self.access_id, self.secret)


class _CredentialW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.c_void_p),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def _printable(text: object) -> bool:
    return (
        type(text) is str
        and 8 <= len(text) <= 256
        and all(33 <= ord(char) <= 126 for char in text)
    )


def _decode_blob(data: bytes) -> str:
    # Windows Credential Manager GUI stores Generic passwords as UTF-16LE.
    # Some API clients store UTF-8 instead. Support both but accept only
    # printable ASCII AWS/B2 key material; never trim or normalize a key.
    if type(data) is not bytes or not 0 < len(data) <= MAX_BLOB:
        raise WindowsVaultRejected("invalid Windows credential data")
    possibilities: list[str] = []
    if len(data) % 2 == 0:
        try:
            possibilities.append(data.decode("utf-16-le"))
        except UnicodeError:
            pass
    try:
        possibilities.append(data.decode("utf-8"))
    except UnicodeError:
        pass
    for value in possibilities:
        if _printable(value):
            return value
    raise WindowsVaultRejected("Windows credential secret encoding invalid")


def _read_generic(target: str) -> ScopedSecret:
    if sys.platform != "win32":
        raise WindowsVaultRejected("Windows Credential Manager requires a Windows session")
    if target not in TARGETS.values():
        raise WindowsVaultRejected("unapproved Windows credential target")
    try:
        library = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        pointer = ctypes.POINTER(_CredentialW)()
        library.CredReadW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(_CredentialW)),
        ]
        library.CredReadW.restype = wintypes.BOOL
        library.CredFree.argtypes = [ctypes.c_void_p]
        library.CredFree.restype = None
        if not library.CredReadW(target, GENERIC_TYPE, 0, ctypes.byref(pointer)):
            raise WindowsVaultRejected("required Windows credential entry missing")
        try:
            record = pointer.contents
            if (record.Type != GENERIC_TYPE
                    or not _printable(record.UserName)
                    or not 0 < record.CredentialBlobSize <= MAX_BLOB
                    or not record.CredentialBlob):
                raise WindowsVaultRejected("Windows generic credential invalid")
            value = ctypes.string_at(record.CredentialBlob, record.CredentialBlobSize)
            return ScopedSecret(record.UserName, _decode_blob(value))
        finally:
            library.CredFree(ctypes.cast(pointer, ctypes.c_void_p))
    except WindowsVaultRejected:
        raise
    except Exception:
        raise WindowsVaultRejected("Windows Credential Manager read failed") from None


def load_credentials(
    mode: str, *,
    lookup: Callable[[str], ScopedSecret] | None = None,
) -> tuple[tuple[str, str], ...]:
    """Exact fixed roles, for the caller's Windows logon account only.

    Injected lookup is test-only; production CLI never accepts a lookup option.
    """
    if mode not in ("backup", "restore"):
        raise WindowsVaultRejected("unsupported cloud credential mode")
    read = _read_generic if lookup is None else lookup
    if not callable(read):
        raise WindowsVaultRejected("credential reader unavailable")
    roles = BACKUP_ROLES if mode == "backup" else RESTORE_ROLES
    values: list[tuple[str, str]] = []
    try:
        for role in roles:
            credential = read(TARGETS[role])
            if (type(credential) is not ScopedSecret
                    or not _printable(credential.access_id)
                    or not _printable(credential.secret)):
                raise WindowsVaultRejected("scoped Windows credential malformed")
            values.append(credential.as_tuple())
        if len({pair[0] for pair in values}) != len(values):
            raise WindowsVaultRejected("separate cloud role identities required")
        return tuple(values)
    except WindowsVaultRejected:
        raise
    except Exception:
        raise WindowsVaultRejected("scoped Windows credential retrieval failed") from None


def credential_status(*, lookup: Callable[[str], ScopedSecret] | None = None) -> dict:
    """Fixed target presence check, no usernames/passwords in output."""
    read = _read_generic if lookup is None else lookup
    available = {}
    for role in BACKUP_ROLES:
        try:
            credential = read(TARGETS[role])
            available[role] = (
                type(credential) is ScopedSecret
                and _printable(credential.access_id)
                and _printable(credential.secret)
            )
        except Exception:
            available[role] = False
    return {
        "status": "WINDOWS_CREDENTIAL_MANAGER_SCOPED_CHECK",
        "current_windows_account_only": True,
        "backup_roles_ready": all(available.values()),
        "restore_roles_ready": available["aws_reader"] and available["b2_reader"],
        "roles": available,
        "network_requests": 0,
    }
