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



def flatten_dict(d, parent_key='', sep='.'):
    """
    Flatten a nested dictionary into dot notation.

    Parameters:
    -----------
    d : dict
        The nested dictionary to flatten.
    
    parent_key : str, optional
        The base key to use for the flattened dictionary. Default is an empty string.
    
    sep : str, optional
        The separator to use between keys. Default is '.'.

    Returns:
    --------
    dict
        A dictionary with flattened keys using dot notation.

    Notes:
    ------
    This function recursively flattens a nested dictionary. If a value in the dictionary is another dictionary, it will
    concatenate the keys using the specified separator. If a value is a list, it will recursively flatten each element 
    of the list.
    """
    if isinstance(d, dict):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    elif isinstance(d, list):
        return [flatten_dict(el) for el in d]
    else:
        return d
    


def get_all_columns_of(coll, dict_expand_level=0):
    """
    Retrieve all unique column names from a MongoDB collection, expanding nested fields up to a specified level.

    Parameters:
    -----------
    coll : pymongo.collection.Collection
        The MongoDB collection from which to retrieve column names.
    
    dict_expand_level : int, optional
        The level of nested dictionary expansion. Default is 0.

    Returns:
    --------
    list
        A list of unique column names in dot notation.

    Notes:
    ------
    This function uses MongoDB's aggregation framework to project and unwind nested fields up to the specified 
    dict_expand_level. It then collects all unique keys from the documents in the collection.
    """    

    # Initialize the aggregation pipeline
    pipeline = [
        {"$project": {"data0": {"$objectToArray": "$$ROOT"}}},
        {"$unwind": "$data0"},
        {"$project": {"k": "$data0.k", "v": "$data0.v"}}
    ]

    # Function to recursively handle nested fields up to dict_expand_level
    def recursive_project_and_unwind(level):
        return [
            {"$project": {
                f"data{level}": {
                    "$cond": {
                        "if": {"$eq": [{"$type": f"$v"}, "object"]},
                        "then": {"$objectToArray": f"$v"},
                        "else": []
                    }
                },
                "k": 1
            }},
            {"$unwind": {
                "path": f"$data{level}",
                "preserveNullAndEmptyArrays": False
            }},
            {"$project": {
                "k": {"$cond": {
                    "if": {"$eq": [f"$data{level}", None]},
                    "then": "$k",
                    "else": {"$concat": ["$k", ".", f"$data{level}.k"]}
                }},
                "v": {"$cond": {
                    "if": {"$eq": [f"$data{level}", None]},
                    "then": "$v",
                    "else": f"$data{level}.v"
                }}
            }}
        ]

    # Add recursive stages to the pipeline up to dict_expand_level
    for level in range(1, dict_expand_level + 1):
        pipeline.extend(recursive_project_and_unwind(level))

    # Final stage to collect all unique keys
    pipeline.extend([
        {"$group": {"_id": None, "keys": {"$addToSet": "$k"}}}
    ])

    # Execute the pipeline and get the keys
    result = list(coll.aggregate(pipeline))
    if result:
        _columns = result[0]["keys"]
    else:
        _columns = []

    # Remove '_id' from the list of columns if present
    _columns = [c for c in _columns if c != "_id" and c == c and c != "None"]

    return _columns    





from pymongo import MongoClient

def from_mongo(host, database, collection,
               columns=None,
               filter={},
               array_expand=True,
               cached_meta=True,
               dict_expand_level=0,
               meta_collection = None
               ):
    
    """
    Fetch data from a MongoDB collection and return it as a DataFrame-like object.

    Parameters:
    -----------
    host : str
        The MongoDB host address.
    
    database : str
        The name of the MongoDB database.
    
    collection : str
        The name of the MongoDB collection.
    
    columns : list, optional
        A list of column names to include in the result. If None, columns will be inferred.
    
    filter : dict, optional
        A `mongodf.Filter` class. If None, no filter will be applied
    
    array_expand : bool, optional
        Whether to expand arrays found in the documents into separate rows. Default is True.
    
    cached_meta : bool, optional
        Whether to use cached metadata for inferring columns. Default is True.
    
    dict_expand_level : int, optional
        The level of dictionary expansion to perform. Default is 0.
    
    meta_collection : str, optional
        The name of the collection to use for cached metadata. If None, defaults to '__<collection>_meta'.

    Returns:
    --------
    DataFrame
        A DataFrame-like object containing the data from the MongoDB collection.

    Notes:
    ------
    If `cached_meta` is True and `columns` is None, the function will attempt to retrieve column names 
    from a meta collection (either specified by `meta_collection` or defaulting to '__<collection>_meta'). 
    If no columns are found in the meta collection, it will then infer the columns by analyzing the collection's documents.
    The `dict_expand_level` parameter controls how deeply nested dictionaries are expanded into separate columns.
    """    
    from .filter import Filter
    from .dataframe import DataFrame

    if cached_meta and columns is None:
        _client = MongoClient(host)
        _db = _client.get_database(database)
        if meta_collection is not None:
            _meta_coll = _db.get_collection(meta_collection)
        else:
            _meta_coll = _db.get_collection("__" + collection + "_meta")
        columns = [el["name"] for el in _meta_coll.find({}, {"_id": 0, "name": 1})]
        
        if len(columns) == 0:
            columns = None
        else:
            print("use cols from meta")
        
    if columns is None:
        
        _client = MongoClient(host)
        _db = _client.get_database(database)
        _coll = _db.get_collection(collection)

        _columns = []
        # search nested entries if needed
        for l in reversed(range(dict_expand_level+1)):
            n_cols = get_all_columns_of(_coll, dict_expand_level=l)
            n_cols = [
                c for c in n_cols if 
                len(_columns) == 0 
                or not any([o.startswith(c) for o in _columns])
            ]
            _columns.extend(n_cols)

    else:
        _columns = columns

    mf = DataFrame(host, database, collection, _columns,
                   filter=filter,
                   array_expand=array_expand,
                   _meta_coll=_meta_coll
                   )

    mf._filter = Filter(mf, filter)
    return mf
