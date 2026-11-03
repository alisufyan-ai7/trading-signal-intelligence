"""GUI-only private recovery passphrase prompt for Windows VPS RDP.

Avoid Python getpass/msvcrt clipboard quirks in Windows Console/PowerShell.
Tk Entry is masked, supports Ctrl+V and shows only character count/match.
The passphrase is never printed, logged, written to a file, passed to another
process, stored in Windows Credential Manager or persisted by this module.

A copied secret can remain in Windows/RDP clipboard/history independently of
this code; prefer password-manager auto-type when possible and clear clipboard
after use. No cloud, database, SDK or credential operations occur here.
"""
from __future__ import annotations

import sys

MINIMUM_LENGTH = 16
MAXIMUM_LENGTH = 1024


class PrivatePassphraseRejected(RuntimeError):
    """Fixed public error; never include the entered passphrase."""


def validate(mode: str, password: str, confirmation: str | None = None) -> str:
    if mode not in ("backup", "restore"):
        raise PrivatePassphraseRejected("unsupported passphrase operation")
    if (type(password) is not str
            or not MINIMUM_LENGTH <= len(password) <= MAXIMUM_LENGTH
            or "\x00" in password or "\r" in password or "\n" in password):
        raise PrivatePassphraseRejected("recovery passphrase length/input invalid")
    if mode == "backup" and (
        type(confirmation) is not str or confirmation != password
    ):
        raise PrivatePassphraseRejected("recovery passphrase confirmation mismatch")
    return password


def prompt(mode: str) -> str:
    """Blocking modal GUI; returns ephemeral characters to the same process.

    Strictly Windows+Tk; failure never falls back to console input, plaintext
    env variables, arguments, or clipboard logging. No SDK/source access.
    """
    if mode not in ("backup", "restore"):
        raise PrivatePassphraseRejected("unsupported passphrase operation")
    if sys.platform != "win32":
        raise PrivatePassphraseRejected("Windows RDP desktop required")
    try:
        import tkinter as tk
        from tkinter import ttk
        root = tk.Tk()
    except Exception:
        raise PrivatePassphraseRejected(
            "Windows graphical password dialog unavailable"
        ) from None
    answer: dict[str, str] = {}
    try:
        root.title("VowSig encrypted backup — recovery passphrase")
        root.geometry("560x255" if mode == "backup" else "560x206")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        panel = ttk.Frame(root, padding=(18, 16))
        panel.pack(fill="both", expand=True)
        ttk.Label(panel,
            text="Paste your private recovery passphrase (16+ characters)."
        ).pack(anchor="w")
        ttk.Label(panel,
            text="Input is hidden. Nothing is saved or shown in PowerShell."
        ).pack(anchor="w", pady=(0, 10))

        password_var = tk.StringVar()
        field = ttk.Entry(panel, textvariable=password_var,
                          show="*", width=65)
        field.pack(anchor="w", fill="x")

        confirm_var = tk.StringVar()
        if mode == "backup":
            ttk.Label(panel, text="Paste the identical passphrase again:"
                      ).pack(anchor="w", pady=(12, 2))
            ttk.Entry(panel, textvariable=confirm_var,
                      show="*", width=65).pack(anchor="w", fill="x")

        status_var = tk.StringVar()
        ttk.Label(panel, textvariable=status_var).pack(
            anchor="w", pady=(12, 6)
        )
        button_row = ttk.Frame(panel)
        button_row.pack(fill="x")

        def is_valid() -> bool:
            password = password_var.get()
            confirmation = confirm_var.get()
            try:
                validate(mode, password, confirmation)
                return True
            except PrivatePassphraseRejected:
                return False

        def redraw(*_args: object) -> None:
            length = len(password_var.get())
            if length < MINIMUM_LENGTH:
                message = f"Characters: {length} / {MINIMUM_LENGTH} minimum"
            elif length > MAXIMUM_LENGTH:
                message = "Passphrase exceeds maximum allowed length"
            elif mode == "backup" and confirm_var.get() != password_var.get():
                message = f"Characters: {length} — confirmation does not match"
            else:
                message = f"Characters: {length} — ready"
            status_var.set(message)
            submit_btn.configure(state=("normal" if is_valid() else "disabled"))

        def submit() -> None:
            try:
                password = validate(mode, password_var.get(), confirm_var.get())
            except PrivatePassphraseRejected:
                return
            # Best-effort clear current RDP clipboard after a successful
            # paste. Windows clipboard history and password-manager buffers
            # are outside this process and may retain earlier entries.
            try:
                root.clipboard_clear()
            except Exception:
                pass
            answer["passphrase"] = password
            root.quit()

        def cancel() -> None:
            root.quit()

        submit_btn = ttk.Button(button_row, text="Continue", command=submit)
        submit_btn.pack(side="left")
        ttk.Button(button_row, text="Cancel", command=cancel
                   ).pack(side="left", padx=10)

        password_var.trace_add("write", redraw)
        confirm_var.trace_add("write", redraw)
        root.protocol("WM_DELETE_WINDOW", cancel)
        redraw()
        field.focus_set()
        root.mainloop()
    except Exception:
        raise PrivatePassphraseRejected(
            "Windows graphical recovery password dialog failed"
        ) from None
    finally:
        root.destroy()
    if "passphrase" not in answer:
        raise PrivatePassphraseRejected("recovery passphrase entry cancelled")
    return answer["passphrase"]
