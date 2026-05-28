import subprocess


class FakeCompletedProcess:
    def __init__(self, returncode=0):
        self.returncode = returncode


def make_fake_run(returncode=0, raise_timeout=False, raise_exception=False):
    """
    Returns a drop-in replacement for subprocess.run.

    Args:
        returncode:       Exit code the fake process returns (default 0 = success).
        raise_timeout:    If True, raises subprocess.TimeoutExpired (simulates FFmpeg hang).
        raise_exception:  If True, raises a generic Exception (simulates system error).
    """
    def fake_run(cmd, **kwargs):
        if raise_exception:
            raise Exception("fake subprocess error")
        if raise_timeout:
            arg0 = cmd[0] if isinstance(cmd, list) else cmd
            timeout = kwargs.get("timeout", 60)
            raise subprocess.TimeoutExpired(arg0, timeout)
        return FakeCompletedProcess(returncode=returncode)

    return fake_run
