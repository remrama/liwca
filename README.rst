
.. image:: https://www.repostatus.org/badges/latest/wip.svg
   :target: https://www.repostatus.org/#wip
   :alt: Project Status

.. image:: https://img.shields.io/pypi/v/liwca.svg
   :target: https://pypi.python.org/pypi/liwca
   :alt: PyPI

.. image:: https://img.shields.io/pypi/pyversions/liwca.svg
   :target: https://pypi.python.org/pypi/ruff
   :alt: Python Versions

.. image:: https://img.shields.io/pypi/l/liwca.svg
   :target: https://github.com/remrama/liwca/blob/main/LICENSE.txt
   :alt: License

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
   :target: https://github.com/astral-sh/ruff
   :alt: Ruff



LIWCA
=====


LIWCA is a `LIWC <https://liwc.app>`_ assistant. It is not a copy of LIWC (they don't like that), it is just helper functions that I've found useful.

Stuff like:

* Reading and writing dictionary files (``.dic[x]``)
* Converting between ``.dic`` and ``.dicx`` files
* Converting between dictionary (``.dic[x]``) and tabular (``.[c|t]sv``) files
* Merging dictionary files
* Fetching public dictionary files from remote repositories
* Calling ``liwc-22-cli`` from Python (opens/closes the LIWC-22 app in background as needed)



Installation
------------

.. code-block:: shell

   pip install --upgrade liwca



Usage
-----

.. code-block:: python

   import liwca

   # Download and read a public dictionary files
   dx = liwca.fetch_dx("sleep")

   # Read local dictionary files
   dx = liwca.read_dx("./sleep.dic")
   dx = liwca.read_dx("./sleep.dicx")

   # Write local dictionary files
   liwca.write_dx(dx, "./sleep.dic")
   liwca.write_dx(dx, "./sleep.dicx")



Similar Projects
----------------

* `liwc-python <https://github.com/chbrown/liwc-python>`_
* `lingmatch <https://github.com/miserman/lingmatch>`_
* `sentibank <https://github.com/socius-org/sentibank>`_
