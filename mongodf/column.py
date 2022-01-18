from .filter import Filter
import numpy as _np
import pandas as _pd


class Column():
    def __init__(self, dataframe, name):
        self._mf = dataframe
        self._name = name

    def isin(self, array):
        return Filter(self._mf, {self._name: {"$in": array}})

    def __eq__(self, value):
        return Filter(self._mf, {self._name: {"$eq": value}})

    def __ne__(self, value):
        return Filter(self._mf, {self._name: {"$ne": value}})

    def __ge__(self, value):
        return Filter(self._mf, {self._name: {"$gte": value}})

    def __gt__(self, value):
        return Filter(self._mf, {self._name: {"$gt": value}})

    def __lt__(self, value):
        return Filter(self._mf, {self._name: {"$lt": value}})

    def __le__(self, value):
        return Filter(self._mf, {self._name: {"$lte": value}})

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
