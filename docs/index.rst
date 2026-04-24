.. image:: _static/banner.png
   :class: only-light
   :align: center

.. image:: _static/banner-dark.png
   :class: only-dark
   :align: center

|

:bolditalic:`liwca` (Linguistic Inquiry Word Count Assistant) is a Python helper library for working with `LIWC <https://liwc.app>`_
dictionaries. It is useful when you want end-to-end pipelines or notebook workflows
that don't require the LIWC-22 app to be open, or when you just need reusable
``.dic[x]`` file I/O without writing it from scratch every project.

.. code-block:: bash

   pip install liwca

Features
--------

.. - :ref:`api-io` - Read, write, and merge ``.dic`` and ``.dicx`` dictionary files
.. - :ref:`api-count` - Pure-Python LIWC-style word counting, no LIWC-22 required
.. - :ref:`api-ddr` - Semantic scoring via word embeddings (DDR)
.. - :ref:`api-datasets` - Download and cache public LIWC-format dictionaries on demand
.. - :ref:`api-liwc22` - Python wrapper for the LIWC-22 command-line tool

.. toctree::
   :hidden:

   guide
   api/index
   changelog
