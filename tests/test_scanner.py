"""Tests for the UPS scanner."""

from unittest.mock import patch

from nut_up.scanner import parse_nut_scanner_output, scan_usb

SINGLE_DEVICE = """\
[nutdev1]
\tdriver = "usbhid-ups"
\tport = "auto"
\tvendorid = "051D"
\tproductid = "0002"
\tproduct = "Back-UPS XS 1500M"
\tserial = "1234567890"
\tbus = "001"
"""

MULTIPLE_DEVICES = """\
[nutdev1]
\tdriver = "usbhid-ups"
\tport = "auto"
\tproduct = "Back-UPS XS 1500M"

[nutdev2]
\tdriver = "blazer_usb"
\tport = "auto"
\tproduct = "Smart-UPS 750"
"""


def test_parse_single_device() -> None:
    devices = parse_nut_scanner_output(SINGLE_DEVICE)
    assert len(devices) == 1
    dev = devices[0]
    assert dev["name"] == "nutdev1"
    assert dev["driver"] == "usbhid-ups"
    assert dev["port"] == "auto"
    assert dev["desc"] == "Back-UPS XS 1500M"
    assert dev["extra"]["vendorid"] == "051D"
    assert dev["extra"]["productid"] == "0002"
    assert dev["extra"]["serial"] == "1234567890"
    assert dev["extra"]["bus"] == "001"


def test_parse_empty() -> None:
    devices = parse_nut_scanner_output("")
    assert devices == []


def test_parse_multiple_devices() -> None:
    devices = parse_nut_scanner_output(MULTIPLE_DEVICES)
    assert len(devices) == 2
    assert devices[0]["name"] == "nutdev1"
    assert devices[0]["driver"] == "usbhid-ups"
    assert devices[1]["name"] == "nutdev2"
    assert devices[1]["driver"] == "blazer_usb"
    assert devices[1]["desc"] == "Smart-UPS 750"


def test_scan_usb_calls_nut_scanner() -> None:
    mock_result = type("Result", (), {"returncode": 0, "stdout": SINGLE_DEVICE, "stderr": ""})()
    with patch("nut_up.scanner.subprocess.run", return_value=mock_result) as mock_run:
        devices = scan_usb()
        mock_run.assert_called_once_with(
            ["nut-scanner", "-U"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert len(devices) == 1
        assert devices[0]["driver"] == "usbhid-ups"


def test_scan_usb_not_installed() -> None:
    with patch("nut_up.scanner.subprocess.run", side_effect=FileNotFoundError):
        devices = scan_usb()
        assert devices == []


def test_scan_usb_nonzero_exit() -> None:
    mock_result = type("Result", (), {"returncode": 1, "stdout": "", "stderr": "error"})()
    with patch("nut_up.scanner.subprocess.run", return_value=mock_result):
        devices = scan_usb()
        assert devices == []


def test_scan_usb_timeout() -> None:
    import subprocess

    with patch(
        "nut_up.scanner.subprocess.run", side_effect=subprocess.TimeoutExpired("nut-scanner", 30)
    ):
        devices = scan_usb()
        assert devices == []
