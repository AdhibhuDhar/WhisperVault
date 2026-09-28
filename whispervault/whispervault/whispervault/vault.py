"""Encrypted mapping vault (Fix #7, R11, R21).

Windows  : DPAPI (CryptProtectData) - key is tied to the user's Windows account.
Elsewhere: passphrase-derived key (scrypt + AES-GCM) - used for development,
           CI, and as the portable backup format (R21).

Security boundary (R11): DPAPI is only as strong as the Windows account it is
bound to - the same threat model as Windows Credential Manager.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Protocol

MAGIC_PASS = b"WVP1"
MAGIC_DPAPI = b"WVD1"


class Protector(Protocol):
    def encrypt(self, data: bytes) -> bytes: ...
    def decrypt(self, blob: bytes) -> bytes: ...


class PassphraseProtector:
    def __init__(self, passphrase: str):
        if not passphrase:
            raise ValueError("passphrase must not be empty")
        self._pw = passphrase.encode("utf-8")

    def _key(self, salt: bytes) -> bytes:
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

        return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(self._pw)

    def encrypt(self, data: bytes) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        salt, nonce = os.urandom(16), os.urandom(12)
        return MAGIC_PASS + salt + nonce + AESGCM(self._key(salt)).encrypt(nonce, data, MAGIC_PASS)

    def decrypt(self, blob: bytes) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if not blob.startswith(MAGIC_PASS):
            raise ValueError("not a passphrase-protected vault")
        salt, nonce, ct = blob[4:20], blob[20:32], blob[32:]
        return AESGCM(self._key(salt)).decrypt(nonce, ct, MAGIC_PASS)  # raises on wrong key


class DpapiProtector:
    """Windows DPAPI via ctypes (no extra dependency, works on ARM64 Windows)."""

    def __init__(self, entropy: bytes = b"whispervault-v1"):
        if sys.platform != "win32":
            raise RuntimeError("DPAPI is only available on Windows")
        self._entropy = entropy

    @staticmethod
    def _apis():
        import ctypes
        from ctypes import wintypes

        class BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
        argtypes = [ctypes.POINTER(BLOB), wintypes.LPCWSTR, ctypes.POINTER(BLOB),
                    ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(BLOB)]
        crypt32.CryptProtectData.argtypes = argtypes
        crypt32.CryptProtectData.restype = wintypes.BOOL
        u_args = [ctypes.POINTER(BLOB), ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(BLOB),
                  ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(BLOB)]
        crypt32.CryptUnprotectData.argtypes = u_args
        crypt32.CryptUnprotectData.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        return ctypes, BLOB, crypt32, kernel32

    def _blob(self, BLOB, ctypes, data: bytes):
        buf = ctypes.create_string_buffer(data, len(data))
        return BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf

    def _call(self, protect: bool, data: bytes) -> bytes:
        ctypes, BLOB, crypt32, kernel32 = self._apis()
        b_in, _k1 = self._blob(BLOB, ctypes, data)
        b_ent, _k2 = self._blob(BLOB, ctypes, self._entropy)
        b_out = BLOB()
        if protect:
            ok = crypt32.CryptProtectData(ctypes.byref(b_in), "WhisperVault", ctypes.byref(b_ent),
                                          None, None, 0, ctypes.byref(b_out))
        else:
            ok = crypt32.CryptUnprotectData(ctypes.byref(b_in), None, ctypes.byref(b_ent),
                                            None, None, 0, ctypes.byref(b_out))
        if not ok:
            raise OSError(f"DPAPI call failed (error {ctypes.GetLastError()})")
        try:
            return ctypes.string_at(b_out.pbData, b_out.cbData)
        finally:
            kernel32.LocalFree(ctypes.cast(b_out.pbData, ctypes.c_void_p))

    def encrypt(self, data: bytes) -> bytes:
        return MAGIC_DPAPI + self._call(True, data)

    def decrypt(self, blob: bytes) -> bytes:
        if not blob.startswith(MAGIC_DPAPI):
            raise ValueError("not a DPAPI-protected vault")
        return self._call(False, blob[4:])


def default_protector(passphrase: str | None = None) -> Protector:
    if passphrase:
        return PassphraseProtector(passphrase)
    if sys.platform == "win32":
        return DpapiProtector()
    raise RuntimeError("Off Windows a passphrase is required "
                       "(set WHISPERVAULT_PASSPHRASE or pass --passphrase-env).")


def save_vault(path: str | Path, mapping: dict, protector: Protector) -> None:
    Path(path).write_bytes(protector.encrypt(json.dumps(mapping).encode("utf-8")))


def load_vault(path: str | Path, protector: Protector) -> dict:
    return json.loads(protector.decrypt(Path(path).read_bytes()).decode("utf-8"))


def export_backup(vault_path: str | Path, backup_path: str | Path,
                  source: Protector, passphrase: str) -> None:
    """R21: re-encrypt a DPAPI vault under a passphrase so it survives a lost
    laptop or a reset Windows profile."""
    mapping = load_vault(vault_path, source)
    save_vault(backup_path, mapping, PassphraseProtector(passphrase))
