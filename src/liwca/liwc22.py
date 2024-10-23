"""
Run LIWC from command line without having to open it up manually.

https://www.liwc.app/help/cli
https://github.com/ryanboyd/liwc-22-cli-python/blob/main/LIWC-22-cli_Example.py
"""

import subprocess
import time
from typing import Any, Optional

import psutil

__all__ = [
    "cli",
]


def _return_liwc_process(app_name: str = "LIWC-22") -> psutil.Process:
    """
    Find and return the process for the specified application name.

    This function iterates over all running processes and returns the process
    that matches the given application name and is currently running.

    Parameters
    ----------
    app_name : str, optional
        The name of the application to search for (default is "LIWC-22").

    Returns
    -------
    psutil.Process
        The process object for the specified application.

    Raises
    ------
    AssertionError
        If the process is found but is not in a running state.
    """
    for proc in psutil.process_iter(["name"]):
        if proc.name().split(".")[0] == app_name:
            assert proc.status() == psutil.STATUS_RUNNING
            return proc


def _is_liwc_running(app_name: str = "LIWC-22") -> bool:
    """
    Check if a specific application is currently running.

    This function iterates through all running processes and checks if any
    process matches the given application name. It asserts that the process
    status is running.

    Parameters
    ----------
    app_name : str, optional
        The name of the application to check for (default is "LIWC-22").

    Returns
    -------
    bool
        True if the application is running, False otherwise.
    """
    for proc in psutil.process_iter(["name"]):
        if proc.name().split(".")[0] == app_name:
            assert proc.status() == psutil.STATUS_RUNNING
            return True
    return False


def _open_liwc(app_name: str = "LIWC-22", wait: int = 30) -> Optional[subprocess.Popen]:
    """
    Opens the LIWC application if it is not already running.
    Parameters
    ----------
    app_name : str, optional
        The name of the LIWC application to open. Default is "LIWC-22".
    wait : int, optional
        The maximum time to wait (in seconds) for the application to start. Default is 30 seconds.
    Returns
    -------
    Optional[subprocess.Popen]
        A Popen object if the application was started successfully, None if the application is already running or could not be started.
    """

    if _return_liwc_process(app_name) is None:
        popen = subprocess.Popen(app_name)
        if wait is not None:
            start_time = time.time()
            while time.time() - start_time < wait:
                proc = _return_liwc_process(app_name)
                if proc is not None:
                    return popen
                time.sleep(1)  # Wait for 1 second before checking again
        return popen
    return None


def _terminate_liwc(app_name: str = "LIWC-22") -> psutil.Process:
    """
    Terminates the LIWC application process if it is running.

    Parameters
    ----------
    app_name : str, optional
        The name of the LIWC application to terminate. Default is "LIWC-22".

    Returns
    -------
    psutil.Process
        The process object of the terminated LIWC application, or None if the process was not found.
    """
    if (proc := _return_liwc_process(app_name)) is not None:
        proc.terminate()
        proc.wait()
    return proc


def cli(shell_kwargs: dict[str, Any] = {}, **kwargs: Any) -> int:
    """
    Execute the LIWC-22 command line interface with the given arguments.

    Parameters
    ----------
    shell_kwargs : dict[str, Any], optional
        Additional keyword arguments to pass to the subprocess call.
    **kwargs : Any
        Command line arguments to pass to the LIWC-22 CLI.

    Returns
    -------
    int
        The return code from the subprocess call.

    Raises
    ------
    AssertionError
        If LIWC-22 is not running.
    """
    assert _is_liwc_running(), "LIWC-22 is not running."
    command = ["liwc-22-cli"]
    for key, value in kwargs.items():
        command.extend([f"--{key}", value])
    retcode = subprocess.call(command, **shell_kwargs)
    return retcode
