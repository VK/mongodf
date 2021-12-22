from .exception import MongoDfException

class Filter():

    inversion_map = {
        "$in": "$nin",
        "$nin": "$in",
        "$gt": "$lte",
        "$lt": "$gte",
        "$gte": "$lt",
        "$lte": "$gt",
        "$eq": "$ne",
        "$ne": "$eq"
    }

    def __init__(self, dataframe, config):
        self._mf = dataframe
        self.config = config

    def __invert__(self):
        if len(self.config) != 1:
            raise MongoDfException("Filter inversion only possible for single objects!")

        new_filter = {k: {self.inversion_map[ik]: iv for ik, iv in v.items(
        )} for k, v in self.config.items()}

        return Filter(self._mf, new_filter)

    def __and__(self, filter_b):
        if self._mf != filter_b._mf:
            raise MongoDfException(
                "You cannot mix DataFrames during filtering")

        new_filter = self.config.copy()
        new_filter.update(filter_b.config)
        return Filter(self._mf, new_filter)