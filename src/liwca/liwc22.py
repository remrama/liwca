"""
Run LIWC from command line without having to open it up manually.

https://www.liwc.app/help/cli
https://github.com/ryanboyd/liwc-22-cli-python/blob/main/LIWC-22-cli_Example.py
"""

# import argparse
import subprocess
import time

import psutil


__all__ = [
    "cli",
]


def _return_liwc_process(app_name: str = "LIWC-22") -> psutil.Process:
    """
    Return a process object for a running application.

    Parameters
    ----------
    app_name : str
        The name of the application to return the process object for.

    Returns
    -------
    psutil.Process
        The process object for the running application.
    """
    for proc in psutil.process_iter(["name"]):
        if proc.name().split(".")[0] == app_name:
            assert proc.status() == psutil.STATUS_RUNNING
            return proc


def _is_liwc_running(app_name: str = "LIWC-22") -> bool:
    """
    Check if an application is running on the computer.

    Parameters
    ----------
    app_name : str
        The name of the application to check.

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


def _open_liwc(app_name: str = "LIWC-22", wait: int = 30) -> subprocess.Popen:
    """
    Open an application and wait until it is fully loaded.
    C:/Program Files/LIWC-22/LIWC-22.exe

    Parameters
    ----------
    app_name : str, optional
        The name of the application to check. Defaults to LIWC-22.
    timeout : int, optional
        The maximum time to wait for the application to load, in seconds (default is 30).
        If None, don't wait.

    Returns
    -------
    bool
        True if the application is fully loaded within the timeout period, False otherwise.
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
    return


def _terminate_liwc(app_name: str = "LIWC-22") -> psutil.Process:
    """
    Terminate a running application.

    Parameters
    ----------
    app_name : str
        The name of the application to terminate.

    Returns
    -------
    bool
        True if the application was terminated, False otherwise.
    """
    if (proc := _return_liwc_process(app_name)) is not None:
        proc.terminate()
        proc.wait()
    return proc


def cli(shell_kwargs: dict = {}, **kwargs) -> int:
    """
    Run LIWC-22-cli from Python.
 -m,--mode <arg>   Selects type of analysis: word count (wc), word frequency (freq), mean extraction method (mem),
                   contextualizer (context), arc of narrative (arc), convert separate transcript files to spreadsheet
                   (ct), language style matching (lsm).
                   Possible values: wc, freq, mem, context, arc, ct, lsm
    """
    assert _is_liwc_running(), "LIWC-22 is not running."
    # assert mode in ["wc", "freq", "mem", "context", "arc", "ct", "lsm"], f"Invalid mode: {mode}"
    # command = ["liwc-22-cli", "--mode", mode]
    command = ["liwc-22-cli"]
    for key, value in kwargs.items():
        command.extend([f"--{key}", value])
    retcode = subprocess.call(command, **shell_kwargs)
    return retcode
