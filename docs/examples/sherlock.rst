.. _examples-sherlock:

Run LIWC word count analysis on Sherlock corpus
===============================================


.. code-block:: python

   >>> import liwca
   >>> from liwca.datasets import corpora, dictionaries
   >>>
   >>> df = corpora.fetch_sherlock()
   >>> dx = dictionaries.fetch_sleep()
   >>> results = liwca.count(df["text"], dx)
   >>> results.head()
   Category    WC     sleep
   text_id
   NN01      1592  0.062814
   NN02      1958  0.000000
   NN03      2492  0.000000
   NN04      1746  0.057274
   NN05      1398  0.000000
