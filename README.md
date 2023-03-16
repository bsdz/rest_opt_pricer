# rest_opt_pricer

Price simple options using simple REST API.

Run following commands. You'll need poetry.

```bash
# clone repo or unzip source
#...

# create venv
$ python3.10 -mvenv .venv

# activate
$ . .venv/bin/activate

# install deps
$ poetry install

# run app
$ poetry run python webapp.py
```

You should see:

```bash
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
```

In a separate terminal you can do:

```bash
# see uploaded market data
$ curl http://0.0.0.0:8080/marketdata/get; echo
{}

# upload json with market data
$ curl -F data=@./market_data.json http://0.0.0.0:8080/marketdata/put; echo
{"message": "success"}

# check market data uploaded
$ curl http://0.0.0.0:8080/marketdata/get; echo
[{"Symbol": "BRN", "Tenors": ["Jan24", "Feb24"], "FuturesPrice": [100, 120], "SmileCallDeltas": [0.1, 0.25, 0.5, 0.75, 0.9], "VolatilitySurface": [[50, 49, 48, 49, 50], [51, 50, 49, 50, 51]]}, {"Symbol": "HH", "Tenors": ["Feb24", "Mar24"], "FuturesPrice": [100, 120], "SmileCallDeltas": [0.1, 0.25, 0.5, 0.75, 0.9], "VolatilitySurface": [[50, 49, 48, 49, 50], [51, 50, 49, 50, 51]]}]


# price and option
$ curl http://0.0.0.0:8080/optionpricing/european/BRN/Jan24/Call/100; echo
{"premium": 15.951506051334627}

# price and option
$ curl http://0.0.0.0:8080/optionpricing/european/BRN/Jan24/Put/110; echo
{"premium": 22.122937284478322}

# some basic error handling.
$ curl http://0.0.0.0:8080/optionpricing/european/BRN/Jan24/PutX/100; echo
{"error": "option must be either put or call"}
```