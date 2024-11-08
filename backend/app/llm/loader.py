import json
from pathlib import Path
from pprint import pprint
from langchain_community.document_loaders import JSONLoader
import os
from enum import Enum
from langchain_core.documents import Document

class DataSource(Enum):
    COMPANIES = "/app/mockdata/companies.json"

FILE_PATHS = ["app/mockdata/companies.json", "app/mockdata/products.json"]

def load_json_docs(file_paths = FILE_PATHS):
    docs_list = []
    for file_path in file_paths:
        loader = JSONLoader(
         file_path=file_path,
         jq_schema=".[] | .company_name",
        )
        docs = loader.load()
        # for doc in docs:
        #     print(doc)
        docs_list.append(docs)
    return docs_list

