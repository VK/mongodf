
from .filter import Filter
from .column import Column
from .exception import MongoDfException
import pandas as _pd
from itertools import cycle, islice


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

    def example(self, n=5):

        def get_sampledata(name):
            data = list(self._collection.find(
                {name: {"$exists": True}}, {name: 1, "_id": 0})[:n])
            data = [d[name] for d in data]

            if len(data) < n:
                data = list(islice(cycle(data), n))

            return data

        return _pd.DataFrame({
            c: get_sampledata(c) for c in self.columns
        })

    @property
    def dtypes(self):
        sample_df = self.example(10)
        return sample_df.dtypes
