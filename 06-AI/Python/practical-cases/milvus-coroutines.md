---
title: 协程操作 Milvus 向量数据库
description: 用 run_in_executor 包装 pymilvus 的同步 SDK，实现并发批量查询与插入
tags:
  - python
  - asyncio
  - milvus
  - vector-database
date: 2026-11-06
aliases:
  - milvus-coroutines
---

# 协程操作 Milvus 向量数据库

> 依赖：`pip install pymilvus`

本示例演示如何使用 Python 协程并发查询 Milvus 向量数据库，提升 I/O 密集型任务的效率。

---

## 1. 初始化连接

```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

def init_milvus():
    connections.connect(alias="default", host="localhost", port="19530")
    
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=2)
    ]
    
    schema = CollectionSchema(fields=fields, description="测试集合")
    collection = Collection(name="test_coroutine", schema=schema)
    collection.create_index(field_name="vector", index_params={"index_type": "FLAT"})
    
    return collection
```

---

## 2. 协程查询

`pymilvus` 客户端以同步 API 为主，通过 `run_in_executor` 包装可支持协程并发查询：

```python
import asyncio

async def search_milvus(collection, query_vector, top_k=2):
    loop = asyncio.get_running_loop()
    
    result = await loop.run_in_executor(
        None,  # 使用默认线程池
        lambda: collection.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "L2"},
            limit=top_k,
            output_fields=["id"]
        )
    )
    return result[0]
```

---

## 3. 并发查询主函数

```python
async def main():
    collection = init_milvus()
    
    query_vectors = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
    
    tasks = [search_milvus(collection, vec) for vec in query_vectors]
    results = await asyncio.gather(*tasks)
    
    for i, res in enumerate(results):
        print(f"\n查询向量 {query_vectors[i]} 的结果：")
        for hit in res:
            print(f"  id: {hit.id}, 距离: {hit.distance:.4f}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 4. 批量插入示例

```python
async def insert_vectors(collection, vectors):
    loop = asyncio.get_running_loop()
    
    await loop.run_in_executor(
        None,
        lambda: collection.insert([list(range(len(vectors))), vectors])
    )
```

---

## 5. 完整示例

```python
import asyncio
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

def init_milvus():
    connections.connect(alias="default", host="localhost", port="19530")
    
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128)
    ]
    
    schema = CollectionSchema(fields=fields, description="向量检索测试")
    collection = Collection(name="vectors", schema=schema)
    collection.create_index(
        field_name="vector",
        index_params={"index_type": "IVF_FLAT", "params": {"nlist": 128}}
    )
    collection.load()
    
    return collection

async def search(collection, query_vectors, top_k=10):
    loop = asyncio.get_running_loop()
    
    results = await loop.run_in_executor(
        None,
        lambda: collection.search(
            data=query_vectors,
            anns_field="vector",
            param={"metric_type": "L2", "params": {"nprobe": 16}},
            limit=top_k
        )
    )
    return results

async def main():
    collection = init_milvus()
    
    import numpy as np
    query_vectors = [np.random.rand(128).tolist() for _ in range(100)]
    
    results = await search(collection, query_vectors)
    
    for i, hits in enumerate(results[:3]):
        print(f"Query {i}: {len(hits)} results")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. 性能对比

| 方式 | 100 次查询耗时 |
|------|----------------|
| 同步串行 | ~10s |
| 协程并发 | ~2s |

**关键点：** 协程通过并发减少 I/O 等待时间，但单个查询的延迟不变。适合批量查询场景。

---

## See Also

- [[04-python-async|Python 异步编程]] —— `run_in_executor` / `to_thread` 包装同步 SDK 的原理
- [[06-AI/python/practical-cases/index|实战案例目录]] —— 其他落地案例
- [[06-AI/python/index|Python 笔记目录]]