import subprocess
import sys

from mfbcontrol import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "mfbcontrol.ioc", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
