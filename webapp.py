""" Copyright (C) 2023 Blair Azzopardi

Simple REST API for uploading market data and pricing options.

Example usage:

    # see uploaded market data
    curl http://0.0.0.0:8080/marketdata/get

    # upload json with market data
    curl -F data=@./market_data.json http://0.0.0.0:8080/marketdata/put

    # price and option
    curl http://0.0.0.0:8080/optionpricing/european/BRN/Jan24/Call/100

"""

import json
from statistics import NormalDist
import logging

import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.interpolate import CubicSpline
from aiohttp import web
from aiohttp.web import Request, Response, RouteTableDef

routes = RouteTableDef()

uploaded_data = {}

Z = norm()


logger = logging.getLogger(__name__)


# curl http://0.0.0.0:8080/marketdata/get
@routes.get("/marketdata/get")
async def market_data_get(request: Request) -> Response:
    """Retrieve market data."""
    return web.json_response(uploaded_data)


# curl -F data=@./market_data.json http://0.0.0.0:8080/marketdata/put
@routes.post("/marketdata/put")
async def market_data_put(request: Request) -> Response:
    """Upload market data using format supplied in accompanying file market_data.json."""
    try:
        global uploaded_data
        post = await request.post()
        data = post.get("data")
        if data:
            content = data.file.read()  # type: ignore
            # TODO: check format of file
            uploaded_data = json.loads(content)
            if not isinstance(uploaded_data, list) and not all(
                isinstance(x, dict) for x in uploaded_data
            ):
                raise ValueError("market data should be a list of dicts")
            allowable_fields = {
                "FuturesPrice",
                "Symbol",
                "SmileCallDeltas",
                "Tenors",
                "VolatilitySurface",
            }
            if set.union(*[set(x) for x in uploaded_data]) > allowable_fields:
                raise ValueError(
                    "market data fields must be one of %s", allowable_fields
                )
        return web.json_response({"message": "success"})
    except Exception as e:
        logger.exception("Unexpected error in market_data_put")
        return web.json_response({"error": str(e)}, status=530)


def get_today() -> pd.Timestamp:
    """Fix today for this demo, however, in real scenarion use today's actual date."""
    # return pd.Timestamp.now().floor('d')
    return pd.Timestamp("2023-03-16")


def get_rate() -> float:
    """Fix to value, however, in real scenario used internal rates/discount curves."""
    return 0.01


def get_expiry(symbol, tenor) -> pd.Timestamp:
    """Determine option expiry from tenor."""
    tenor = pd.to_datetime(tenor, format="%b%y")

    if symbol == "BRN":
        return tenor - pd.offsets.BMonthEnd(2)
    elif symbol == "HH":
        return tenor - pd.offsets.BMonthEnd(1)
    else:
        raise ValueError("Unsupported symbol in get_expiry: %s", symbol)


def delta_to_strike(delta, vol, T, F, df=1):
    """Convert vol sfc delta to equivalent strike."""
    d1 = Z.ppf(delta / df)
    return F * np.exp(0.5 * vol * vol * T - vol * d1 * np.sqrt(T))


# curl http://0.0.0.0:8080/optionpricing/european/BRN/Jan24/Call/100
@routes.get("/optionpricing/european/{symbol}/{tenor}/{putcall}/{strike}")
async def optionpricing_european(request: Request) -> Response:
    """Price an option."""
    try:
        global uploaded_data

        if not uploaded_data:
            raise ValueError("No market data uploaded!")

        symbol = request.match_info["symbol"]
        tenor = request.match_info["tenor"]
        putcall = request.match_info["putcall"].lower()
        K = float(request.match_info["strike"])

        if putcall not in ["put", "call"]:
            raise ValueError("option must be either put or call")

        mds = [dct for dct in uploaded_data if dct["Symbol"] == symbol]
        if not mds:
            raise ValueError("No market data for %s", symbol)

        today = get_today()
        expiry = get_expiry(symbol, tenor)

        if today < expiry:
            N = (expiry - today).days
            T = N / 365

            # extract market data
            md = mds[0]
            md_tenor_ix = md["Tenors"].index(tenor)
            md_smile = np.array(md["VolatilitySurface"][md_tenor_ix])
            md_deltas = np.array(md["SmileCallDeltas"])
            F = md["FuturesPrice"][md_tenor_ix]

            # find corresponding strike from vol sfc

            # switch from deltas to strikes
            md_strikes = delta_to_strike(md_deltas, md_smile / 100, T, F, 1)

            # ensure we are sorted correctly for spline
            ix_sorted = np.argsort(md_strikes)

            vol_spline = CubicSpline(
                md_strikes[ix_sorted],
                md_smile[ix_sorted],
                bc_type="clamped",
                extrapolate=True,
            )

            sigma = vol_spline(K)

            r = get_rate()

            # use black76 formula
            d1 = (np.log(F / K) + sigma**2 / 2 * T) / sigma / np.sqrt(T)
            d2 = d1 - sigma * np.sqrt(T)
            if putcall == "call":
                prem = np.exp(-r * T) * (F * Z.cdf(d1) - K * Z.cdf(d2))
            else:  # == "put"
                prem = np.exp(-r * T) * (K * Z.cdf(-d2) - F * Z.cdf(-d1))
        else:
            prem = 0

        return web.json_response({"premium": prem})

    except Exception as e:
        logger.exception("Unexpected error in optionpricing_european")
        return web.json_response({"error": str(e)}, status=530)


app = web.Application()
app.router.add_routes(routes)

if __name__ == "__main__":
    web.run_app(app)
