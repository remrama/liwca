Available Dictionaries
======================

liwca includes a registry of public LIWC-format dictionaries that can be
fetched and cached locally with :func:`~liwca.fetch_dx` or
:func:`~liwca.fetch_path`.

To list all available dictionaries:

.. code-block:: python

   import liwca
   liwca.list_available()
   # ['bigtwo_a', 'bigtwo_b', 'honor', 'mystical', 'sleep', 'threat']


Dictionary catalogue
--------------------

.. list-table::
   :header-rows: 1
   :widths: 15 10 45 30

   * - Name
     - Format
     - Description
     - Source
   * - ``bigtwo_a``
     - ``.dic``
     - Big Two personality dimensions (agency).
     - `OSF <https://osf.io/download/62txv>`_
   * - ``bigtwo_b``
     - ``.dic``
     - Big Two personality dimensions (communion).
     - `OSF <https://osf.io/download/y59eb>`_
   * - ``honor``
     - ``.dic``
     - Honor culture dictionary (English).
     - `Gelfand et al., 2015 <https://drive.google.com/uc?export=download&id=1EmQ5fFcr7ATRffyIP87Fej_TO3nDER6h>`_
   * - ``mystical``
     - ``.xlsx``
     - Mystical experience dictionary.
     - `OSF <https://osf.io/6ph8z>`_
   * - ``sleep``
     - ``.tsv``
     - Sleep-related language dictionary.
     - `Zenodo <https://zenodo.org/records/13941010>`_
       (`PMC9908817 <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9908817>`_)
   * - ``threat``
     - ``.txt``
     - Threat perception dictionary (English).
     - `Gelfand et al. <https://www.michelegelfand.com/threat-dictionary>`_
       (`doi:10.1073/pnas.2113891119 <https://doi.org/10.1073/pnas.2113891119>`_)


Fetching dictionaries
---------------------

Use :func:`~liwca.fetch_dx` to download and load a dictionary as a
:class:`~pandas.DataFrame`:

.. code-block:: python

   dx = liwca.fetch_dx("threat")
   dx.head()

The file is downloaded once and cached locally via
`Pooch <https://www.fatiando.org/pooch/latest/>`_.

To get only the cached file path without loading:

.. code-block:: python

   fp = liwca.fetch_path("threat")


Cache location
~~~~~~~~~~~~~~

By default, files are cached in your OS data directory:

- **Linux:** ``~/.cache/liwca``
- **macOS:** ``~/Library/Caches/liwca``
- **Windows:** ``%LOCALAPPDATA%\liwca``

You can override this by setting the ``LIWCA_DATA_DIR`` environment variable
before importing liwca:

.. code-block:: bash

   export LIWCA_DATA_DIR=/path/to/my/cache
