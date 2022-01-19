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
            raise MongoDfException(
                "Filter inversion only possible for single objects!")

        new_filter = {k: {self.inversion_map[ik]: iv for ik, iv in v.items(
        )} for k, v in self.config.items()}

        return Filter(self._mf, new_filter)

    def __and__(self, filter_b):
        if self._mf._collection != filter_b._mf._collection:
            raise MongoDfException(
                "You cannot mix DataFrames during filtering")

        if len(self.config) > 0:
            if len(filter_b.config) == 0:
                return Filter(self._mf, self.config)

            new_filter = {"$and": [self.config.copy(), filter_b.config.copy()]}
            return Filter(self._mf, new_filter)
        else:
            return Filter(self._mf, filter_b.config)

    def __or__(self, filter_b):
        if self._mf._collection != filter_b._mf._collection:
            raise MongoDfException(
                "You cannot mix DataFrames during filtering")

        if len(self.config) > 0:
            if len(filter_b.config) == 0:
                return Filter(self._mf, self.config)

            new_filter = {"$or": [self.config.copy(), filter_b.config.copy()]}
            return Filter(self._mf, new_filter)
        else:
            return Filter(self._mf, filter_b.config)
