# 基本要素

State、Node、Edge

- State: LangGraph 运行过程中的共享数据，用于表示应用在某一时刻的状态快照。 承载了图运行所需的上下文信息、中间结果和后续节点需要读取的数据，
  是节点之间传递信息的核心载体。
- Node：具体执行单元，通常实现为一个函数。节点会读取当前 State,执行相应的业务逻辑，并返回对 State 的局部更新。
- Edge：用于定义节点之间的流转关系，觉得一个节点执行完成后下一步应该进入哪个节点。

### 图运行过程

基于 Superstep（超步） 来组织和推进。Superstep 可以理解为图运行过程中的一次”单步循环”。一次图运行过程从开始到结束，就是由一系列连续的 Superstep 串联而成。

每个 Superstep 都包含以下三个阶段：

1. 计划/路由节点：根据当前的 State（状态） 和 Edge（边） 的逻辑，确定本轮超步中应该被执行的节点。
2. 执行阶段：运行本轮被选中的节点。如果本轮有多个节点同时被触发，它们会并行执行。每个节点都会基于本轮开始时的状态快照进行计算，并输出各自对状态的局部更新。在本阶段中，一个节点产生的更新不会立即被其他节点读取到。
3. 状态更新/提交阶段：当本轮所有节点都执行完成后，LangGraph 会将它们的输出统一合并到 State 中，生成新的状态快照。这个新状态会作为下一轮 Superstep 的输入。

> 额外功能：绘制图

```python
raw_memaid = graph.get_graph().draw_mermaid()
print(raw_memaid)
Markdown(raw_memaid)
```

> 额外功能：保存图片文件

```python
png_bytes = graph.get_graph().draw_mermaid_png()
png_filename = 'first_demo_graph.png'
with open(png_filename, "wb") as f:
    f.write(png_bytes)
```

## 图的状态管理

状态的定义实际上是在声明状态的 Schema，后者是状态字段的完整描述。
三种定义 Schema 的方式：

- TypedDict
- dataclass
- Pydantic

### 校验行为

上述这三种方式都要求字段名称完全一致。

#### 输入字段不匹配

##### 1. TypedDict

TypedDict 将输入字段视为字典的`Key`，不匹配时抛出`KeyError`异常。

##### 2. dataclass

dataclass 将输入字段视为类的`属性`，不匹配时抛出`TypeError（类型错误）`异常。

##### 3. Pydantic

Pydantic 对输入字段进行校验，不匹配时抛出`ValidationError`异常。

#### 节点返回字段不匹配

图节点返回的是对于状态的更新，如果返回字段和状态字段不匹配，上述三种 Schema 定义方式的行为是统一的：状态更新会被忽略。

## State Reducer

### 1. 什么是 State Reducer

用于合并状态更新的核心机制。在 LangGraph 的 `StateGraph` 中，每个节点可以读取和写入共享状态，而 Reducer 定义了如何将多个节点对同一状态键的更新合并
核心特征：

1. 函数签名：`(state, update) -> state`,接收当前值和更新值，返回合并后的新值
2. 注解定义：通过 `Annotated[Type, reducer_function]` 为状态键指定 Reducer
3. 默认行为：未指定 Reducer 的状态键使用覆盖策略（Last-Write-Wins）

### 2. 如何定义 Reducer

#### 定义 Reducer 函数

本质是一个二元合并函数，用于定义当同一个字段产生多个更新值时，LangGraph 应该如何将这些值合并为一个最终结果。
函数签名：`(state, update) -> state`

#### 将 Reducer 和状态字段关联

通过 Python 的 `typing.Annotated` 与状态字段进行关联。
`Annotated` 的第一个参数是被注解的原始类型，后续参数是附加的元数据。
基本形式：`Annotated[Type, reducer_function]`

- Type: 表示状态字段的数据类型
- reducer_function:表示该字段对应的 Reducer 函数。

##### 常用的内置 Reducer 函数

1.  `operator.add`: 用于数值类型的累加,等价于 `a（第一个参数）+b（第二个参数）`
2.  `langgraph.graph.message.add_messages`: LangGraph 中专用于合并消息列表的 Reducer 函数。
    不是简单的执行合并，而是根据消息内的 id，如果 id 已存在则覆盖，如果不存在则追加。
3.  默认行为：后一次更新值会覆盖该字段原有的状态值

## 节点中访问 State

节点本质上是一个可调用对象，通常定义为普通 Python 函数。会自动将当前图运行到该节点时的 `State` 传入节点函数。
节点函数的第一个参数通常是当前运行图的状态对象，也就是 `State`。
注意：如果并行节点的话，他们读取的是全局状态快照。

### 图节点更新状态

不需要返回更新后的完整状态，只需要返回本节点对状态的局部更新。

- 对于节点没有返回的字段，LangGraph 会保留其原有状态值；
- 对于节点返回的字段，LangGraph 会根据该字段是否配置了 `Reducer` 来决定如何合并更新值。
  - 如果字段配置了 `Reducer`，则使用对应的 `Reducer` 函数将旧值和新值合并；
  - 如果字段没有配置 `Reducer`，则按照默认规则使用节点返回的新值覆盖原值。

### Overwrite 绕过 Reducer

`Overwrite` 的作用是：告诉 LangGraph 本次状态更新不走该字段原本定义的 `Reducer`，而是直接用新值覆盖状态中的旧值。
`Overwrite` 只影响当前这一次更新，并不会修改状态字段本身的 `Reducer` 定义。后续节点如果继续正常返回该字段的更新值，仍然会按照原来的 `Reducer` 逻辑进行合并。

## MultiSchema 用法

### 状态类型

- 全局状态/内部状态：图内部主要使用的状态，创建 `StateGraph` 时传递给 `state_schema` 参数。

- 输入状态：图对外接收输入时使用的状态，创建 `StateGraph` 时传递给 `input_schema` 参数。用于约束调用图时允许传入哪些字段

- 输出状态：图最终对外返回结果时使用的状态，创建 `StateGraph` 时传递给 `output_schema` 参数。它用于约束图运行结束后只返回哪些字段。

- 私有状态：图内部节点之间传递的临时状态，通常不作为图的输入，也不作为图的最终输出。它可以通过节点函数的入参类型注解声明，并在节点返回值中写入。

> 注意，输入状态和输出状态主要面向图的边界，即“图如何接收外部输入”和“图如何返回外部结果”；而全局状态和私有状态主要面向图内部节点之间的数据传递。

### 状态之间的关系

#### 设计规范

1. 输入状态和输出状态通常应是全局状态的子集
2. 私有状态和全局状态应尽量避免字段重名
3. 节点函数应明确声明入参状态类型和返回状态类型
4. 节点函数中不应该访问入参状态类型中不存在的字段
5. 节点函数返回的字典应尽量和返回类型注解保持一致

#### 源码层面的约束

从底层机制角度说明 `LangGraph` 如何记录、裁剪和更新状态。

##### 状态的记录

状态并不是简单保存在一个普通字典中，而是会被拆分成多个可读写的状态字段。每个状态字段在底层通常对应一个 `Channel`。
这些状态字段会在不同阶段被记录到状态图中。

1. `StateGraph` 记录状态字段的核心方法是 `_add_schema()`
   `_add_schema()` 会解析传入的状态 Schema，并将其中声明的字段记录到图中，使这些字段成为图运行时可以读写的状态字段。

2. 创建 `StateGraph` 时，会记录 `state_schema`、`input_schema` 和 `output_schema` 中的字段
   当创建状态图时：

   ```
   builder = StateGraph(
       OverAllState,
       input_schema=InputState,
       output_schema=OutputState
   )
   ```

   LangGraph 会解析这些 Schema，并将其中涉及的字段加入图的状态管理体系。

3. 调用 `add_node()` 添加节点时，也可能记录节点入参声明的状态 Schema
   当添加节点时，`LangGraph` 会根据节点函数第一个参数的类型注解推断该节点的输入状态类型。
   如果这个输入状态类型之前没有被图记录过，LangGraph 也会通过 `_add_schema()` 将其加入图中。
   这也是私有状态能够生效的原因。
   例如：

   ```python
   class PrivateState(TypedDict):
       greeting: str

   def node_3(state: PrivateState) -> OutputState:
       return {
           "graph_output": state["greeting"]
       }
   ```

   当 `node_3` 被添加到图中时，`PrivateState` 中的 `greeting` 字段会被记录到图中，从而成为图内部可以传递的状态字段。

4. 总结

- 全局状态、输入状态、输出状态通常在创建 `StateGraph` 时被记录。
- 私有状态通常在调用 `add_node()` 添加节点时，根据节点入参类型注解被记录。
- 被记录后的状态字段，底层会成为图运行时可以读写的状态字段。

##### 状态的访问

1. 调用图时，输入会按照 `input_schema` 进行约束
   当调用图时：

   ```python
   graph.invoke({"username": "小黄"})
   ```

   如果创建图时声明了 `input_schema`，那么外部输入会按照 `input_schema` 进行约束。
   如果没有声明 `input_schema`，则通常按照 `state_schema` 作为图的输入 Schema。
   因此，`input_schema` 的作用不是“只让第一个节点可见”，而是约束图的外部输入结构。
   此处的约束是指：按照 `schema` 裁剪输入，只保留 `schema` 中出现的状态字段

2. 节点接收到的状态会按照节点入参类型进行裁剪
   每个节点能读取哪些字段，主要取决于该节点第一个参数的类型注解。
   例如：

   ```python
   def node_1(state: InputState) -> OverAllState:
       ...
   ```

   此时，`node_1` 接收到的 `state` 会按照 `InputState` 进行裁剪。即使图的全局状态中还有其他字段，`node_1` 也不应该访问不属于 `InputState` 的字段。
   如果访问了入参状态中不存在的字段，例如：

   ```python
   state["nickname"]
   ```

   就可能抛出：

   ```python
   KeyError
   ```

3. 节点返回的是状态更新，而不是完整状态
   节点函数不需要返回完整状态，只需要返回本节点想要更新的字段。
   例如：

   ```python
   def node_1(state: InputState) -> OverAllState:
       return {
           "nickname": "Dear " + state["username"]
       }
   ```

   这里虽然返回类型注解是 `OverAllState`，但函数实际只返回了 `nickname` 一个字段。这是允许的，因为 LangGraph 会把节点返回值视为对状态的部分更新。

4. 节点返回值的应用主要由字段名称和图中已记录的状态字段决定
   节点返回的字典会根据字段名称写入对应状态字段，并按照该字段的 `Reducer` 规则进行合并。
   需要注意的是，函数返回类型注解主要用于表达代码意图，不是严格的运行时写入边界。
   也就是说，如果某个字段已经被图记录为可用状态字段，那么节点即使没有在返回类型注解中声明该字段，也可能仍然可以返回并更新它。
   不过，为了代码清晰，仍然推荐让节点的返回值和返回类型注解保持一致。

5. 最终输出会按照 `output_schema` 进行裁剪
   图运行完成后，最终返回给外部调用方的结果会按照 `output_schema` 进行裁剪。
   因此，`output_schema` 的作用不是“只让最后一个节点可见”，而是约束图最终对外暴露哪些字段。
   例如，图内部状态中可能同时存在：

   ```
   username
   nickname
   greeting
   graph_output
   ```

   但如果 `output_schema` 只包含：

   ```
   graph_output
   ```

   那么最终 `graph.invoke()` 的返回结果就只会包含 `graph_output`。

## 预定义状态

### MessageState

`LangGraph` 官方提供了一个预定义状态类型：`langgraph.graph.message.MessagesState`。
开发者可以直接继承该状态类型，并在其基础上扩展自定义状态字段。
源码如下：

```python
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```

由此可知，`MessagesState` 只有一个字段：`messages`。
该字段的类型是列表，元素类型为 `AnyMessage`；同时，它通过 `Annotated` 绑定了内置 `Reducer` 函数 `add_messages`。

`add_messages` 的完全限定名（英文全称 `fully qualified name`）是：

`langgraph.graph.message.add_messages`，正是上文 3.2.2.3.2 节介绍的内置 `Reducer` 函数。

## AgentState

`AgentState` 是 `LangChain Agent` 内部使用的状态类型。
也可以将 `AgentState` 或其子类作为自定义 `LangGraph` 的状态类型。
`AgentState` 的全类名，也可以称为类的完全限定名（英文全称： `fully qualified class name`）是：`langchain.agents.middleware.types.AgentState`
源码如下

```python
class AgentState(TypedDict, Generic[ResponseT]):
    """State schema for the agent."""

    messages: Required[Annotated[list[AnyMessage], add_messages]]
    jump_to: NotRequired[Annotated[JumpTo | None, EphemeralValue, PrivateStateAttr]]
    structured_response: NotRequired[Annotated[ResponseT, OmitFromInput]]
```
