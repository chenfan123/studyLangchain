## 使用 docker 部署

打开 **`PowerShell`** 或 **`CMD`** 终端，执行：

```bash
docker pull postgres:16
```

这里选择 **`PostgreSQL 16`** 版本，是当前最新的稳定大版本，与 **`langgraph-checkpoint-postgres==3.0.5`** 兼容。

拉取完成后，可通过以下命令查看本地已有的镜像：

```bash
docker images | findstr postgres
```

#### 运行 PostgreSQL 容器

执行以下命令启动容器：

```bash
docker run -d `
  --name langgraph-postgres `
  -e POSTGRES_DB=langgraph_db `
  -e POSTGRES_USER=langgraph_user `
  -e POSTGRES_PASSWORD=123456 `
  -p 5432:5432 `
  postgres:16
```

各参数含义：

| 参数                                  | 含义                                               |
| ------------------------------------- | -------------------------------------------------- |
| **`-d`**                              | 后台运行（`daemon` 模式），终端关闭后容器不会停止  |
| **`--name langgraph-postgres`**       | 容器名称，方便后续管理                             |
| **`-e POSTGRES_DB=langgraph_db`**     | 创建容器时自动创建名为 **`langgraph_db`** 的数据库 |
| **`-e POSTGRES_USER=langgraph_user`** | 自动创建用户 **`langgraph_user`**                  |
| **`-e POSTGRES_PASSWORD=123456`**     | 设置该用户的密码为 **`123456`**                    |
| **`-p 5432:5432`**                    | 将容器的 5432 端口映射到宿主机的 5432 端口         |

#### 验证容器运行状态

```bash
# 查看正在运行的容器
docker ps

# 如果看不到 langgraph-postgres，查看所有容器（包括已停止的）
docker ps -a

# 查看容器日志
docker logs langgraph-postgres
```

如果容器没有运行，可以通过以下命令启动：

```bash
docker start langgraph-postgres
```

> **常用容器管理命令**：
>
> ```bash
> docker stop langgraph-postgres    # 停止容器
> docker start langgraph-postgres   # 启动容器
> docker restart langgraph-postgres # 重启容器
> docker rm langgraph-postgres      # 删除容器（需要先停止）
> ```

#### A.2.1.4. Docker Compose 方式（可选）

如果更习惯使用 **`Docker Compose`** 管理容器，可以创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16
    container_name: langgraph-postgres
    environment:
      POSTGRES_DB: langgraph_db
      POSTGRES_USER: langgraph_user
      POSTGRES_PASSWORD: 123456
    ports:
      - “5432:5432”
    volumes:
      - pgdata:/var/lib/postgresql/data # 持久化数据，容器删除后数据不丢失

volumes:
  pgdata:
```

然后在 `docker-compose.yml` 所在目录执行：

```bash
docker compose up -d
```

**`volumes`** 配置将数据库文件映射到宿主机，**即使容器被删除，数据也不会丢失**——这对于保存检查点数据非常重要。

## PostgreSQL 基本操作

本节介绍 **`PostgreSQL`** 的常用操作。掌握这些内容有助于理解 **`PostgresSaver`** 在数据库中做了什么，也方便日常排查问题。

### A.3.1. 连接 PostgreSQL

#### A.3.1.1. 使用 psql 命令行工具

**`psql`** 是 **`PostgreSQL`** 自带的命令行客户端。

连接命令格式：

```bash
psql -h <主机> -p <端口> -U <用户名> -d <数据库名>
```

对应本附录的连接信息：

```bash
psql -h localhost -p 5432 -U langgraph_user -d langgraph_db
# 输入密码: 123456
```

连接成功后，终端提示符变为 `langgraph_db=>`，可以输入 **`SQL`** 命令。

> **Docker 用户**：如果主机上没有安装 **`psql`**，可以直接进入容器内执行：
>
> ```bash
> docker exec -it langgraph-postgres psql -U langgraph_user -d langgraph_db
> ```

常用 **`psql`** 元命令：

| 命令                | 说明                   |
| ------------------- | ---------------------- |
| **`\l`**            | 列出所有数据库         |
| **`\dt`**           | 列出当前数据库的所有表 |
| **`\d table_name`** | 查看表结构             |
| **`\q`**            | 退出 **`psql`**        |

#### A.3.1.2. 使用 Python 连接

在 **`Python`** 中使用 **`psycopg`** 连接：

```python
import psycopg

DB_URL = “postgresql://langgraph_user:123456@localhost:5432/langgraph_db?sslmode=disable”

conn = psycopg.connect(DB_URL)
cur = conn.cursor()

# 查看 PostgreSQL 版本信息
cur.execute(“SELECT version();”)
result = cur.fetchone()
print(f”PostgreSQL 版本：{result[0]}”)

cur.close()
conn.close()
```

**运行结果如下**

```
PostgreSQL 版本：PostgreSQL 16.x on x86_64-pc-linux-gnu, compiled by gcc ...
```

> **注意**：如果在 `pip install psycopg` 时没有加 `[binary]` 后缀，可能会因为缺少编译环境而报错。遇到这种情况执行 `pip install psycopg[binary]` 即可。

### A.3.2. 创建数据库和用户

> **Docker 用户请注意**：通过 **`docker run`** 的 **`-e`** 环境变量启动容器时，数据库和用户已经自动创建并配置好权限，**可以跳过本节**，直接阅读 **A.3.3 节**。

如果你是**手动安装的 **`PostgreSQL`**，启动时**不会**自动创建 **`langgraph_db`数据库和 **`langgraph_user`** 用户，需要手动创建。

#### A.3.2.1. 创建数据库

首先用超级用户 **`postgres`** 连接：

```bash
psql -h localhost -p 5432 -U postgres
```

然后创建数据库：

```sql
CREATE DATABASE langgraph_db;
```

查看是否创建成功：

```sql
\l
```

输出中如果能找到 **`langgraph_db`** 条目，则说明创建成功。

#### A.3.2.2. 创建用户并授权

在同一个 **`psql`** 会话中继续执行：

```sql
-- 创建用户
CREATE USER langgraph_user WITH PASSWORD '123456';

-- 赋予该用户对 langgraph_db 的所有权限
GRANT ALL PRIVILEGES ON DATABASE langgraph_db TO langgraph_user;
```

> **`PostgreSQL 15+`** 版本默认收紧了对 **`public`** 模式的权限管理。如果后续 **`PostgresSaver`** 在创建表时报权限错误，需要额外执行：
>
> ```sql
> \c langgraph_db
> GRANT ALL ON SCHEMA public TO langgraph_user;
> ```

退出 **`psql`**，用新用户测试连接：

```bash
psql -h localhost -p 5432 -U langgraph_user -d langgraph_db
# 输入密码: 123456
```

如果能成功连接，说明用户和数据库配置正确。

### A.3.3. 基本 CRUD 操作

了解基本的 **`SQL`** 增删改查有助于查看和理解 **`PostgresSaver`** 内部的数据存储。

#### A.3.3.1. 创建表

```sql
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- **`SERIAL PRIMARY KEY`**：自增主键，**`PostgreSQL`** 会自动为新插入的行分配唯一的 **`id`**；
- **`TEXT`**：变长文本类型，适合存储聊天消息内容；
- **`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`**：时间戳类型，默认为插入时的当前时间。

#### A.3.3.2. 插入数据

```sql
INSERT INTO messages (thread_id, role, content)
VALUES ('chapter_6_6.2.4', 'user', '你好，我是老王');

INSERT INTO messages (thread_id, role, content)
VALUES ('chapter_6_6.2.4', 'assistant', '老王你好！有什么可以帮你的？');
```

#### A.3.3.3. 查询数据

```sql
-- 查询所有记录
SELECT * FROM messages;

-- 按 thread_id 筛选（最常用，对应 LangGraph 中的 thread）
SELECT * FROM messages WHERE thread_id = 'chapter_6_6.2.4';

-- 按时间排序
SELECT * FROM messages WHERE thread_id = 'chapter_6_6.2.4' ORDER BY created_at;
```

#### A.3.3.4. 更新和删除数据

```sql
-- 更新某条记录的内容
UPDATE messages SET content = '你好，我是老王，今年30岁。'
WHERE id = 1;

-- 删除某条记录
DELETE FROM messages WHERE id = 2;

-- 删除整个表（注意：操作不可逆）
DROP TABLE IF EXISTS messages;
```

### A.3.4. 查看 PostgresSaver 创建的表结构

这是整个附录中最实用的部分——**连接回 6.2.4 节**，看看 **`checkpointer.setup()`** 在 **`PostgreSQL`** 中到底创建了什么。

#### A.3.4.1. 运行 setup()后查看表

首先运行一次 **6.2.4 节** 的代码（确保 **`setup()`** 已执行），然后在 **`psql`** 中查看：

```sql
\c langgraph_db
\dt
```

**运行结果如下**

```
             List of relations
 Schema |        Name           | Type  |     Owner
--------+-----------------------+-------+----------------
 public | checkpoint_blobs      | 数据表 | langgraph_user
 public | checkpoint_migrations | 数据表 | langgraph_user
 public | checkpoint_writes     | 数据表 | langgraph_user
 public | checkpoints           | 数据表 | langgraph_user
```

可以看到 **`setup()`** 在数据库中创建了四张表：

| 表名                        | 用途                                                             |
| --------------------------- | ---------------------------------------------------------------- |
| **`checkpoints`**           | 存储完整的检查点快照（状态、元数据等）                           |
| **`checkpoint_writes`**     | 存储每个检查点对应的通道写入记录                                 |
| **`checkpoint_blobs`**      | 存储大型二进制数据（如图片、文件等，如果状态中包含的话）         |
| **`checkpoint_migrations`** | 记录数据库迁移版本，**`LangGraph`** 内部使用，用于管理表结构变更 |

#### A.3.4.2. 检查点表结构说明

使用 **`\d`** 命令查看每张表的实际结构。

**（1）checkpoints 表**

```sql
\d checkpoints
```

```
         栏位         | 类型  |  可空的  |    预设
----------------------+-------+----------+-------------
 thread_id            | text  | not null |
 checkpoint_ns        | text  | not null | ''::text
 checkpoint_id        | text  | not null |
 parent_checkpoint_id | text  |          |
 type                 | text  |          |
 checkpoint           | jsonb | not null |
 metadata             | jsonb | not null | '{}'::jsonb
索引：
    "checkpoints_pkey" PRIMARY KEY, btree (thread_id, checkpoint_ns, checkpoint_id)
    "checkpoints_thread_id_idx" btree (thread_id)
```

**关键字段说明**：

| 字段                       | 类型        | 说明                                                              |
| -------------------------- | ----------- | ----------------------------------------------------------------- |
| **`thread_id`**            | **`text`**  | 线程 ID，对应 **`config`** 中的 **`thread_id`**，用于区分不同对话 |
| **`checkpoint_ns`**        | **`text`**  | 检查点命名空间，默认空字符串，用于子图等场景隔离不同层级的检查点  |
| **`checkpoint_id`**        | **`text`**  | 检查点唯一 ID，由 **`LangGraph`** 内部生成                        |
| **`parent_checkpoint_id`** | **`text`**  | 父检查点 ID，构建检查点链，用于 **`Time Travel`** 回退            |
| **`type`**                 | **`text`**  | 检查点类型                                                        |
| **`checkpoint`**           | **`jsonb`** | 检查点核心数据（状态快照），以 **`JSON`** 格式存储                |
| **`metadata`**             | **`jsonb`** | 检查点元数据（创建时间、来源、步骤序号等），预设为 `'{}'::jsonb`  |

- 主键为 **(thread_id, checkpoint_ns, checkpoint_id)** 联合主键。
- 另有 **`thread_id`** 单列索引，加速按线程筛选查询。

**（2）checkpoint_writes 表**

```sql
\d checkpoint_writes
```

```
     栏位      |  类型   |  可空的  |   预设
---------------+---------+----------+----------
 thread_id     | text    | not null |
 checkpoint_ns | text    | not null | ''::text
 checkpoint_id | text    | not null |
 task_id       | text    | not null |
 idx           | integer | not null |
 channel       | text    | not null |
 type          | text    |          |
 blob          | bytea   | not null |
 task_path     | text    | not null | ''::text
索引：
    "checkpoint_writes_pkey" PRIMARY KEY, btree (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
    "checkpoint_writes_thread_id_idx" btree (thread_id)
```

**关键字段说明**：

| 字段                | 类型          | 说明                                                        |
| ------------------- | ------------- | ----------------------------------------------------------- |
| **`thread_id`**     | **`text`**    | 线程 ID                                                     |
| **`checkpoint_ns`** | **`text`**    | 命名空间，与 **`checkpoints`** 表对应                       |
| **`checkpoint_id`** | **`text`**    | 所属检查点 ID                                               |
| **`task_id`**       | **`text`**    | 产生写入的节点任务 ID                                       |
| **`idx`**           | **`integer`** | 写入顺序索引                                                |
| **`channel`**       | **`text`**    | 写入的目标通道名（如 **`messages`**、**`__pregel_tasks`**） |
| **`type`**          | **`text`**    | 写入数据类型                                                |
| **`blob`**          | **`bytea`**   | 写入的二进制数据                                            |
| **`task_path`**     | **`text`**    | 任务路径，用于追踪节点在子图中的层级关系                    |

- 主键为 **(thread_id, checkpoint_ns, checkpoint_id, task_id, idx)** 联合主键，确保同一任务下的写入顺序唯一。

**（3）checkpoint_blobs 表**

```sql
\d checkpoint_blobs
```

```
     栏位      | 类型  |  可空的  |   预设
---------------+-------+----------+----------
 thread_id     | text  | not null |
 checkpoint_ns | text  | not null | ''::text
 channel       | text  | not null |
 version       | text  | not null |
 type          | text  | not null |
 blob          | bytea |          |
索引：
    "checkpoint_blobs_pkey" PRIMARY KEY, btree (thread_id, checkpoint_ns, channel, version)
    "checkpoint_blobs_thread_id_idx" btree (thread_id)
```

**关键字段说明**：

| 字段                | 类型        | 说明                                 |
| ------------------- | ----------- | ------------------------------------ |
| **`thread_id`**     | **`text`**  | 线程 ID                              |
| **`checkpoint_ns`** | **`text`**  | 命名空间                             |
| **`channel`**       | **`text`**  | 通道名                               |
| **`version`**       | **`text`**  | 数据版本标识，同一通道可以有多个版本 |
| **`type`**          | **`text`**  | 数据类型                             |
| **`blob`**          | **`bytea`** | 二进制数据本体                       |

- 主键为 **(thread_id, checkpoint_ns, channel, version)** 联合主键。
- 与 **`checkpoint_writes`** 不同，**`checkpoint_blobs`** 以 **(channel, version)** 维度管理数据版本，不直接关联某个具体的 **`checkpoint_id`**，允许多个检查点共享同一通道的大型二进制数据。

**（4）checkpoint_migrations 表**

```sql
\d checkpoint_migrations
```

```
 栏位 |  类型   |  可空的  | 预设
------+---------+----------+------
 v    | integer | not null |
索引：
    "checkpoint_migrations_pkey" PRIMARY KEY, btree (v)
```

**关键字段说明**：

| 字段    | 类型          | 说明                 |
| ------- | ------------- | -------------------- |
| **`v`** | **`integer`** | 当前数据库迁移版本号 |

- 单列主键，仅一条记录，**`setup()`** 执行时自动检查并更新。
- 该表由 **`LangGraph`** 内部管理，用户无需手动操作。未来 **`LangGraph`** 版本升级时，若表结构有变更，**`setup()`** 会根据此版本号自动执行对应的迁移 **`SQL`**。

> **四张表的关系**：
>
> - **`checkpoints`** 存储每次 **`graph.invoke()`** 产生的检查点快照；
> - **`checkpoint_writes`** 存储每个检查点下各节点任务的通道写入记录（一条检查点通常对应多条写入）；
> - **`checkpoint_blobs`** 存储通道级别的大型二进制数据，以 **(thread_id, checkpoint_ns, channel, version)** 为维度，可跨检查点复用；
> - **`checkpoint_migrations`** 仅用于数据库表结构版本管理。
>
> **`LangGraph`** 通过 **`thread_id`** + **`checkpoint_ns`** + **`checkpoint_id`** 联合定位和恢复状态。

#### A.3.4.3. 写入检查点数据查询

运行 **6.2.4 节** 的示例代码后，可以直接在数据库中查看写入的数据：

```sql
SET client_encoding = 'UTF8';
-- 查看指定线程的检查点数量
SELECT thread_id, count(*)
FROM checkpoints
WHERE thread_id = 'chapter03-02'
GROUP BY thread_id;

-- 查看所有检查点的基本信息（按创建时间排序）
SELECT checkpoint_id, parent_checkpoint_id, checkpoint_ns, metadata
FROM checkpoints
WHERE thread_id = 'chapter03-02'
ORDER BY metadata;

-- 查看最新检查点的消息通道写入数据
SELECT c.checkpoint_id, c.checkpoint_ns, cw.channel, cw.task_id, cw.type
FROM checkpoints c
JOIN checkpoint_writes cw
  ON c.thread_id = cw.thread_id
 AND c.checkpoint_ns = cw.checkpoint_ns
 AND c.checkpoint_id = cw.checkpoint_id
WHERE c.thread_id = 'chapter03-02'
  AND cw.channel = 'messages'
ORDER BY cw.idx;

-- 查看最新检查点的完整状态 JSON
SELECT checkpoint_id, checkpoint
FROM checkpoints
WHERE thread_id = 'chapter03-02'
ORDER BY metadata DESC
LIMIT 1;

```

通过这些查询，可以直观地理解 **`PostgresSaver`** 是如何将 **`LangGraph`** 的检查点数据持久化到 **`PostgreSQL`** 中的。

> **Windows 终端编码问题**：
> 在中文 **`Windows`** 的 **`CMD`** 或 **`PowerShell`** 中使用 **`psql`** 查询 **`checkpoint`**（**`jsonb`**）字段时，如果数据中包含 emoji 等 4 字节 **`UTF-8`** 字符，可能会报错：
>
> ```
> 错误:  编码"UTF8"的字符0x0xf0 0x9f 0xa4 0x94在编码"GBK"没有相对应值
> ```
>
> 这是因为 **`Windows`** 终端默认编码为 **`GBK`**，无法处理 4 字节 **`UTF-8`** 字符。解决方案：
>
> ```sql
> -- 查询前先切换客户端编码
> SET client_encoding = 'UTF8';
> ```
>
> 或在 **`PowerShell`** 中先执行 **`chcp 65001`** 切换到 **`UTF-8`** 编码，再启动 **`psql`**。

#### 补充说明

- **`setup()`** 是幂等的——多次调用不会重复创建表，也不会清空已有数据；
- 实际项目中，建议将 **`setup()`** 作为独立的数据库初始化/迁移步骤执行，而不是每次启动应用时都调用（这也是 **6.2.4 节** 代码注释中提到的建议）；
- 如果需要主动清理某个线程的检查点数据，可以使用 **`checkpointer.delete_thread(thread_id)`** 方法，或者从数据库层面删除对应记录；
- 关于连接池：如果需要在生产环境中处理高并发请求，建议使用 **`psycopg_pool`** 提供的连接池功能，而不是每次创建新连接。
