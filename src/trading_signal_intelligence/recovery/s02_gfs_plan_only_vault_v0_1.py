"""Separate Windows Generic vault target for NON-DESTRUCTIVE GFS plan encryption.

Only the approved plan-encryption passphrase is read; never writer/delete
credentials, signing keys, arbitrary targets or prompt/command-line secrets.
No credential access at import time.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Callable

from . import windows_credential_manager_v0_1 as existing

PLAN_TARGET = "VowSig.S02.GFS.Plan.Passphrase.v1"
PLAN_USERNAME = "VowSigGFSPlanner"


class GfsPlannerVaultHold(RuntimeError):
    """Safe status; no credential data in exception text."""


def read_plan_passphrase(*, lookup: Callable[[], str] | None = None) -> str:
    """Owner provisions a distinct Generic Credential in the task logon account."""
    if lookup is not None:
        if not callable(lookup):
            raise GfsPlannerVaultHold("untrusted plan secret reader")
        try:
            secret = lookup()
        except Exception:
            raise GfsPlannerVaultHold("plan credential unavailable") from None
    else:
        if sys.platform != "win32":
            raise GfsPlannerVaultHold("Windows owner vault required")
        pointer = ctypes.POINTER(existing._CredentialW)()
        try:
            dll = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
            dll.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                ctypes.POINTER(ctypes.POINTER(existing._CredentialW))]
            dll.CredReadW.restype = wintypes.BOOL
            dll.CredFree.argtypes = [ctypes.c_void_p]
            dll.CredFree.restype = None
            if not dll.CredReadW(PLAN_TARGET, existing.GENERIC_TYPE, 0, ctypes.byref(pointer)):
                raise GfsPlannerVaultHold("independent plan credential missing")
            try:
                row = pointer.contents
                if (row.Type != existing.GENERIC_TYPE
                        or row.UserName != PLAN_USERNAME
                        or not 0 < row.CredentialBlobSize <= existing.MAX_BLOB
                        or not row.CredentialBlob):
                    raise GfsPlannerVaultHold("independent plan credential malformed")
                raw = ctypes.string_at(row.CredentialBlob, row.CredentialBlobSize)
                secret = existing._decode_blob(raw, allow_recovery_phrase=True)
            finally:
                dll.CredFree(ctypes.cast(pointer, ctypes.c_void_p))
        except GfsPlannerVaultHold:
            raise
        except Exception:
            raise GfsPlannerVaultHold("independent Windows plan vault access denied") from None
    if (type(secret) is not str or not 16 <= len(secret) <= 256
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in secret)):
        raise GfsPlannerVaultHold("plan passphrase invalid")
    return secret
