"""QR-code generation for contracts.

Two entry points:

* ``make_qr_png(text)`` — returns raw PNG bytes. Used when the caller
  wants to attach the QR directly to ``Contract.qr`` (ImageField).

* ``make_qr_data_uri(text)`` — returns a ``data:image/png;base64,…`` URI
  suitable for embedding into the HTML template before WeasyPrint
  converts it to PDF. WeasyPrint resolves data URIs natively, so this
  avoids temp-file juggling.

Payload is caller-specified: typically the contract's public URL or a
small JSON blob with ``{contract_number, total_amount}``. Kept minimal
so that scanned codes stay readable on cheap phones.
"""
from __future__ import annotations

import base64
from io import BytesIO

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def make_qr_png(text: str, *, box_size: int = 6, border: int = 2) -> bytes:
    """Render `text` as a QR code, return PNG bytes."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_qr_data_uri(text: str, **kwargs) -> str:
    """Same payload wrapped as a `data:image/png;base64,…` URI."""
    png = make_qr_png(text, **kwargs)
    b64 = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64}"
