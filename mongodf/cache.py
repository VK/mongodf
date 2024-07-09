import pandas as _pd
import numpy as _np
from pymongo import MongoClient
import json
import hashlib
import os

CACHE_HOST = os.getenv("CACHE_HOST", "mongodb://localhost:27017")
CACHE_DATABASE = os.getenv("CACHE_DATABASE", "mongodfcache")
CACHE_EXPIRE_AFTER_SECONDS = int(os.getenv("CACHE_EXPIRE_AFTER_SECONDS", '86400'))


def get_meta(df, large_threshold=1000):
    """
    extract the metadata from a dataframe needed to hand over to the Filter
    """
    from numpy import dtype
    import pandas as _pd

    def parse_object_cat(key):
        try:
            cat = df[key].unique()
            if len(cat) > large_threshold:
                return {"type": "categorical", "large": True, "cat": []}
            return {"type": "categorical", "cat": cat.tolist()}
        except:
            return {"type": "categorical", "large": True, "cat": []}

    def parse(key, val):
        if isinstance(val, _pd.CategoricalDtype):
            # pandas special cat var

            if len(val.categories) > large_threshold:
                return {"type": "categorical", "large": True, "cat": []}
            return {"type": "categorical", "cat": val.categories.tolist()}
        elif val == dtype("O"):
            # conventional string mixed object cat var
            return parse_object_cat(key)

        elif val == dtype("bool"):
            return {"type": "bool"}
        elif "time" in str(val):
            return {
                "type": "temporal",
                **df[key].agg(["median", "min", "max"]).T.to_dict(),
            }
        elif val == dtype("datetime64[ns]"):
            return {
                "type": "temporal",
                **df[key].agg(["median", "min", "max"]).T.to_dict(),
            }
        else:
            try:
                return {
                    "type": "numerical",
                    **df[key].agg(["median", "min", "max"]).T.to_dict(),
                }
            except:
                return parse_object_cat(key)

    return {k: parse(k, val) for k, val in df.dtypes.to_dict().items()}





class MongoDFCache:
    def __init__(
        self,
        host=CACHE_HOST,
        database=CACHE_DATABASE,
        data_collection="data",
        meta_collection="meta",
        info_collection="info",
        _data_frame_id="__data_frame_id",
        expire_after_seconds=CACHE_EXPIRE_AFTER_SECONDS,
    ):

        self._host = host
        self._database = database
        self._data_collection = data_collection
        self._meta_collection = meta_collection
        self._info_collection = info_collection

        self._client = MongoClient(host)
        self._db = self._client[database]
        self._data = self._db[data_collection]
        self._meta = self._db[meta_collection]
        self._info = self._db[info_collection]
        self._data_frame_id = _data_frame_id

        # create expiry index if it doesn't exist
        self._data.create_index("createdAt", expireAfterSeconds=expire_after_seconds)
        # create index for the data_frame_id if it doesn't exist
        self._data.create_index(self._data_frame_id)
        # create index for the data_frame_id if it doesn't exist
        self._meta.create_index(self._data_frame_id)
        # create expiry index if it doesn't exist
        self._meta.create_index("createdAt", expireAfterSeconds=expire_after_seconds)

        # create index for the data_frame_id if it doesn't exist
        self._info.create_index(self._data_frame_id, unique=True)
        # create expiry index if it doesn't exist
        self._info.create_index("createdAt", expireAfterSeconds=expire_after_seconds)


    def get_frame_id(self, identifier):
        if not isinstance(identifier, dict):
            frame_id = hashlib.sha256(
                json.dumps(identifier, sort_keys=True).encode()
            ).hexdigest()
        else:
            frame_id = hashlib.sha256(identifier.encode()).hexdigest()
        return frame_id
    

    def is_frame_id(self, identifier):
        return len(identifier) == 64 and all([c in "0123456789abcdef" for c in identifier])

    def cache_dataframe(self, dataframe, identifier=None, array_group=True):
            """Put a dataframe into the cache

            Parameters:
            - identifier: str | object
                The identifier for the dataframe
            - dataframe: pandas DataFrame
                The dataframe to cache
            - array_group: list | bool
                If the dataframe is grouped, the columns to group by. If the dataframe is not grouped, set to False

            Returns:
            - frame_id: str
                The unique identifier for the cached dataframe
            """

            bad_columns = []

            if identifier is None:
                identifier = "_".join([
                    "DF len(%d)" % len(dataframe),
                    *sorted([str(n) for n in dataframe.columns]),
                    # timestamp
                    str(_pd.Timestamp.now())
                ])
                

            if isinstance(array_group, bool):
                if array_group is False:
                    array_group = []
                else:

                    array_group = []
                    # find suitable columns to group by. conditions
                    # the column is categorical
                    # the has less unique values than the number of rows
                    for key, val in dataframe.dtypes.to_dict().items():
                        try:
                            if val == _pd.CategoricalDtype or val == object:
                                if len(dataframe[key].unique()) < dataframe.shape[0] * 0.9:
                                    array_group.append(key)
                        except:
                            bad_columns.append(key)
                            pass


                
                    

            # need to make a copy of the dataframe to avoid modifying the original
            dataframe = dataframe.copy()

            # transform every temporal column to datetime64
            for key, val in dataframe.dtypes.to_dict().items():
                if isinstance(val, (_pd.Timestamp, _pd.Timedelta, _np.datetime64)):
                    dataframe[key] = _pd.to_datetime(dataframe[key])

            # if the identifier is a dictionary, we need to convert it to a string
            frame_id = self.get_frame_id(identifier)

            # drop the data matching the _data_frame_id from data and meda
            self._data.delete_many({self._data_frame_id: frame_id})
            self._meta.delete_many({self._data_frame_id: frame_id})

            # get the current timestamp
            insert_timestamp = _pd.Timestamp.now()


            # compute the meta data
            meta = get_meta(dataframe)
            for key, val in meta.items():
                val = {**val, "name": key, self._data_frame_id: frame_id, "createdAt": insert_timestamp}
                self._meta.insert_one(val)

            # remove bad columns from the array_group and from the dataframe
            array_group = list(set(array_group) - set(bad_columns))
            dataframe = dataframe.drop(columns=bad_columns)
            # remove colums with nan values from the array_group
            cols_with_nans = dataframe.columns[dataframe.isna().any()].tolist()
            array_group = list(set(array_group) - set(cols_with_nans))
            info = {
                "name": identifier,
                "createdAt": insert_timestamp,
                self._data_frame_id: frame_id,
                "array_group": array_group,
                "bad_columns": bad_columns,
                "cols_with_nans": cols_with_nans,
            }
            self._info.find_one_and_update(
                {self._data_frame_id: frame_id}, {"$set": info}, upsert=True
            )        




            # add the _data_frame_id to the dataframe
            dataframe[self._data_frame_id] = frame_id
            # add the createdAt column to the dataframe
            dataframe["createdAt"] = insert_timestamp

            if len(array_group) == 0:
                data = dataframe.to_dict(orient="records")
                # insert the _data_frame_id into
                self._data.insert_many(data)
            else:
                data = dataframe.groupby(array_group).apply(
                    lambda x: x.to_dict(orient="list")
                )
                bulk_data = []
                for group, records in data.items():
                    if isinstance(group, tuple):
                        group = dict(zip(array_group, group))
                    # condense the records. If all entries in a list are the same, we can use a scalar
                    records = {k: v[0] if len(set(v)) == 1 else v for k, v in records.items()}
                    
                    bulk_data.append({**group, **records})
                self._data.insert_many(bulk_data)




            return frame_id
    


    def get_dataframe(self, identifier):
            """
            Get a dataframe from the cache.

            Parameters:
            - identifier: str | object
                The identifier for the dataframe.

            Returns:
            - mf: DataFrame
                The dataframe retrieved from the cache.
            """

            from . import DataFrame
            from .filter import Filter

            # check if the identifier is already a frame_id
            if self.is_frame_id(identifier):
                frame_id = identifier
            else:
                frame_id = self.get_frame_id(identifier)

            filter = {self._data_frame_id: frame_id}

            columns = [n["name"] for n in self._meta.find(filter, {"name": 1, "_id": 0})]

            info = self._info.find_one(filter)
            array_group = info.get("array_group", [])

            mf = DataFrame(
                self._host,
                self._database,
                self._data_collection,
                [*columns, self._data_frame_id],
                filter=None,
                array_expand=len(array_group) > 0,
            )
            mf._filter = Filter(mf, {})
            mf = mf[mf[self._data_frame_id] == frame_id]
            mf = mf[columns]

            # set the meta
            mf.__meta = {n["name"]: n for n in self._meta.find(filter)}



            # update the access timestamp
            # we use createdAt as access timestamp, to prevent the data from being deleted
            access_timestamp = _pd.Timestamp.now()
            self._info.find_one_and_update(
                filter, {"$set": {"createdAt": access_timestamp}}
            )
            self._meta.update_many(filter, {"$set": {"createdAt": access_timestamp}})
            self._data.update_many(filter, {"$set": {"createdAt": access_timestamp}})


            return mf
