import json
from pathlib import Path
from pprint import pprint
from langchain_community.document_loaders import JSONLoader
import os
from enum import Enum

def load_company_products():
    loader = JSONLoader(
        file_path="app/mockdata/company_products.json",
        jq_schema=".[] | .company_name",
    )
    docs = loader.load()
    # for doc in docs:
    #     print(doc)
    return docs

def load_patents():
    def metadata_func(record: dict, metadata: dict) -> dict:
        metadata["patent_id"] = record.get("patent_id")
        return metadata
    
    loader = JSONLoader(
        file_path="app/mockdata/patents.json",
        jq_schema=".[]",
        content_key="claims",
        metadata_func=metadata_func,
    )
    docs = loader.load()
    for doc in docs:
        print(doc)
    return docs

def load_json_docs():
    return [load_company_products(), load_patents()]

