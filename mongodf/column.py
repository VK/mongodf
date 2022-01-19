from .filter import Filter
import numpy as _np
import pandas as _pd
import datetime


class Column():
    def __init__(self, dataframe, name):
        self._mf = dataframe
        self._name = name

    def _encode_value(self, value):
        if isinstance(value, _np.datetime64):
            return _pd.Timestamp(value).to_pydatetime()
        return value

    def isin(self, array):
        return Filter(self._mf, {self._name: {"$in": array}})

    def __eq__(self, value):
        return Filter(self._mf, {self._name: {"$eq": self._encode_value(value)}})

    def __ne__(self, value):
        return Filter(self._mf, {self._name: {"$ne": self._encode_value(value)}})

    def __ge__(self, value):
        return Filter(self._mf, {self._name: {"$gte": self._encode_value(value)}})

    def __gt__(self, value):
        return Filter(self._mf, {self._name: {"$gt": self._encode_value(value)}})

    def __lt__(self, value):
        return Filter(self._mf, {self._name: {"$lt": self._encode_value(value)}})

    def __le__(self, value):
        return Filter(self._mf, {self._name: {"$lte": self._encode_value(value)}})

    def unique(self):

        return _np.array(
            self._mf._collection.distinct(
                self._name,
                self._mf._filter.config
            )
        )

    def agg(self, types):
        if isinstance(types, str):
            types = [types]

        pmap = {
            "mean": "$avg",
            "median": "$avg",
            "min": "$min",
            "max": "$max",
        }

        res = self._mf._collection.aggregate([
            {"$match": self._mf._filter.config},
            {"$group": {
                "_id": None,
                **{t: {pmap[t]: f"${self._name}"} for t in types}
            }}
        ])

        res = list(res)[0]
        res = {k: v for k, v in res.items() if k != "_id"}

        return _pd.Series(res, name=self._name)
