---
title: Redis 技术文档
description: Redis 核心原理、数据结构与内部编码、持久化、高可用架构、缓存经典问题与生产调优的系统性笔记
tags:
  - redis
  - middleware
  - cache
  - backend
  - distributed-system
date: 2026-10-28
aliases:
  - redis-cache
  - redis-notes
---

# Redis 技术文档

## 概述

关系型数据库的每一次查询都要付磁盘 IO、SQL 解析、事务与锁的代价，在"高频读热点数据"场景下这套
成本被无限放大。Redis（Remote Dictionary Server）把数据放在内存里，用**单线程执行命令 + IO 多路复用**
规避锁竞争与上下文切换，把单次访问压到亚毫秒级，同时提供 String/Hash/List/Set/Zset 等原生数据结构，
让"排行榜、队列、计数器、去重、地理位置"这类需求不必绕道 SQL。

本文以 **7.x / 8.x** 为主（当前最新稳定版为 8.10.x），关键差异处标注旧版本行为。

> **定位**：Redis 是缓存层与分布式数据结构层，不是主库。它默认不保证强持久、不支持复杂查询与事务回滚，
> 核心业务数据应以 MySQL/PostgreSQL 为准，Redis 承担加速与中间状态。

## 前置知识

- [[mysql|MySQL]]：理解缓存与数据库一致性问题的前提
- [[docker|Docker]]：本文用它起本地环境
- [[elasticsearch|Elasticsearch]]：同为中间件，定位是检索层而非缓存层

## 快速开始

```bash
docker run -d --name redis01 -p 6379:6379 \
  -v ./redis.conf:/usr/local/etc/redis/redis.conf \
  redis:8.0 redis-server /usr/local/etc/redis/redis.conf

docker exec -it redis01 redis-cli        # 交互式客户端
redis-cli -h 127.0.0.1 -p 6379 -a <pwd> --no-auth-warning PING
```

生产 `redis.conf` 必改项：

```conf
bind 0.0.0.0                 # 或指定内网 IP，不要暴露公网
requirepass <strong-pass>    # 7.x 起另有 ACL 用户体系
maxmemory 4gb                # 必须设置，通常留物理内存的 60%-70%
maxmemory-policy allkeys-lru
appendonly yes               # 开启 AOF
appendfsync everysec
save 3600 1 300 100 60 10000 # RDB 快照策略
io-threads 4                 # 6.0+ 多线程网络 IO，命令执行仍单线程
lazyfree-lazy-eviction yes   # 异步释放内存，避免大 key 删除卡顿
```

```bash
# 常用运维命令
INFO server / memory / stats / replication / keyspace
SLOWLOG GET 10               # 慢查询日志
CLIENT LIST                  # 连接列表
MEMORY USAGE user:1001       # 单个 key 的内存占用
redis-cli --bigkeys          # 扫描大 key（抽样，别在高峰期跑）
redis-cli --hotkeys          # 需 maxmemory-policy 为 LFU 类
DBSIZE / SCAN 0 MATCH user:* COUNT 500   # 禁止用 KEYS *
```

## 核心概念

### 为什么单线程还能快

```text
客户端 ──► 多路复用器（epoll / kqueue / evport）──► 事件队列 ──► 单线程命令执行 ──► 返回
                                                                    │
                             6.0+：网络读写可由 io-threads 并行，命令执行仍单线程
```

| 快的原因 | 说明 |
|----------|------|
| 纯内存 | 没有磁盘寻道，随机读写都是纳秒级 |
| IO 多路复用 | 一个线程管理上万连接，无线程切换开销 |
| 单线程执行 | 无锁、无竞态、无上下文切换，且命令天然原子 |
| 高效数据结构 | 内部编码随数据规模自适应切换（见下节） |

代价也很明确：**任何一条慢命令都会阻塞整个实例**。因此生产禁用 `KEYS`、`FLUSHALL`、
大集合的 `SMEMBERS`/`HGETALL`/`LRANGE 0 -1`，以及复杂度为 O(N) 的聚合操作。

### 数据结构与内部编码

Redis 对外是 5 种数据类型，对内是多种编码（encoding），随数据规模自动切换以省内存。
用 `OBJECT ENCODING key` 可查看。

| 类型 | 编码 | 触发条件（默认配置） |
|------|------|----------------------|
| String | `int` / `embstr` / `raw` | 整数值 / 字符串 ≤44 字节 / 更长 |
| Hash | `listpack` → `hashtable` | 字段数 ≤512 且值 ≤64 字节（7.0 起 listpack 取代 ziplist） |
| List | `quicklist` | listpack 组成的双向链表，单节点默认 8KB |
| Set | `intset` / `listpack` → `hashtable` | 全整数且 ≤512 个；7.2 起小字符串集合可用 listpack |
| Zset | `listpack` → `skiplist` + `hashtable` | 元素 ≤128 个且 member ≤64 字节 |
| Stream | `radix tree` + `listpack` | 消息 ID 用基数树索引 |

**实践含义**：小对象用 Hash 存比多个独立 String 省一半以上内存（少一份 key 与元数据开销），
但一旦突破阈值退化为 hashtable，反而更占内存——这正是"Hash 存对象"需要控制字段数的原因。

### Key 设计与过期

```bash
SET  mall:product:1001:stock 120 EX 3600      # 业务:对象:ID:属性，统一前缀便于 SCAN 与运维
EXPIRE mall:user:1001:token 7200
TTL mall:user:1001:token                      # -1 永不过期，-2 已不存在
PERSIST mall:user:1001:token
```

**过期键不是"到点就删"**，而是两套机制配合，理解这点才能解释"内存为什么没降"：

| 机制 | 行为 | 特点 |
|------|------|------|
| 惰性删除 | 访问该 key 时才检查并删除 | 不访问就一直占内存 |
| 定期删除 | 每秒 10 次随机抽样，删除已过期键 | 抽样，可能有残留 |

内存打满时由 `maxmemory-policy` 决定如何腾空间：

| 策略 | 淘汰范围 | 适用场景 |
|------|----------|----------|
| `noeviction` | 不淘汰，写请求报错 | 默认；Redis 做存储而非缓存时 |
| `allkeys-lru` | 全体 key，最近最少用 | 通用缓存首选 |
| `volatile-lru` | 仅设了 TTL 的 key | 需要区分永久与临时数据 |
| `allkeys-lfu` / `volatile-lfu` | 按访问频次淘汰 | 有长期热点、需抗偶发扫描 |
| `allkeys-random` / `volatile-random` | 随机 | 数据访问均匀 |
| `volatile-ttl` | 剩余 TTL 最短的先走 | 时效性明显的场景 |

## 数据类型与命令

### String（字符串）

最基础类型，也是计数器、分布式锁、位图的载体，最大 512MB。

```bash
SET user:1001:name "Alice" EX 3600 NX   # NX：不存在才设（加锁语义）；XX：存在才设
GET user:1001:name
SETEX captcha:13800138000 300 "8291"    # 60 秒后过期的简化写法
MSET k1 v1 k2 v2                        # 批量写，减少 RTT
MGET k1 k2

INCR article:1001:pv                    # 原子自增，天然线程安全
INCRBY order:20261028:seq 100
```

```bash
# Bitmap：365 天的签到只占约 46 字节
SETBIT sign:1001:2026 100 1
BITCOUNT sign:1001:2026                 # 统计签到次数
GETBIT sign:1001:2026 100
```

### Hash（散列）

适合存对象，可单独读写字段，避免"改一个字段要序列化整条"。

```bash
HSET user:1001 name "Alice" age 30 city "上海"
HGET user:1001 name
HMGET user:1001 name age
HGETALL user:1001                       # 字段多时会阻塞，改用 HSCAN
HINCRBY user:1001 balance -100          # 原子扣减，适合余额/库存类计数
HLEN user:1001
HSCAN user:1001 0 MATCH * COUNT 100
```

### List（列表）

双向链表结构，头尾操作 O(1)，适合做轻量队列与最新列表。

```bash
LPUSH queue:order "order-1001"          # 左侧入队
RPUSH queue:order "order-1002"
LPOP queue:order / RPOP queue:order
BRPOP queue:order 30                    # 阻塞弹出，30 秒超时；0 表示一直等
LRANGE queue:order 0 -1                 # 全量读取，元素多时禁用
LTRIM news:latest 0 99                  # 只保留最新 100 条，常用于"最新列表"
```

> List 做队列**没有消费确认、没有重试、没有持久化保证**（消费者弹出后崩溃消息就丢了）。
> 需要可靠消息语义请用 Stream（`XADD`/`XREADGROUP`/`XACK`）。

### Set（集合）

无序、元素唯一，擅长去重、标签、集合运算。

```bash
SADD article:1001:tags "redis" "cache" "backend"
SREM article:1001:tags "cache"
SISMEMBER article:1001:tags "redis"
SMEMBERS article:1001:tags              # 元素多时改 SSCAN
SCARD article:1001:tags
SINTER user:a:follow user:b:follow      # 共同关注
SDIFF user:a:follow user:b:follow       # 差集
SRANDMEMBER lottery:2026 3              # 随机抽奖（可重复用 count 为负）
```

### Zset（有序集合）

member + score，按分数有序，是排行榜与延迟队列的标准解法。

```bash
ZADD rank:2026 98 "player:1001" 87 "player:1002"
ZINCRBY rank:2026 5 "player:1001"
ZRANGE rank:2026 0 9 WITHSCORES         # 分数升序取前 10
ZREVRANGE rank:2026 0 9 WITHSCORES      # 排行榜 Top10（降序）
ZRANK rank:2026 "player:1001"           # 升序排名；ZREVRANK 为降序
ZRANGEBYSCORE rank:2026 80 100          # 按分数区间取
ZREMRANGEBYRANK rank:2026 100 -1        # 只保留前 100 名，控制内存
ZUNIONSTORE rank:week 2 rank:d1 rank:d2 WEIGHTS 1 1   # 周榜合并
```

### 扩展类型速查

| 类型 | 命令 | 用途 | 代价 |
|------|------|------|------|
| Bitmap | `SETBIT` `BITCOUNT` `BITOP` | 签到、活跃标记 | 极省内存，只适合布尔状态 |
| HyperLogLog | `PFADD` `PFCOUNT` `PFMERGE` | UV 去重计数 | 0.81% 误差，约 12KB 固定内存，无法取单条 |
| Geo | `GEOADD` `GEORADIUS`/`GEOSEARCH` | 附近的人、门店 | 底层是 Zset |
| Stream | `XADD` `XREADGROUP` `XACK` `XPENDING` | 可靠消息队列、事件溯源 | 支持消费组与确认，可持久化 |
| JSON | `JSON.SET` `JSON.GET` `JSON.NUMINCRBY` | 文档部分读写 | 8.x 起内置（原 RedisJSON 模块） |
| TimeSeries | `TS.ADD` `TS.RANGE` `TS.MRANGE` | 监控指标、时序聚合 | 8.x 起内置 |
| Vector Set | `VADD` `VSIM` | 向量检索、语义相似度 | 8.x 新结构，底层 HNSW |

## 持久化

Redis 数据在内存，断电即失，持久化决定重启后能找回多少。

### RDB（快照）

`BGSAVE` fork 子进程，利用 **写时复制（COW）** 把某一时刻的内存快照写成二进制 `dump.rdb`。

| 优点 | 缺点 |
|------|------|
| 文件紧凑，恢复速度快 | 丢失最后一次快照之后的所有写入 |
| fork 后主进程几乎无 IO 负担 | 数据量大时 fork 本身可能卡顿（COW 期间内存可能翻倍） |
| 适合冷备与跨机房传输 | `save` 过密会频繁 fork |

### AOF（追加日志）

记录每一条写命令，重启时重放。7.0 起改为 **MP-AOF**（多部分 AOF：base + incr + manifest），
重写不再需要合并历史，减少内存与 CPU 抖动。

| `appendfsync` | 刷盘时机 | 最多丢失 | 性能 |
|----------------|----------|----------|------|
| `always` | 每条命令 | 0 | 最低 |
| `everysec` | 每秒（默认推荐） | 1 秒 | 高 |
| `no` | 交给操作系统 | 一个 buffer | 最高 |

AOF 体积会不断膨胀，靠 `BGREWRITEAOF` 重写（按当前内存数据生成最小命令集）。
开启 `aof-use-rdb-preamble yes`（默认）后，AOF 前半段是 RDB 格式——**混合持久化**，兼顾恢复速度与丢失量。

### 选型建议

| 场景 | 方案 |
|------|------|
| 纯缓存，丢了大不了回源 | 可只开 RDB，甚至不持久化 |
| 通用生产（推荐） | AOF `everysec` + RDB 定时快照双开，重启优先加载 AOF |
| 不允许任何丢失 | AOF `always` + 主从多副本；但注意这已超出 Redis 的设计承诺 |

## 高可用与扩展

### 主从复制

```text
Master ──全量：生成 RDB 传给从节点──► Slave
   └──增量：repl_backlog（环形缓冲）持续推送写命令──► Slave
```

- 从节点默认只读（`replica-read-only yes`），读写分离可分摊读压力。
- 断线重连用 `PSYNC` + `replid/offset` 做**断点续传**；若 backlog 被覆盖（默认 1MB）则退化为全量同步。
  写量大时应调大 `repl-backlog-size`（如 64MB）。
- 主从切换需要人工或 Sentinel，**复制本身不提供自动故障转移**。

### 哨兵 Sentinel

监控主从健康 → 主观/客观下线判定 → 投票选新主 → 通知客户端。

- 至少 **3 个 Sentinel 节点**（防误判与自身高可用）， quorum 通常设为 2。
- 应对脑裂：`min-replicas-to-write 1` + `min-replicas-max-lag 10`，
  让主节点在从节点过少或延迟过大时拒绝写入，避免数据丢失。
- 客户端需支持 Sentinel 拓扑发现（Lettuce/Redisson 均支持）。

### Redis Cluster

官方分片方案：16384 个哈希槽，`CRC16(key) % 16384` 决定槽位，节点间用 Gossip 协议通信。

```bash
redis-cli --cluster create 10.0.0.1:6379 10.0.0.2:6379 10.0.0.3:6379 \
                           10.0.0.4:6379 10.0.0.5:6379 10.0.0.6:6379 \
                           --cluster-replicas 1
redis-cli --cluster reshard 10.0.0.1:6379      # 迁移槽位，扩缩容
```

| 现象 | 含义 |
|------|------|
| `MOVED` | 槽已永久迁移到别的节点，客户端应更新本地槽映射 |
| `ASK` | 槽正在迁移中，单次请求临时转向 |

**Cluster 的三个硬限制**：

1. **多键操作必须在同一槽**：`MGET user:1 user:2` 可能报 `CROSSSLOT`。
   解决：用 hashtag 强制同槽 —— `{user:1001}:name` 与 `{user:1001}:age` 按 `user:1001` 计算槽位。
2. **不支持多数据库**：只有 db0，`SELECT` 不可用。
3. Lua / 事务同样受单槽约束。

### 三种方案对比

| 维度 | 主从复制 | Sentinel | Cluster |
|------|----------|----------|---------|
| 数据冗余 | 有 | 有 | 有 |
| 自动故障转移 | 无 | 有 | 有（节点间自愈） |
| 水平扩容（写） | 无 | 无 | 有，按槽分片 |
| 客户端改造 | 无 | 需支持 Sentinel | 需支持集群协议 |
| 适用 | 读写分离、备份 | 中小规模高可用 | 大数据量 / 高吞吐 |

## 缓存经典问题

### 三大穿透类问题

| 问题 | 成因 | 解法 |
|------|------|------|
| 缓存穿透 | 查询根本不存在的数据，缓存永远不命中，直击数据库 | 布隆过滤器拦截；或缓存空值并设短 TTL（如 60s）；接口层校验非法 ID |
| 缓存击穿 | 某个热点 key 恰好过期，瞬间大量请求回源重建 | 互斥锁重建（SETNX 只放一个线程回源）；或逻辑过期（value 内放过期时间，命中即返回旧值并异步刷新） |
| 缓存雪崩 | 大批 key 同时过期，或实例整体宕机 | TTL 加随机抖动（基础值 + 随机分钟）；多级缓存；限流降级；哨兵/集群保障可用性 |

### 缓存一致性

主流做法是 **Cache Aside Pattern**：

```text
读：命中缓存直接返回 → 未命中读数据库 → 写入缓存 → 返回
写：更新数据库 → 删除缓存（不是更新缓存）
```

**为什么是删除而不是更新**：并发写场景下，两次更新缓存可能乱序导致脏数据；而删除让下一次读
自然回源，代价只是一次 miss。

| 方案 | 一致性 | 复杂度 | 适用 |
|------|--------|--------|------|
| 先更新 DB 再删缓存 | 最终一致，极小概率脏读 | 低 | 绝大多数业务 |
| 延迟双删 | 降低上述脏读概率 | 中 | 对一致性要求较高 |
| MQ 异步重试删除 | 保证删除最终成功 | 中 | 删缓存失败要兜底 |
| 订阅 binlog（Canal）异步删 | 与业务解耦 | 高 | 多服务共享缓存、数据平台同步 |

> 先删缓存再更新 DB 是**错误顺序**：删除后、DB 更新完成前若有读请求，会把旧值写回缓存并长期留存。

## 分布式锁

### 正确的加锁解锁

```bash
# 加锁：NX + PX 必须一条命令完成，保证原子性；value 用唯一标识（UUID）
SET lock:order:1001 6f1d3a9c-... NX PX 30000

# 解锁：先比对 value 再删除，两步必须原子 → 用 Lua 脚本
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
```

| 错误做法 | 问题 |
|----------|------|
| `SETNX` + `EXPIRE` 两条命令 | 加锁后宕机 → 锁永不释放（死锁） |
| 解锁直接 `DEL` | 可能删掉别人持有的锁（自己的锁超时后被他人获取） |
| value 用固定字符串 | 无法判断锁归属，必然误删 |
| 不设过期时间 | 业务异常退出导致死锁 |
| 过期时间短于业务耗时 | 锁提前释放，并发安全失效 → 需要看门狗续期（Redisson `RLock` 默认实现） |

### 其他要点

- **Redis 锁是 AP 侧的"建议锁"**：主从切换时锁信息可能丢失（主加完锁未同步就宕机），
  对强一致场景要谨慎，或改用 Redlock（多实例多数派，但业界对其正确性有争议）。
- **可重入与续期**用 Redisson 的 `RLock` 最省事：默认 30s + 每 10s 自动续期（watchdog）。
- **集群下的 hashtag**：Cluster 中锁 key 只有一个，不涉及多键，正常使用即可。

## 事务与 Lua

### 事务（MULTI / EXEC）

```bash
WATCH account:1001          # 乐观锁：监视 key，若被其他客户端修改则事务中止
MULTI
DECRBY account:1001 100
INCRBY account:1002 100
EXEC                        # 返回 nil 表示被 WATCH 的 key 已变更，需重试
```

**Redis 事务不是关系型数据库的事务**：它只保证"命令顺序执行、不被其他客户端打断"，
**不支持回滚**——某条命令失败（如类型错误）不会撤销已执行的命令，需要业务侧自己补偿。

### Lua 脚本

脚本整体原子执行，是"复杂原子操作"的标准手段（如库存扣减 + 订单记录、限流、解锁）。

```lua
-- 简单限流：60 秒内最多 100 次
local current = redis.call("INCR", KEYS[1])
if current == 1 then
    redis.call("EXPIRE", KEYS[1], 60)
end
return current <= tonumber(ARGV[1])
```

约束：脚本要短小（避免阻塞单线程）、禁止长时间循环与随机结果，脚本内所有 key 必须走 `KEYS[]`
以便 Cluster 路由校验。

## Pipeline 与批量操作

| 手段 | 原子 | 作用 | 注意 |
|------|------|------|------|
| Pipeline | 否 | 一次网络往返批量发命令，降低 RTT | 单批控制在数百~数千条，过大会阻塞 |
| `MGET` / `MSET` | 是 | 原生批量命令 | 仅 String，且 Cluster 下需同槽 |
| Lua | 是 | 原子 + 减少往返 | 见上节 |
| 事务 | 部分 | 顺序执行 + WATCH | 不支持回滚 |

典型收益：跨机房 RTT 1ms 时，1 万次 GET 串行约 10s，Pipeline 打包后约几十 ms。

## 性能优化与运维

### 必查指标

| 指标 | 命令/字段 | 关注点 |
|------|-----------|--------|
| 缓存命中率 | `INFO stats` 的 `keyspace_hits / (hits+misses)` | 低于 90% 需排查 key 设计与 TTL |
| 淘汰数量 | `evicted_keys` | 持续增长说明内存不足或策略不当 |
| 内存 | `used_memory` / `mem_fragmentation_ratio` | 碎片率 >1.5 考虑重启或 `MEMORY PURGE` |
| 连接数 | `connected_clients` / `rejected_connections` | 拒绝连接说明 `maxclients` 或慢查询堆积 |
| 持久化 | `rdb_last_bgsave_status` / `aof_last_bgrewrite_status` | 失败要立刻告警 |
| 复制延迟 | `INFO replication` 的 `slave_repl_offset` 差值 | 差值持续增长说明从节点追不上 |

### 优化要点

1. **禁用危险命令**：`KEYS`、`FLUSHALL`、`FLUSHDB`，线上用 `rename-command` 屏蔽。
2. **拆大 Key**：String >10KB、集合元素 >5000 就算大 key。Hash 按 `hash-max-listpack-*` 控制，
   集合用分段（如 `set:1001:part:0..N`）或换结构。
3. **控制 value 大小**：大 value 会放大网络、序列化与内存碎片成本，必要时空缓存压缩。
4. **开启 lazy free**：`lazyfree-lazy-eviction/expire/del yes`，避免删百万级集合时主线程卡顿。
5. **系统层**：关闭 THP（`echo never > /sys/kernel/mm/transparent_hugepage/enabled`）、
   设 `vm.overcommit_memory=1`，否则 fork 失败会导致持久化静默失效。
6. **热点 key**：本地缓存（Caffeine）挡一层；或用 `key:1..N` 分片打散到不同实例后再聚合。
7. **客户端缓冲**：主从全量同步期间，从节点输出缓冲暴涨会触发 `client-output-buffer-limit`
   断开连接导致反复全量同步，需调大 `slave` 分类的限制。

## Java 实战

### 客户端选型

| 客户端 | 线程模型 | 特点 |
|--------|----------|------|
| Lettuce | 基于 Netty，连接天然线程安全，可共享 | Spring Boot 2.x/3.x 默认；支持异步、响应式 |
| Jedis | 直连，实例非线程安全，需连接池 | API 直观，生态老；高并发下连接池是瓶颈 |
| Redisson | 基于 Netty，提供分布式对象 | 分布式锁、延迟队列、布隆过滤器等高级抽象最全 |

### Spring Data Redis 示例

```java
// 1. 序列化配置：默认 JDK 序列化可读性差且体积大，统一换 JSON
@Bean
public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
    RedisTemplate<String, Object> template = new RedisTemplate<>();
    template.setConnectionFactory(factory);
    GenericJackson2JsonRedisSerializer json = new GenericJackson2JsonRedisSerializer();
    template.setKeySerializer(RedisSerializer.string());
    template.setValueSerializer(json);
    template.setHashKeySerializer(RedisSerializer.string());
    template.setHashValueSerializer(json);
    return template;
}
```

```java
// 2. Cache Aside：查缓存 → 未命中回源 → 回写缓存
public Product getById(Long id) {
    String key = "mall:product:" + id;
    Product cached = (Product) redisTemplate.opsForValue().get(key);
    if (cached != null) {
        return cached;                      // 空值时缓存的是 NullValue，不是 null
    }
    Product db = productMapper.selectById(id);
    // 缓存空值防穿透：TTL 短一些，避免不存在的数据长期占位
    redisTemplate.opsForValue().set(key, db == null ? NullValue.INSTANCE : db,
            db == null ? Duration.ofMinutes(2) : Duration.ofMinutes(30));
    return db;
}

// 3. 原子计数与限流
Long pv = redisTemplate.opsForValue().increment("mall:product:" + id + ":pv");
```

```java
// 4. Redisson 分布式锁：自动续期，业务跑多久都不会提前释放
RLock lock = redissonClient.getLock("lock:order:" + orderId);
boolean locked = lock.tryLock(10, 30, TimeUnit.SECONDS);
if (!locked) {
    throw new BizException("操作过于频繁，请稍后重试");
}
try {
    createOrder(orderId);
} finally {
    lock.unlock();                          // 必须判断当前线程是否仍持有锁
}
```

> **序列化坑**：`GenericJackson2JsonRedisSerializer` 会写入 `@class` 类型信息，
> 反序列化依赖类路径，改动包名或类结构会导致反序列化失败；追求可控时改用
> `Jackson2JsonRedisSerializer<Product>`（指定类型，不带类型信息）。

## 常见误区与陷阱

| 误区 | 实际情况 | 纠正方法 |
|------|----------|----------|
| 把 Redis 当主库 | 默认异步持久化，宕机会丢数据 | 关键数据落 MySQL，Redis 只做加速与中间态 |
| 用 `KEYS *` 查 key | O(N) 阻塞单线程 | 用 `SCAN` 游标迭代 |
| 一个大 Hash 存所有用户 | 突破 listpack 阈值后内存暴涨，且 HGETALL 阻塞 | 按用户拆分 key，控制字段数与 value 长度 |
| 缓存更新用"更新"而非"删除" | 并发写导致乱序脏数据 | 更新 DB 后删除缓存 |
| 先删缓存再更新 DB | 期间读请求会把旧值写回缓存 | 先更新 DB，再删缓存 |
| `SETNX` + `EXPIRE` 加锁 | 非原子，宕机即死锁 | `SET key val NX PX ttl` |
| 解锁直接 `DEL` | 可能删掉别人的锁 | value 唯一标识 + Lua 校验后删 |
| List 当消息队列用 | 无 ACK、消费失败即丢 | 用 Stream 消费组 |
| 不设 `maxmemory` | 内存打满被 OOM Killer 杀掉 | 设上限 + 明确淘汰策略 |
| 不设密码暴露公网 | 极高危，勒索与挖矿重灾区 | 强密码 + ACL + 内网/防火墙 |
| 用 `SMEMBERS` 取大集合 | 一次性拉回百万元素，网络与内存双爆 | `SSCAN` 分页 |
| 认为事务能回滚 | Redis 事务无回滚 | 业务侧补偿或用 Lua 保证原子 |

## 排错

| 症状 | 原因 | 排查/解决 |
|------|------|-----------|
| `MISCONF ... save RDB snapshots` | 上次 bgsave 失败，拒绝写入 | 查磁盘权限、`vm.overcommit_memory=1`、关闭 THP |
| `OOM command not allowed when used memory > maxmemory` | 内存满且策略为 `noeviction` | 调大 maxmemory 或改淘汰策略 |
| `READONLY You can't write against a read only replica` | 连到了从节点 | 写操作走主节点；检查客户端路由 |
| `CROSSSLOT Keys in request don't hash to the same slot` | Cluster 多键跨槽 | 用 hashtag `{}` 保证同槽 |
| `CLUSTERDOWN The cluster is down` | 有槽无节点负责 | `redis-cli --cluster check`；修复节点或 `fix` |
| 主从反复全量同步 | 输出缓冲被限流断开 | 调大 `client-output-buffer-limit slave` 与 `repl-backlog-size` |
| 延迟突然抖动 | 大 key 删除 / fork / AOF rewrite / 慢查询 | 查 `SLOWLOG`、`INFO commandstats`、`latest_fork_usec` |
| `NOAUTH Authentication required` | 未认证 | 配置 `requirepass` 或 ACL 用户并在客户端传入 |
| 缓存命中率持续下降 | TTL 过短、key 设计分散、热点变更 | 分析 `--hotkeys`、调整 TTL 与预热策略 |
| 库存超卖 | 读改写非原子 | Lua 脚本或 `DECRBY` 原子扣减 |

## 与相关概念的关系

- 与 [[mysql|MySQL]]：MySQL 是数据落地的最终来源，Redis 在其前面挡读压力；
  一致性靠 Cache Aside + 删除缓存 + binlog 订阅兜底，二者是"存储 + 加速"的搭档关系。
- 与 [[elasticsearch|Elasticsearch]]：ES 擅长全文检索与聚合分析，Redis 擅长精确 key 的低延迟读写；
  常见组合是"Redis 挡热点 → 回源查库 → 复杂检索交 ES"，两者不互相替代。
- 与 [[minio|MinIO]]：MinIO 存大对象（图片、文件），Redis 存小热数据；
  不要往 Redis 里塞大文件，可只在 Redis 缓存对象的元信息与临时签名链接。
- 与 [[docker|Docker]]：本地起 Redis 与搭建主从/集群实验环境的基础工具。

## 参考

- [Redis 官方文档](https://redis.io/docs/latest/)
- [Redis 命令参考](https://redis.io/commands/)
- [Redis 设计与实现（内部编码与持久化原理）](http://redisbook.com/)
- [[middleware/index|中间件索引]]
- [[mysql|MySQL]]
