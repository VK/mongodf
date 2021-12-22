# MongoDf

[![Python Package](https://github.com/VK/mongodf/actions/workflows/python-publish.yml/badge.svg)](https://github.com/VK/mongodf/actions/workflows/python-publish.yml)
[![PyPI](https://img.shields.io/pypi/v/mongodf?logo=pypi)](https://pypi.org/project/mongodf)

A mongoDB to pandas DataFrame converter with a pandas filter style.

## Install
```
pip install mongodf
```

## Filter Example
```python
import mongodf
import pymongo

mongo = pymongo.MongoClient("mongodb://mongo:27017")

# create a dataframe from a mongoDB collection
df = mongodf.from_mongo(mongo, "DB", "Collection")

# filter values
df = df[(df["colA"] == "Test") & (df.ColB.isin([1, 2]))]

# filter columns
df = df[["colA", "colC"]]

# compute a pandas.DataFrame
df.compute()
```

|   | colA  | colC |
|---| ----- | ---- |
|0  | Test  |  NaN |
|1  | Test  |   12 |