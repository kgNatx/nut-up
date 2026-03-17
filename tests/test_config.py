"""Tests for NUT config file generation."""

from pathlib import Path

from nut_up.config import HEADER, NUTConfigReader, NUTConfigWriter


def test_write_nut_conf_standalone(tmp_path: Path) -> None:
    writer = NUTConfigWriter(str(tmp_path))
    writer.write_nut_conf("standalone")
    content = (tmp_path / "nut.conf").read_text()
    assert content.startswith(HEADER)
    assert "MODE=standalone" in content


def test_write_nut_conf_netserver(tmp_path: Path) -> None:
    writer = NUTConfigWriter(str(tmp_path))
    writer.write_nut_conf("netserver")
    content = (tmp_path / "nut.conf").read_text()
    assert "MODE=netserver" in content


def test_write_nut_conf_netclient(tmp_path: Path) -> None:
    writer = NUTConfigWriter(str(tmp_path))
    writer.write_nut_conf("netclient")
    content = (tmp_path / "nut.conf").read_text()
    assert "MODE=netclient" in content


def test_write_ups_conf_single(tmp_path: Path) -> None:
    writer = NUTConfigWriter(str(tmp_path))
    ups_list = [
        {
            "name": "myups",
            "driver": "usbhid-ups",
            "port": "auto",
            "desc": "APC Back-UPS 1500",
        }
    ]
    writer.write_ups_conf(ups_list)
    content = (tmp_path / "ups.conf").read_text()
    assert content.startswith(HEADER)
    assert "[myups]" in content
    assert "driver = usbhid-ups" in content
    assert "port = auto" in content
    assert 'desc = "APC Back-UPS 1500"' in content


def test_write_ups_conf_with_extras(tmp_path: Path) -> None:
    writer = NUTConfigWriter(str(tmp_path))
    ups_list = [
        {
            "name": "myups",
            "driver": "usbhid-ups",
            "port": "auto",
            "desc": "APC UPS",
            "extra": {"vendorid": "051d", "pollinterval": "15"},
        }
    ]
    writer.write_ups_conf(ups_list)
    content = (tmp_path / "ups.conf").read_text()
    assert 'vendorid = "051d"' in content
    assert 'pollinterval = "15"' in content


def test_write_upsd_conf_listen(tmp_path: Path) -> None:
    writer = NUTConfigWriter(str(tmp_path))
    writer.write_upsd_conf(["0.0.0.0", "::1"], port=3493)
    content = (tmp_path / "upsd.conf").read_text()
    assert content.startswith(HEADER)
    assert "LISTEN 0.0.0.0 3493" in content
    assert "LISTEN ::1 3493" in content
    assert "MAXAGE 15" in content


def test_write_upsd_users(tmp_path: Path) -> None:
    writer = NUTConfigWriter(str(tmp_path))
    writer.write_upsd_users("adminpass", "monpass")
    content = (tmp_path / "upsd.users").read_text()
    assert content.startswith(HEADER)
    assert "[admin]" in content
    assert "password = adminpass" in content
    assert "actions = SET FSD" in content
    assert "instcmds = ALL" in content
    assert "[upsmon_primary]" in content
    assert "password = monpass" in content
    assert "upsmon primary" in content
    assert "[upsmon_secondary]" in content
    assert "upsmon secondary" in content


def test_write_upsmon_conf_primary(tmp_path: Path) -> None:
    writer = NUTConfigWriter(str(tmp_path))
    monitors = [
        {
            "ups_name": "myups",
            "user": "upsmon_primary",
            "password": "monpass",
            "role": "primary",
        }
    ]
    writer.write_upsmon_conf(monitors)
    content = (tmp_path / "upsmon.conf").read_text()
    assert content.startswith(HEADER)
    assert "MONITOR myups@localhost:3493 1 upsmon_primary monpass primary" in content
    assert "MINSUPPLIES 1" in content
    assert 'SHUTDOWNCMD "/sbin/shutdown -h +0"' in content
    assert "POWERDOWNFLAG /etc/killpower" in content
    assert "POLLFREQ 5" in content
    assert "DEADTIME 15" in content
    assert "NOTIFYMSG ONLINE" in content
    assert "NOTIFYFLAG ONBATT" in content


def test_write_upsmon_conf_secondary(tmp_path: Path) -> None:
    writer = NUTConfigWriter(str(tmp_path))
    monitors = [
        {
            "ups_name": "myups",
            "host": "10.0.0.1",
            "port": 3493,
            "powervalue": 1,
            "user": "upsmon_secondary",
            "password": "monpass",
            "role": "secondary",
        }
    ]
    writer.write_upsmon_conf(monitors)
    content = (tmp_path / "upsmon.conf").read_text()
    assert "MONITOR myups@10.0.0.1:3493 1 upsmon_secondary monpass secondary" in content


def test_backup_existing(tmp_path: Path) -> None:
    # Create some existing config files
    (tmp_path / "nut.conf").write_text("MODE=standalone\n")
    (tmp_path / "ups.conf").write_text("[myups]\n")

    writer = NUTConfigWriter(str(tmp_path))
    backups = writer.backup_existing()
    assert len(backups) == 2
    for backup in backups:
        assert Path(backup).exists()
        assert ".bak." in backup


def test_write_server_creates_all_five(tmp_path: Path) -> None:
    writer = NUTConfigWriter(str(tmp_path))
    ups_list = [
        {
            "name": "myups",
            "driver": "usbhid-ups",
            "port": "auto",
            "desc": "APC UPS",
        }
    ]
    paths = writer.write_server("netserver", ups_list, "adminpass", "monpass")
    assert len(paths) == 5
    for path in paths:
        assert path.exists()

    # Verify all files exist by name
    assert (tmp_path / "nut.conf").exists()
    assert (tmp_path / "ups.conf").exists()
    assert (tmp_path / "upsd.conf").exists()
    assert (tmp_path / "upsd.users").exists()
    assert (tmp_path / "upsmon.conf").exists()

    # Netserver should listen on 0.0.0.0
    upsd_content = (tmp_path / "upsd.conf").read_text()
    assert "LISTEN 0.0.0.0" in upsd_content


def test_write_server_standalone_listens_localhost(tmp_path: Path) -> None:
    writer = NUTConfigWriter(str(tmp_path))
    ups_list = [
        {
            "name": "myups",
            "driver": "usbhid-ups",
            "port": "auto",
            "desc": "APC UPS",
        }
    ]
    writer.write_server("standalone", ups_list, "adminpass", "monpass")
    upsd_content = (tmp_path / "upsd.conf").read_text()
    assert "LISTEN 127.0.0.1" in upsd_content


def test_read_mode(tmp_path: Path) -> None:
    (tmp_path / "nut.conf").write_text("# comment\nMODE=netserver\n")
    reader = NUTConfigReader(str(tmp_path))
    assert reader.read_mode() == "netserver"


def test_read_mode_missing(tmp_path: Path) -> None:
    reader = NUTConfigReader(str(tmp_path))
    assert reader.read_mode() is None


def test_has_existing_config_true(tmp_path: Path) -> None:
    (tmp_path / "nut.conf").write_text("MODE=standalone\n")
    reader = NUTConfigReader(str(tmp_path))
    assert reader.has_existing_config() is True


def test_has_existing_config_false(tmp_path: Path) -> None:
    reader = NUTConfigReader(str(tmp_path))
    assert reader.has_existing_config() is False


def test_creates_conf_dir_if_missing(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "nested" / "nut"
    writer = NUTConfigWriter(str(nested))
    writer.write_nut_conf("standalone")
    assert (nested / "nut.conf").exists()
