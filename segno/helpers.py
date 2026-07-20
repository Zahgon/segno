import re
import decimal
import segno
from urllib.parse import quote


_MECARD_ESCAPE = {
    ord('\\'): "\\\\",
    ord(';'): "\\;",
    ord(':'): "\\:",
    ord('"'): '\\"',
}


_VCARD_ESCAPE = {
    ord(','): '\\,',
    ord(';'): '\\;',
}


def _escape_mecard(s):
    pass


def _escape_vcard(s):
    pass


def make_wifi_data(ssid, password=None, security=None, hidden=False):
    pass


def make_wifi(ssid, password=None, security=None, hidden=False):
    pass


def make_mecard_data(name, reading=None, email=None, phone=None, videophone=None,
                     memo=None, nickname=None, birthday=None, url=None,
                     pobox=None, roomno=None, houseno=None, city=None,
                     prefecture=None, zipcode=None, country=None):
    pass


def make_mecard(name, reading=None, email=None, phone=None, videophone=None,
                memo=None, nickname=None, birthday=None, url=None, pobox=None,
                roomno=None, houseno=None, city=None, prefecture=None,
                zipcode=None, country=None):
    pass


_looks_like_datetime = re.compile(r'^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:(?:-?\d{2}:\d{2})|Z)?)?$').match


def make_vcard_data(name, displayname, email=None, phone=None, fax=None,
                    videophone=None, memo=None, nickname=None, birthday=None,
                    url=None, pobox=None, street=None, city=None, region=None,
                    zipcode=None, country=None, org=None, lat=None, lng=None,
                    source=None, rev=None, title=None, photo_uri=None,
                    cellphone=None, homephone=None, workphone=None):
    pass


def make_vcard(name, displayname, email=None, phone=None, fax=None,
               videophone=None, memo=None, nickname=None, birthday=None,
               url=None, pobox=None, street=None, city=None, region=None,
               zipcode=None, country=None, org=None, lat=None, lng=None,
               source=None, rev=None, title=None, photo_uri=None,
               cellphone=None, homephone=None, workphone=None):
    pass


def make_geo_data(lat, lng):
    pass


def make_geo(lat, lng):
    pass


def make_make_email_data(to, cc=None, bcc=None, subject=None, body=None):
    pass


def make_email(to, cc=None, bcc=None, subject=None, body=None):
    pass


def _make_epc_qr_data(name, iban, amount, text=None, reference=None, bic=None,
                      purpose=None, encoding=None):
    """\
    Validates the input and creates the data for an EPC QR Code.

    DOES NOT belong to the public API, kept separate from make_epc_qr to apply
    tests on the raw data.

    See :py:func:`make_epc_qr` for a description of the parameters.
    """
    encodings = ('utf-8', 'iso-8859-1', 'iso-8859-2', 'iso-8859-4',
                 'iso-8859-5', 'iso-8859-7', 'iso-8859-10', 'iso-8859-15')
    min_amount = decimal.Decimal('0.01')
    max_amount = decimal.Decimal('999999999.99')
    text = text.rstrip() if text else text
    reference = reference.rstrip() if reference else reference
    bic = bic.strip() if bic else bic
    name = name.strip() if name else name
    if encoding is not None:
        if isinstance(encoding, str):
            try:
                encoding = encodings.index(encoding.lower()) + 1
            except ValueError:
                raise ValueError(f'Invalid encoding "{encoding}", use one of {encodings}')
        elif not isinstance(encoding, int) or not 1 <= encoding <= len(encodings):
            raise ValueError(f'Invalid encoding number only 1 .. 8 are allowed, got "{encoding}"')
    if (not text and not reference) or (text and reference):
        raise ValueError('Either a text or a creditor reference (ISO 11649) must be provided')
    if text and not 0 < len(text) <= 140:
        raise ValueError(f'Invalid text, max. 140 characters are allowed, got "{len(text)}"')
    elif reference and not 0 < len(reference) <= 35:
        raise ValueError('Invalid creditor reference (ISO 11649), max. 35 characters are allowed, '
                         f'got "{len(reference)}"')
    if name is None or not 0 < len(name) <= 70:
        raise ValueError(f'Invalid name, max. 70 characters are allowed, got "{name}"')
    if iban is None or not 4 < len(iban) <= 34:
        raise ValueError(f'Invalid IBAN, min. 5 and max. 34 characters are allowed, got "{iban}"')
    if bic and len(bic) not in (8, 11):
        raise ValueError(f'Invalid BIC, should be 8 or 11 characters long, got "{bic}"')
    if purpose and len(purpose) != 4:
        raise ValueError(f'Invalid purpose, 4 characters are allowed, got "{purpose}"')
    amount = decimal.Decimal(amount)
    if not min_amount <= amount <= max_amount:
        raise ValueError(f'Invalid amount, must be in bigger or equal {min_amount} and less or equal {max_amount}')
    tmp_data = ['BCD',  # Service tag
                '002',  # Version
                '',  # character set (will be set later)
                'SCT',  # Identification
                bic or '',  # BIC
                name,  # Name of the recipient
                iban,  # IBAN
                f'EUR{amount:.2f}'.rstrip('0').rstrip('.'),  # Amount
                purpose or '',  # Purpose
                reference or '',  # Remittance
                ]
    if text:
        tmp_data.append(text)
    data = '\n'.join(tmp_data)
    charset = -1 if encoding is None else encoding
    if charset < 0:
        for idx, enc in enumerate(encodings[1:], start=2):
            try:
                data.encode(enc)
                charset = idx
                break
            except UnicodeEncodeError:
                pass
    if charset < 0:
        charset = 1  # Use UTF-8
    tmp_data[2] = str(charset)  # Set character set
    data = '\n'.join(tmp_data).encode(encodings[charset - 1])
    if len(data) > 331:  # pragma: no cover
        raise ValueError(f'Payload is too big: Max. 331 bytes allowed, got {len(data)} bytes')
    return data


def make_epc_qr(name, iban, amount, text=None, reference=None, bic=None,
                purpose=None, encoding=None):
    """\
    Creates and returns an European Payments Council Quick Response Code
    (EPC QR Code) version 002.

    The returned :py:class:`segno.QRCode` uses always the error correction level
    "M" and utilizes max. version 13 to fulfill the constraints of the EPC QR
    Code standard.

    .. note::

        Either the ``text`` or ``reference`` must be provided but not both

    .. note::

        Neither the IBAN, BIC, nor remittance reference number or any other
        information is validated (aside from checks regarding the allowed string
        lengths).

    :param str name: Name of the recipient.
    :param str iban: International Bank Account Number (IBAN)
    :param amount: The amount (in EUR) to transfer.
            The currency is always Euro, no other currencies are supported.
    :type amount: int, float, decimal.Decimal
    :param str text: Remittance Information (unstructured)
    :param str reference: Remittance Information (structured)
    :param str bic: Bank Identifier Code (BIC). Optional, only required
                for non-EEA countries.
    :param str purpose: SEPA purpose code.
    :param encoding: By default, this function tries to find the best,
                minimal encoding. If another encoding should be used, the encoding
                name or the encoding constant (an integer) can be provided:
                ``1``: "UTF-8", ``2``: "ISO 8859-1", ``3``: "ISO 8859-2",
                ``4``: "ISO 8859-4", ``5``: "ISO 8859-5", ``6``: "ISO 8859-7",
                ``7``: "ISO 8859-10", ``8``: "ISO 8859-15"

                The encoding is case-insensitive.
    :type encoding: str or int
    :rtype: segno.QRCode
    """
    qr = segno.make_qr(_make_epc_qr_data(name, iban, amount, text, reference,
                                         bic, purpose, encoding),
                       error='m', boost_error=False)
    if qr.version > 13:  # pragma: no cover
        raise ValueError(f'Invalid EPC QR Code, max. QR Code version 13 is allowed, got "{qr.designator}"')
    return qr
