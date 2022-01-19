from .column import Column
from .filter import Filter
from .dataframe import DataFrame


def from_mongo(mongo, database, collection, columns=None, filter={}):

    _db = mongo.get_database(database)
    _coll = _db.get_collection(collection)

    if columns is None:
        # compute the colums of the data
        _columns = list(_coll.aggregate([
            {"$project": {
                "data": {"$objectToArray": "$$ROOT"}
            }},
            {"$project": {"data": "$data.k"}},
            {"$unwind": "$data"},
            {"$group": {
                "_id": None,
                "keys": {"$addToSet": "$data"}
            }}
        ]))[0]["keys"]

        _columns = [c for c in _columns if c != "_id"]
    else:
        _columns = columns

    mf = DataFrame(mongo, _db, _coll, _columns)
    mf._filter = Filter(mf, filter)
    return mf


__all__ = ["Column", "Filter", "DataFrame", "from_mongo"]
