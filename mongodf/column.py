from .filter import Filter

class Column():
    def __init__(self, dataframe, name):
        self._mf = dataframe
        self._name = name

    def isin(self, array):
        return Filter(self._mf, {self._name: {"$in": array}})

    def __eq__(self, value):
        return Filter(self._mf, {self._name: {"$eq": value}})

    def __ne__(self, value):
        return Filter(self._mf, {self._name: {"$gte": value}})

    def __ge__(self, value):
        return Filter(self._mf, {self._name: {"$gte": value}})

    def __gt__(self, value):
        return Filter(self._mf, {self._name: {"$gt": value}})

    def __lt__(self, value):
        return Filter(self._mf, {self._name: {"$lt": value}})

    def __le__(self, value):
        return Filter(self._mf, {self._name: {"$lt": value}})