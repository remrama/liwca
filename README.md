# liwca

LIWCA is a [LIWC](https://liwc.app) assistant. It is not a copy of LIWC (they don't like that), it is just helper functions that I've found useful.

Stuff like:

- Reading and writing dictionary files (`.dic[x]`)
- Converting between `.dic` and `.dicx` files
- Converting between dictionary (`.dic[x]`) and tabular (`.[ct]sv`) files
- Fetching public dictionary files from remote repositories
- Calling `liwc-22-cli` from Python


### Install with pip

```shell
pip install liwca
```


## Examples

```python
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
```
