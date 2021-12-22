
from .filter import Filter
from .column import Column
from .exception import MongoDfException
import pandas as _pd


class DataFrame():

    def __init__(self, _mongo, _database, _collection, _columns, _filter=None):
        self._mongo = _mongo
        self._database = _database
        self._collection = _collection
        self.columns = _columns
        self._filter = _filter

    def __getitem__(self, key):
        if isinstance(key, Filter):
            return DataFrame(
                self._mongo,
                self._database,
                self._collection,
                self.columns,
                key.__and__(self._filter)
            )

        if isinstance(key, list):
            if not all([k in self.columns for k in key]):
                raise MongoDfException("Not all columns available")

            return DataFrame(
                self._mongo,
                self._database,
                self._collection,
                key,
                self._filter
            )

        if key in self.columns:
            return Column(self, key)
        else:
            raise MongoDfException(f"column {key} not found!")

    def __getattr__(self, key):
        if key in self.columns:
            return Column(self, key)
        else:
            raise MongoDfException(f"column {key} not found!")

    def compute(self):
        colfilter = {"_id": 0}
        colfilter.update({c: 1 for c in self.columns})

        return _pd.DataFrame(
            list(self._collection.find(
                self._filter.config,
                colfilter
            ))
        )
