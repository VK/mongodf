# MongoDf

[![Python Package](https://github.com/VK/mongodf/actions/workflows/python-publish.yml/badge.svg)](https://github.com/VK/mongodf/actions/workflows/python-publish.yml)
[![PyPI](https://img.shields.io/pypi/v/mongodf?logo=pypi)](https://pypi.org/project/mongodf)
[![Documentation](https://github.com/VK/mongodf/workflows/Documentation/badge.svg)](https://vk.github.io/mongodf)


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



## Cache Example
```
import plotly.express as px
df = px.data.gapminder()

cache = MongoDFCache(
    host="mongodb://mongo:27017",
    database="mongodfcache",
    expire_after_seconds=20,
)

# put the dataframe into the mongo cache
# the name can be auto generated, array_group can be a list of cols
id = cache.cache_dataframe(df, "test_df", array_group=True)

# get a mongodf without reading all the data
cdf = cache.get_dataframe(id)

# get the metadata and the content of the dataframe
gcdf.get_meta()
gcdf.compute()

```