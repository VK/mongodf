# Copyright 2024 Viktor Krückl. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================



from .exception import MongoDfException
import numpy as _np


class Filter():
    """
    A class to represent a filter for querying a DataFrame from a MongoDB collection.

    Parameters:
    -----------
    dataframe : DataFrame
        The DataFrame to which the filter is applied.
    config : dict
        The configuration of the filter, represented as a MongoDB query.
    func : function, optional
        A function to be applied to the filter results. Default is an identity function.

    Methods:
    --------
    __invert__():
        Inverts the filter by swapping query operators with their opposites.
    __and__(filter_b):
        Combines two filters using a logical AND operation.
    __or__(filter_b):
        Combines two filters using a logical OR operation.
    """    


    """A mapping of MongoDB query operators to their inverses.
    """
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

    def __init__(self, dataframe, config, func=lambda x: x):
        """
        Initializes a Filter object.

        Parameters:
        -----------
        dataframe : DataFrame
            The DataFrame to which the filter is applied.
        config : dict
            The configuration of the filter, represented as a MongoDB query.
        func : function, optional
            A function to be applied to the filter results. Default is an identity function.
        """        
        self._mf = dataframe
        self.config = config
        self.func = func

    def __invert__(self):
        """
        Inverts the filter by swapping query operators with their opposites.

        Returns:
        --------
        Filter
            A new Filter object with inverted query operators.

        Raises:
        -------
        MongoDfException
            If the filter contains more than one query element.
        """        

        if len(self.config) != 1:
            raise MongoDfException(
                "Filter inversion only possible for single objects!")

        def sub_invert(ele):
            if "$elemMatch" in ele:
                return {"$elemMatch": sub_invert(ele["$elemMatch"])}
            else:
                if len(ele) != 1:
                    raise MongoDfException(
                        "Filter inversion only possible for single objects!")
                return {self.inversion_map[k]: v for k, v in ele.items()}

        new_filter = {k: sub_invert(v) for k, v in self.config.items()}

        return Filter(self._mf, new_filter, lambda x: _np.invert(self.func(x)))

    def __and__(self, filter_b):
        """
        Combines two filters using a logical AND operation.

        Parameters:
        -----------
        filter_b : Filter
            The other filter to combine with.

        Returns:
        --------
        Filter
            A new Filter object combining the two filters with a logical AND.

        Raises:
        -------
        MongoDfException
            If the filters belong to different DataFrames.
        """        
        if self._mf._collection != filter_b._mf._collection:
            raise MongoDfException(
                "You cannot mix DataFrames during filtering")

        if len(self.config) > 0:
            if len(filter_b.config) == 0:
                return Filter(self._mf, self.config, self.func)

            if self._mf._array_expand:

                new_filter = filter_b.config.copy()
                for k, v in self.config.items():
                    if k in new_filter:
                        if "$elemMatch" in new_filter[k] and "$elemMatch" in v:
                            new_filter[k]["$elemMatch"].update(v["$elemMatch"])
                        else:
                            new_filter[k].update(v)
                    else:
                        new_filter[k] = v

            else:
                new_filter = filter_b.config.copy()
                for k, v in self.config.items():
                    if k in new_filter:
                        new_filter[k].update(v)
                    else:
                        new_filter[k] = v

            return Filter(self._mf, new_filter, lambda x: _np.logical_and(self.func(x), filter_b.func(x)))
        else:
            return Filter(self._mf, filter_b.config, filter_b.func)

    def __or__(self, filter_b):
        """
        Combines two filters using a logical OR operation.

        Parameters:
        -----------
        filter_b : Filter
            The other filter to combine with.

        Returns:
        --------
        Filter
            A new Filter object combining the two filters with a logical OR.

        Raises:
        -------
        MongoDfException
            If the filters belong to different DataFrames.
        """        
        if self._mf._collection != filter_b._mf._collection:
            raise MongoDfException(
                "You cannot mix DataFrames during filtering")

        if len(self.config) > 0:
            if len(filter_b.config) == 0:
                return Filter(self._mf, self.config, self.func)

            new_filter = {"$or": [self.config.copy(), filter_b.config.copy()]}
            return Filter(self._mf, new_filter, lambda x: _np.logical_or(self.func(x), filter_b.func(x)))
        else:
            return Filter(self._mf, filter_b.config, filter_b.func)
