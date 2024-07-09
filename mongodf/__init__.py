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


"""
MongoDf
-------

.. |github-badge| image:: https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white
    :alt: Github
    :height: 20px
    :target: https://github.com/VK/mongodf

.. |build-status| image:: https://github.com/VK/mongodf/actions/workflows/python-publish.yml/badge.svg
    :alt: Publish Status
    :height: 20px

.. |pypi-status| image:: https://img.shields.io/pypi/v/mongodf?logo=pypi
    :alt: PyPi
    :height: 20px
    :target: https://pypi.org/project/mongodf

.. |docu-status| image:: https://github.com/VK/mongodf/workflows/Documentation/badge.svg
    :alt: Documentation
    :height: 20px
    :target: https://vk.github.io/mongodf


|github-badge| |build-status| |pypi-status| |docu-status|  
  
A mongoDB to pandas DataFrame converter with a pandas filter style.

Example::
  
    import mongodf

    # create a dataframe from a mongoDB collection
    df = mongodf.from_mongo("mongodb://mongo:27017", "DB", "Collection")

    # filter values
    df = df[(df["colA"] == "Test") & (df.ColB.isin([1, 2]))]

    # filter columns
    df = df[["colA", "colC"]]

    # compute a pandas.DataFrame
    df.compute()

Output::

    |   | colA  | colC |
    |---| ----- | ---- |
    |0  | Test  |  NaN |
    |1  | Test  |   12 |

"""

from .column import Column
from .filter import Filter
from .dataframe import DataFrame
from .cache import MongoDFCache
from .utils import get_all_columns_of, from_mongo, flatten_dict

__all__ = ["Column", "Filter", "DataFrame", "from_mongo", "get_all_columns_of", "flatten_dict", "MongoDFCache"]
