from .filter import Filter
from .column import Column
from .exception import MongoDfException
import pandas as _pd
import numpy as _np
from itertools import cycle, islice
from pymongo import MongoClient


class DataFrame():

    def __init__(self, _host, _database, _collection, _columns,
                 list_columns=[], filter=None, array_expand=True):

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

    def __getitem__(self, key):
        if isinstance(key, Filter):
            return DataFrame(
                self._host,
                self._database,
                self._collection,
                self.columns,
                filter=key.__and__(self._filter),
                array_expand=self._array_expand,
                list_columns=self.list_columns
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
                list_columns=self.list_columns
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

    def compute(self, **kwargs):
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
                        return _pd.DataFrame(d)
                    except:
                        return _pd.DataFrame(d, index=[0])

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

        with MongoClient(self._host) as client:

            db = client.get_database(self._database)
            coll = db.get_collection(self._collection)

            def get_sampledata(name):
                data = list(coll.find(
                    {name: {"$exists": True}}, {name: 1, "_id": 0})[:n])
                data = [d[name] for d in data]

                if len(data) < n:
                    data = list(islice(cycle(data), n))

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

    @property
    def dtypes(self):
        sample_df = self.example(20).fillna(axis=0, method="ffill").fillna(axis=0, method="bfill")
        return sample_df.dtypes

    def __get_meta_entry(self, key, val, older_than=None, old_values=None):
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
                    print(ex)
                    return parse_object_cat(key)
        except:
            return {"error": True}


    def update_meta_cache(self):
        from numpy import dtype

        with MongoClient(self._host) as client:
            db = client.get_database(self._database)
            meta_coll = db.get_collection("__" + self._collection + "_meta")

            # get the old metadata
            old_data = list(meta_coll.find({}))
            old_data = {el["name"]: el for el in old_data}    

            # use the old metadata to reconstruct self.dtypes.to_dict()
            dtypes_dict = {k: {
                "numerical": dtype('float64'),
                "bool": dtype('bool'),
                "categorical": dtype('O'),
                "temporal": dtype('<M8[ns]'),
            }[v['type']]for k,v in old_data.items()}

            # if there are some missing cols use the old version to 
            new_dtypes_dict = self.__getitem__([c for c in self.columns if c not in dtypes_dict]).dtypes.to_dict()
            print("new cols", new_dtypes_dict)
            dtypes_dict.update(new_dtypes_dict)

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
                    meta_coll.delete_one({"name": k})

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

                meta_coll.find_one_and_update(
                    {"name": k},
                    {"$set": new_entry},
                    upsert=True
                )


    def update_meta_cache_all(self):

        with MongoClient(self._host) as client:
            db = client.get_database(self._database)
            meta_coll = db.get_collection("__" + self._collection + "_meta")

            meta_coll.drop()

            meta_coll.insert_many([
                {
                    "name": k, **self.__get_meta_entry(k, val)
                }for k, val in self.dtypes.to_dict().items()
            ])

    def get_meta(self):
        with MongoClient(self._host) as client:
            db = client.get_database(self._database)
            meta_coll = db.get_collection("__" + self._collection + "_meta")

            meta = {el["name"]: el for el in meta_coll.find({}, {"_id": 0})}

            if len(meta) > 0:
                return meta

        return {
            k: self.__get_meta_entry(k, val)
            for k, val in self.dtypes.to_dict().items()
        }
