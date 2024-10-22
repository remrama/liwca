
.. image:: https://badge.fury.io/py/liwca.svg
   :target: https://badge.fury.io/py/liwca
   :alt: PyPI

.. image:: https://img.shields.io/pypi/l/liwca.svg
   :target: https://github.com/remrama/liwca/blob/main/LICENSE.txt
   :alt: License

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
   :target: https://github.com/astral-sh/ruff
   :alt: Ruff

----


LIWCA
=====


LIWCA is a `LIWC <https://liwc.app>`_ assistant. It is not a copy of LIWC (they don't like that), it is just helper functions that I've found useful.

Stuff like:

* Reading and writing dictionary files (``.dic[x]``)
* Converting between ``.dic`` and ``.dicx`` files
* Converting between dictionary (``.dic[x]``) and tabular (``.[c|t]sv``) files
* Merging dictionary files
* Fetching public dictionary files from remote repositories
* Calling ``liwc-22-cli`` from Python



Installation
------------

.. code-block:: shell

   pip install liwca



Usage
-----

.. code-block:: python

   import liwca

   # Download and read a public dictionary
   dx = liwca.fetch_dx("sleep")

   # Write local dictionary files
   liwca.write_dx(dx, "./sleep.dic")
   liwca.write_dx(dx, "./sleep.dicx")

   # Read local dictionaries
   dx = liwca.read_dic("./sleep.dic")
   dx = liwca.read_dicx("./sleep.dicx")

   dx.to_dicx("./moral-foundations.dicx")

   # Load local dictionary
   dic = liwca.read_dx("./sleep.dicx")
