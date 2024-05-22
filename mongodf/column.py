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



from .filter import Filter
import numpy as _np
import pandas as _pd
import datetime
from pymongo import MongoClient


class Column():
    """
    A class representing a column in a DataFrame-like object, enabling operations and filters on MongoDB collections.

    Parameters:
    -----------
    dataframe : DataFrame
        The DataFrame-like object this column belongs to.
    
    name : str
        The name of the column.

    Methods:
    --------
    _query_value(qt, value):
        Internal method to format a query value for MongoDB.

    isin(array):
        Returns a Filter object to check if column values are in the given array.

    __eq__(value):
        Returns a Filter object to check if column values are equal to the given value.

    __ne__(value):
        Returns a Filter object to check if column values are not equal to the given value.

    __ge__(value):
        Returns a Filter object to check if column values are greater than or equal to the given value.

    __gt__(value):
        Returns a Filter object to check if column values are greater than the given value.

    __lt__(value):
        Returns a Filter object to check if column values are less than the given value.

    __le__(value):
        Returns a Filter object to check if column values are less than or equal to the given value.

    unique():
        Returns an array of unique values in the column.

    agg(types):
        Returns a Pandas Series containing aggregate values (mean, median, min, max) for the column.

    """

    def __init__(self, dataframe, name):
        """
        Initialize a Column object.

        Parameters:
        -----------
        dataframe : DataFrame
            The DataFrame-like object this column belongs to.

        name : str
            The name of the column.
        """        
        self._mf = dataframe
        self._name = name

    def _query_value(self, qt, value):
        """
        Internal method to format a query value for MongoDB.

        Parameters:
        -----------
        qt : str
            The MongoDB query operator (e.g., '$eq', '$in').

        value : any
            The value to query.

        Returns:
        --------
        dict
            A MongoDB query condition.
        """        

        if isinstance(value, _np.datetime64):
            value = _pd.Timestamp(value).to_pydatetime()

        if self._mf._array_expand and self._name in self._mf.list_columns:
            return {"$elemMatch": {qt: value}}
        return {qt: value}

    def isin(self, array):
        """
        Create a Filter object to check if column values are in the given array.

        Parameters:
        -----------
        array : list
            The array of values to check against.

        Returns:
        --------
        Filter
            A Filter object with the specified condition.
        """        
        return Filter(self._mf, {self._name: self._query_value("$in", array)},
         lambda x: x[self._name].isin(array)  if self._name in x.columns else True)

    def __eq__(self, value):
        """
        Create a Filter object to check if column values are equal to the given value.

        Parameters:
        -----------
        value : any
            The value to compare against.

        Returns:
        --------
        Filter
            A Filter object with the specified condition.
        """        
        return Filter(self._mf, {self._name: self._query_value("$eq", value)},
         lambda x: x[self._name] == value if self._name in x.columns else True)

    def __ne__(self, value):
        """
        Create a Filter object to check if column values are not equal to the given value.

        Parameters:
        -----------
        value : any
            The value to compare against.

        Returns:
        --------
        Filter
            A Filter object with the specified condition.
        """        
        return Filter(self._mf, {self._name: self._query_value("$ne", value)},
         lambda x: x[self._name] != value  if self._name in x.columns else True)

    def __ge__(self, value):
        """
        Create a Filter object to check if column values are greater than or equal to the given value.

        Parameters:
        -----------
        value : any
            The value to compare against.

        Returns:
        --------
        Filter
            A Filter object with the specified condition.
        """        
        return Filter(self._mf, {self._name: self._query_value("$gte", value)},
         lambda x: x[self._name] >= value  if self._name in x.columns else True)

    def __gt__(self, value):
        """
        Create a Filter object to check if column values are greater than the given value.

        Parameters:
        -----------
        value : any
            The value to compare against.

        Returns:
        --------
        Filter
            A Filter object with the specified condition.
        """        
        return Filter(self._mf, {self._name: self._query_value("$gt", value)},
         lambda x: x[self._name] > value  if self._name in x.columns else True)

    def __lt__(self, value):
        """
        Create a Filter object to check if column values are less than the given value.

        Parameters:
        -----------
        value : any
            The value to compare against.

        Returns:
        --------
        Filter
            A Filter object with the specified condition.
        """        
        return Filter(self._mf, {self._name: self._query_value("$lt", value)},
         lambda x: x[self._name] < value  if self._name in x.columns else True)

    def __le__(self, value):
        """
        Create a Filter object to check if column values are less than or equal to the given value.

        Parameters:
        -----------
        value : any
            The value to compare against.

        Returns:
        --------
        Filter
            A Filter object with the specified condition.
        """        
        return Filter(self._mf, {self._name: self._query_value("$lte", value)},
         lambda x: x[self._name] <= value  if self._name in x.columns else True)

    def unique(self):
        """
        Get the unique values in the column.

        Returns:
        --------
        numpy.ndarray
            An array of unique values in the column.
        """        

        with MongoClient(self._mf._host) as client:
            db = client.get_database(self._mf._database)
            coll = db.get_collection(self._mf._collection)
            return _np.array(
                coll.distinct(
                    self._name,
                    self._mf._filter.config
                )
            )

    def agg(self, types):
        """
        Aggregate values in the column.

        Parameters:
        -----------
        types : str or list
            The types of aggregation to perform ('mean', 'median', 'min', 'max').

        Returns:
        --------
        pandas.Series
            A Series containing the aggregated values for the column.
        """        
        if isinstance(types, str):
            types = [types]

        pmap = {
            "mean": "$avg",
            "median": "$avg",
            "min": "$min",
            "max": "$max",
        }

        with MongoClient(self._mf._host) as client:
            db = client.get_database(self._mf._database)
            coll = db.get_collection(self._mf._collection)


            res = coll.aggregate([
                {"$match": self._mf._filter.config},
                {"$group": {
                    "_id": None,
                    **{t: {pmap[t]: f"${self._name}"} for t in types}
                }}
            ])

            res = list(res)
            if len(res) > 0:           
                res = res[0]
            else:
                res = {"mean": None, "median": None, "min": None, "max": None}

        if res["median"] is None and "min" in res and res["min"] is not None:
            res["median"] = res["min"]
        if res["median"] is None and "max" in res and res["max"] is not None:
            res["median"] = res["max"]

        def flatten(t, el):
            if isinstance(el, list):
                a = _np.array(el)
                a = a[_pd.notnull(a)]
                return getattr(_np, t)(a)
            return el

        res = {k: flatten(k, v) for k, v in res.items() if k != "_id"}

        return _pd.Series(res, name=self._name)
