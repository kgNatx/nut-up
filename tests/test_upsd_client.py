"""Tests for the NUT upsd protocol client."""

import pytest

from nut_up.upsd_client import NUTError, UpsdClient


pytestmark = pytest.mark.anyio


async def test_server_version(mock_upsd) -> None:
    async with UpsdClient(mock_upsd.host, mock_upsd.port) as client:
        version = await client.server_version()
        assert "upsd" in version
        assert "2.8.0" in version


async def test_list_ups(mock_upsd) -> None:
    async with UpsdClient(mock_upsd.host, mock_upsd.port) as client:
        ups_list = await client.list_ups()
        assert "myups" in ups_list
        assert ups_list["myups"] == "Test UPS (mock)"


async def test_list_vars(mock_upsd) -> None:
    async with UpsdClient(mock_upsd.host, mock_upsd.port) as client:
        vars_ = await client.list_vars("myups")
        assert vars_["ups.status"] == "OL"
        assert vars_["battery.charge"] == "100"
        assert vars_["battery.runtime"] == "3600"
        assert vars_["ups.load"] == "25"
        assert vars_["input.voltage"] == "120.0"


async def test_get_var(mock_upsd) -> None:
    async with UpsdClient(mock_upsd.host, mock_upsd.port) as client:
        status = await client.get_var("myups", "ups.status")
        assert status == "OL"
        charge = await client.get_var("myups", "battery.charge")
        assert charge == "100"


async def test_get_var_unknown_ups(mock_upsd) -> None:
    async with UpsdClient(mock_upsd.host, mock_upsd.port) as client:
        with pytest.raises(NUTError) as exc_info:
            await client.get_var("nonexistent", "ups.status")
        assert exc_info.value.code == "UNKNOWN-UPS"


async def test_list_rw(mock_upsd) -> None:
    async with UpsdClient(mock_upsd.host, mock_upsd.port) as client:
        rw = await client.list_rw("myups")
        assert "ups.delay.shutdown" in rw
        assert rw["ups.delay.shutdown"] == "20"
        assert "ups.delay.start" in rw
        assert rw["ups.delay.start"] == "30"


async def test_list_commands(mock_upsd) -> None:
    async with UpsdClient(mock_upsd.host, mock_upsd.port) as client:
        cmds = await client.list_commands("myups")
        assert "test.battery.start" in cmds
        assert "shutdown.return" in cmds
        assert "beeper.toggle" in cmds
        assert len(cmds) == 4


async def test_list_clients(mock_upsd) -> None:
    async with UpsdClient(mock_upsd.host, mock_upsd.port) as client:
        clients = await client.list_clients("myups")
        assert "127.0.0.1" in clients


async def test_authenticate_and_set_var(mock_upsd) -> None:
    async with UpsdClient(mock_upsd.host, mock_upsd.port) as client:
        await client.authenticate("admin", "testpass")
        # Should not raise
        await client.set_var("myups", "ups.delay.shutdown", "30")


async def test_authenticate_and_instcmd(mock_upsd) -> None:
    async with UpsdClient(mock_upsd.host, mock_upsd.port) as client:
        await client.authenticate("admin", "testpass")
        await client.run_command("myups", "test.battery.start")


async def test_set_var_without_auth(mock_upsd) -> None:
    async with UpsdClient(mock_upsd.host, mock_upsd.port) as client:
        with pytest.raises(NUTError) as exc_info:
            await client.set_var("myups", "ups.delay.shutdown", "30")
        assert exc_info.value.code == "ACCESS-DENIED"
