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
from .column import Column
from .exception import MongoDfException
from .utils import flatten_dict
import pandas as _pd
import numpy as _np
from itertools import cycle, islice
from pymongo import MongoClient


class DataFrame():
    """
    A class to represent a DataFrame for MongoDB collections with extended functionality for querying and metadata management.

    Parameters:
    -----------
    _host : str
        The MongoDB host.
    _database : str
        The name of the database.
    _collection : str
        The name of the collection.
    _columns : list
        The list of columns to include in the DataFrame.
    list_columns : list or set, optional
        A list or set of columns that are considered to be lists and need special handling. Default is an empty list.
    filter : Filter, optional
        A Filter object representing the query filter. Default is None.
    array_expand : bool, optional
        Whether to expand arrays into separate rows. Default is True.
    
    Attributes:
    -----------
    _host : str
        The MongoDB host.
    _database : str
        The name of the database.
    _collection : str
        The name of the collection.
    columns : list
        The list of columns included in the DataFrame.
    _filter : Filter
        The query filter for the DataFrame.
    _array_expand : bool
        Whether to expand arrays into separate rows.
    list_columns : set
        A set of columns that are considered to be lists and need special handling.
    large_threshold : int
        A threshold for determining when a categorical column is large. Default is 1000.
    _update_col : str
        The name of the column used for tracking updates. Default is "__UPDATED".
    """    

    def __init__(self, _host, _database, _collection, _columns,
                 list_columns=[], filter=None, array_expand=True,
                 _meta_coll=None
                 ):

        self._host = _host
        self._database = _database
        self._collection = _collection
        self.columns = _columns
        self._filter = filter
        self._array_expand = array_expand
        if isinstance(list_columns, list):
            self.list_columns = set(list_columns)
        elif isinstance(list_columns, set):
            self.list_columns = list_columns
        else:
            self.list_columns = set([])

        # flag to determine when a categorical column is large
        self.large_threshold = 1000
        self._update_col = "__UPDATED"
        self.__meta = None

        # keep track of the mongo meta collection
        self._meta_coll = _meta_coll

    def __getitem__(self, key):
        """
        Retrieve a subset of the DataFrame based on the key.

        Parameters:
        -----------
        key : str, list, or Filter
            If a string, retrieves the column with that name.
            If a list, retrieves a DataFrame with only the specified columns.
            If a Filter, retrieves a DataFrame filtered by the specified filter.

        Returns:
        --------
        DataFrame or Column
            A new DataFrame or Column based on the key.

        Raises:
        -------
        MongoDfException
            If the specified columns are not available.
        """        
        if isinstance(key, Filter):
            return DataFrame(
                self._host,
                self._database,
                self._collection,
                self.columns,
                filter=key.__and__(self._filter),
                array_expand=self._array_expand,
                list_columns=self.list_columns,
                _meta_coll=self._meta_coll,
            )

        if isinstance(key, list):
            if not all([k in self.columns for k in key]):
                raise MongoDfException("Not all columns available")

            return DataFrame(
                self._host,
                self._database,
                self._collection,
                key,
                filter=self._filter,
                array_expand=self._array_expand,
                list_columns=self.list_columns,
                _meta_coll=self._meta_coll,
            )

        if key in self.columns:
            return Column(self, key)
        else:
            raise MongoDfException(f"column {key} not found!")

    @property
    def dtypes(self):
        """
        Get the data types of the columns in the DataFrame.

        Returns:
        --------
        pandas.Series
            A Series with the data types of the columns.
        """        
        sample_df = self.example(20).ffill(axis=0).bfill(axis=0)
        return sample_df.dtypes

    def __getattr__(self, key):
        """
        Get a column by name as an attribute.

        Parameters:
        -----------
        key : str
            The name of the column.

        Returns:
        --------
        Column
            The Column object for the specified column.

        Raises:
        -------
        MongoDfException
            If the column is not found.
        """        
        if key == "dtypes":
            sample_df = self.example(20).ffill(axis=0).bfill(axis=0)
            return sample_df.dtypes            
            
        if key in self.columns:
            return Column(self, key)
        else:
            raise MongoDfException(f"column {key} not found!")

    def compute(self, **kwargs):
        """
        Compute the DataFrame by querying the MongoDB collection.

        Parameters:
        -----------
        kwargs : dict
            Additional parameters for the computation.

        Returns:
        --------
        pandas.DataFrame
            The resulting DataFrame after querying the MongoDB collection.
        """        
        colfilter = {"_id": 0}
        colfilter.update(
            {c: 1 for c in list(set([*self.columns, *self._filter.config.keys()]))})

        with MongoClient(self._host) as client:

            db = client.get_database(self._database)
            coll = db.get_collection(self._collection)

            query_data = coll.find(
                self._filter.config,
                colfilter
            )

            if self._array_expand:

                def create_df(d):
                    try:
                        return _pd.DataFrame(flatten_dict(d))
                    except:
                        return _pd.DataFrame(flatten_dict(d), index=[0])

                try:
                    res_df = _pd.concat([
                        create_df(d) for d in query_data
                    ])
                except ValueError:
                    res_df = _pd.DataFrame()

                if len(self._filter.config) != 0:
                    res_df = res_df[self._filter.func(res_df)]

                res_df = res_df[[
                    c for c in self.columns if c in res_df.columns]]

                res_df = res_df.copy()

                missing_cols = [
                    cc for cc in self.columns if cc not in res_df.columns]
                res_df = _pd.concat(
                    [
                        res_df,
                        _pd.DataFrame(
                            [[_np.nan]*len(missing_cols)],
                            index=res_df.index,
                            columns=missing_cols
                        )
                    ], axis=1
                )

                return res_df
            
            res_df = _pd.DataFrame(list(query_data))
            missing_cols = [cc for cc in self.columns if cc not in res_df.columns]
            if len(missing_cols) == 0:
                return res_df
            
            res_df = _pd.concat(
                [
                    res_df,
                    _pd.DataFrame(
                        [[_np.nan]*len(missing_cols)],
                        index=res_df.index,
                        columns=missing_cols
                    )
                ], axis=1
            )       

            return res_df     
        

    

    def example(self, n=20):
        """
        Retrieve an example of the DataFrame with a specified number of rows.

        Parameters:
        -----------
        n : int, optional
            The number of rows to retrieve. Default is 20.

        Returns:
        --------
        pandas.DataFrame
            A DataFrame with example data.
        """        

        with MongoClient(self._host) as client:

            db = client.get_database(self._database)
            coll = db.get_collection(self._collection)

            def get_sampledata(name):
                try:
                    data = list(coll.find({name: {"$exists": True}}, {name: 1, "_id": 0}).limit(n))
                    
                    data = flatten_dict(data)
                    data = [d[name] for d in data]

                    if len(data) < n and len(data) > 0:
                        data = list(islice(cycle(data), n))
                except:
                    print("error example", name)
                    data = []

                if len(data) == 0:
                    data = [_np.nan]*n

                return data

            def filter_to_single(data):
                if isinstance(data, list):
                    sub = [v for v in data if v == v]
                    if len(sub) > 0:
                        return sub[0]
                    else:
                        return data[0]
                else:
                    return data

            res = {
                c: get_sampledata(c) for c in self.columns
            }
            out = _pd.DataFrame(res)
            if self._array_expand:
                for c in out.columns:
                    if any([isinstance(d, list) for d in out[c].values]):
                        self.list_columns.add(c)
                        out[c] = out[c].map(filter_to_single)

            return out



    def __get_meta_entry(self, key, val, older_than=None, old_values=None):
        """
        Get metadata entry for a specific column.

        Parameters:
        -----------
        key : str
            The column name.
        val : dtype
            The data type of the column.
        older_than : datetime, optional
            A timestamp to filter for updated values. Default is None.
        old_values : dict, optional
            Previous metadata values. Default is None.

        Returns:
        --------
        dict
            The metadata entry for the column.
        """        
        from numpy import dtype

        def parse_object_cat(key):

            if old_values:
                if "large" in old_values:
                    return {
                        "type": "categorical",
                        "large": True,
                        "cat": []
                    }

            if older_than and self._update_col in self.columns:
                cat = self[self[self._update_col] > older_than][key].unique()
                cat = list(set([*cat, *old_values["cat"]]))
            else:
                cat = self[key].unique()

            if len(cat) > self.large_threshold:
                return {
                    "type": "categorical",
                    "large": True,
                    "cat": []
                }
            return {
                "type": "categorical",
                "cat": cat if isinstance(cat, list) else cat.tolist()
            }

        def get_updated_agg_data(mdf, key):
            if older_than and self._update_col in self.columns:
                try:
                    query_res = mdf[self[self._update_col] > older_than][key].agg(["median", "min", "max"]).T.to_dict()
                except:
                    print("exc ", key)
                    query_res = {}
                if "median" in query_res and query_res["median"]:
                    query_res["min"] = min(old_values["min"], query_res["min"])
                    query_res["max"] = max(old_values["max"], query_res["max"])
                else:
                    query_res={k: old_values[k] for k in ["median", "min", "max"]}
            else:
                query_res = mdf[key].agg(["median", "min", "max"]).T.to_dict() 

            return query_res

        try:
            if isinstance(val, _pd.CategoricalDtype):
                if len(val.categories) > self.large_threshold:
                    return {
                        "type": "categorical",
                        "large": True,
                        "cat": []
                    }
                return {
                    "type": "categorical",
                    "cat": val.categories.tolist()
                }

            elif val == dtype('O'):
                return parse_object_cat(key)

            elif val == dtype('bool'):
                return {
                    "type": "bool"
                }
            elif "time" in str(val):
                query_res = get_updated_agg_data(self, key)

                return {"type": "temporal", **query_res}
            else:
                try:
                    query_res = get_updated_agg_data(self[self[key] > -1.0e99], key)

                    return {"type": "numerical", **query_res}
                except:
                    return parse_object_cat(key)
        except:
            return {"error": True}


    def update_meta_cache(self):
        """
        Update the metadata cache for the DataFrame.
        """
        from numpy import dtype

        with MongoClient(self._host) as client:
            db = client.get_database(self._database)
            if not self._meta_coll:
                self._meta_coll = db.get_collection("__" + self._collection + "_meta")

            # get the old metadata
            old_data = list(self._meta_coll.find({}))
            old_data = {el["name"]: el for el in old_data}   

            # use the old metadata to reconstruct self.dtypes.to_dict()
            dtypes_dict = {k: {
                "numerical": dtype('float64'),
                "bool": dtype('bool'),
                "categorical": dtype('O'),
                "temporal": dtype('<M8[ns]'),
            }[v['type']]for k,v in old_data.items() if "type" in v}

            print(dtypes_dict)

            # if there are some missing cols use the old version to 
            new_dtypes_dict = self.__getitem__([c for c in self.columns if c not in dtypes_dict]).dtypes.to_dict()
            print("new cols", new_dtypes_dict)
            dtypes_dict.update(new_dtypes_dict)

            dtypes_dict = {k: v for k, v in dtypes_dict.items() if k == k}

            older_than = None
            if self._update_col in self.columns:
                older_than = old_data[self._update_col]["max"] if self._update_col in old_data else None
                if older_than:
                    print("last_updated", older_than)
                    try:
                        new_entries = self[self[self._update_col] > older_than][[self._update_col]].compute()
                    except:
                        new_entries = []
                    if len(new_entries) == 0:
                        print("no new documents --> no update needed")
                        return
                    print("number new documents", len(new_entries))

            # update the metadata collection
            for k, val in dtypes_dict.items():

                if k not in self.columns:
                    self._meta_coll.delete_one({"name": k})

                if k in self.columns and k in old_data:
                      if "large" in old_data[k]:
                            continue

                if k in old_data and older_than:
                    new_entry = {
                         "name": k, **self.__get_meta_entry(k, val, older_than, old_data[k])
                    }
                else:
                    new_entry = {
                         "name": k, **self.__get_meta_entry(k, val)
                    }

                self._meta_coll.find_one_and_update(
                    {"name": k},
                    {"$set": new_entry},
                    upsert=True
                )


    def update_meta_cache_all(self):
        """
        Update the entire metadata cache for the DataFrame.
        """        

        with MongoClient(self._host) as client:
            db = client.get_database(self._database)
            if not self._meta_coll:
                self._meta_coll = db.get_collection("__" + self._collection + "_meta")

            self._meta_coll.drop()

            self._meta_coll.insert_many([
                {
                    "name": k, **self.__get_meta_entry(k, val)
                }for k, val in self.dtypes.to_dict().items()
            ])

    def get_meta(self):
        """
        Get the metadata for the DataFrame.

        Returns:
        --------
        dict
            A dictionary with metadata for each column.
        """
        if self.__meta:
            return self.__meta

        with MongoClient(self._host) as client:
            db = client.get_database(self._database)
            if not self._meta_coll:
                self._meta_coll = db.get_collection("__" + self._collection + "_meta")

            meta = {el["name"]: el for el in self._meta_coll.find({}, {"_id": 0})}

            if len(meta) > 0:
                self.__meta = meta
                return meta

        self.__meta = {
            k: self.__get_meta_entry(k, val)
            for k, val in self.dtypes.to_dict().items()
        }

        return self.__meta
