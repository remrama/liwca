.. _guide-ddr:

Distributed Dictionary Representation
=====================================

:func:`~liwca.ddr` performs semantic scoring of texts against dictionary categories
using cosine similarity in embedding space, following the Distributed Dictionary
Representation (DDR) method (Garten et al., 2018). This captures semantic proximity
even when exact dictionary words are absent from the text.

Pass a gensim model name to automatically download embeddings (requires
``pip install liwca[ddr]``):

.. code-block:: python

   results = liwca.ddr(texts, dx, "glove-wiki-gigaword-100")

Or bring your own embeddings as a dict-like mapping:

.. code-block:: python

   results = liwca.ddr(texts, dx, my_embeddings)

Values are cosine similarities in [-1, 1].  See :func:`~liwca.ddr` for full
parameter details.
