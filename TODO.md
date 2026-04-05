# TODO

- Add useful Claude skills and/or agents.
- Add agents files that GitHub Copilot will expect.
- function to list available dictionaries to fetch
- Add type checking (static type checking? incorporate with pandera?)
- Update pandera schema (any new ones? standardize code, any new attributes?)
- Review and revise tutorial
- Raise concern about memory issues with count module
- Run test of all remote downloads only during a merge into main, and require passing before successful push/release. Related: how to handle that some have version control but others don't.
- Improve docs for dicx_processor(), and also I think assertion should check for not only dicx but dic.
- Standardize read_raw_* docstrings. Related: need a standard format for all read docstrings so that there can be a good documentation for the available dictionaries.
- Raise specific error if a fetched dictionary is trying to be loaded but doesn't have a loader (and is not a dic or dicx file).
- Create contributing docs page and be specific about how to add a new dictionary.
- What is going on with _get_downloader()?
- Add float precision option to counts
- Add cache to tests across the matrix, since examples use doctests and will have to call pooch.
- as_proportion in counts() isn't really accurate, since it's a percentage by default, not a proportion. Should it be reported as percentage or proportion?
- Use index of returned dataframe from counts() as a text identifier
    In [26]: liwca.count(texts, dx)
    Out[26]:
    Category  WC  threat
    0          8    12.5
    1          4     0.0
    Should be a text ID. If not provided via pandas series, should be generated. Input options should be an iterable with key value text_id, text pairs.
- MAJOR: Add individual word count export from counts.
- MAJOR: Add ability to handle large memory and write to file directly with counts. I like having both options.
- Update docs and README to emphasize using liwca command line CLI (rather than the Python access, thought still include a note of that)
- Streamline docs and README to focus on the primary features?
- Add sphinx directives to _remoteprocessors (I think claude didn't do it for the hidden functions)
- Add pooch and other dependencies to conf.py interpshinx mapping
- Better handling of pooch data path dir, either as argument through fetcher and/or through environment variable (via Pooch's `env` argument). Be clear in the docs about this option.
- Make sure that the docs have targeted section on fetching remote dictionaries.
- Create a dictionaries or fetchers page in the docs and have a place where all the available dictionaries are mentioned and described in detail. This might be a bigger thing, as we need to somehow have systematic and standardized metadata for all the dictionaries. Maybe docstrings and/or somewhere else.
- MAJOR: multi-level handling in dx dataframes for category/subcategories/etc. So confusing, like how sleep and threat "dictionaries" are just a category, but then honor dictionary has categories.
- When you drop a category from a dictionary (dx column), then you might still have a bunch of words that now have 0 for all columns. Those rows should be able to be removed. Should there be like a "drop_category" function?
- Should dx be a class object instead of a dictionary?
    - dx.filepath
    - dx.citation
    - dx.categories
    - dx.count(sentences)
    - dx.to_dic
    - dx.to_dicx
    - dx.merge(otherdic)
    - with dic as dx:
