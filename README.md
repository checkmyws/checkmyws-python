![Build](https://travis-ci.org/checkmyws/checkmyws-python.svg)

# checkmyws-python

[Check my Website](https://checkmy.ws) client for Python.

## REST api

todo

## WAMP api

Setup a test environment

```
git clone -b live https://github.com/checkmyws/checkmyws-python.git
cd checkmyws-python
virtualenv python
source python/bin/activate
pip install -r requirements.txt
pip install service_identity pyOpenSSL twisted txaio autobahn
```

Exemple
```
import logging
logging.basicConfig(level=logging.INFO)

from checkmyws.live import run, register


@register(".*")
def on_event(timestamp, check, procedure, location, worker, output):
    print("%s %s: %s %s %s", timestamp, check['_id'], procedure, location, output)

run(authid='<LOGIN>', secret='<TOKEN>')

```
