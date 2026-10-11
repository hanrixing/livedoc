# LiveDoc 规格格式（`.livedoc`）

LiveDoc 是一种「活文档」声明文件：它不存内容，而存**三件事**——版式长什么样、数据从哪来、讲稿怎么讲。
生成器读它，拉实时数据、渲染成可播放的动态内容。

## 顶层结构

```
{
  "meta":         { ... },   // 元信息：标题、分身、是否含敏感数据
  "data_sources": [ ... ],   // 数据源声明数组：mock / http / mcp
  "compute":      { ... },   // 派生字段：从已拉到的值算出新值
  "script":       [ ... ]    // 讲稿分镜：每段 = 一镜
}
```

> 兼容说明：旧格式的单对象 `data_source`（非数组）仍可正常解析。

---

## 1. meta —— 元信息

| 字段 | 必填 | 说明 |
|---|---|---|
| `title` | ✅ | 文档标题 |
| `avatar` | ✅ | 数字分身引用（即梦 `@分身名`） |
| `sensitive` | ⬜ | 默认为 `true`。**为 true 时，`--live` 产物隔离到 `output/live/`（已 gitignore）并告警** |
| `layout` | ⬜ | 版式模板名（如 `quarterly-report`）。当前为逻辑声明，尚未做可视化编辑器 |
| `author` / `privacy` / `desc` | ⬜ | 作者、隐私说明、描述，仅作展示 |

```json
"meta": {
  "title": "麦麦省钱周报",
  "avatar": "@麦麦省钱官分身",
  "sensitive": true,
  "privacy": "live 模式产出含个人券信息，仅限本地查看"
}
```

---

## 2. data_sources —— 数据源声明

数组，每项一个数据源。三种类型：

### 通用字段

| 字段 | 说明 |
|---|---|
| `id` | 数据源标识（用于来源标注） |
| `type` | `mock` / `http` / `mcp` |
| `fallback` | 拉取失败或字段抽不到时的兜底值，**保证产物永远能生成** |

### mcp（推荐：接实时业务数据）

```json
{
  "id": "my_coupons",
  "type": "mcp",
  "server": "mcd-mcp",
  "tool": "query-my-coupons",
  "args": {},
  "extract": {
    "coupon_count": "共\\s*(\\d+)\\s*张可用优惠券",
    "coupon_first": "##\\s*(.+)",
    "claimable":   { "op": "count", "pattern": "优惠券标题" }
  },
  "fallback": { "coupon_count": 3, "coupon_first": "示例券", "claimable": 6 }
}
```

- MCP 返回的是**文本**（多为 Markdown），所以用 `extract` 正则抽字段
- 正则字符串 → 取第 1 个捕获组
- `{"op":"count","pattern":"..."}` → 统计匹配次数（适合数列表条数）
- Token 由生成器从 `MCD_MCP_TOKEN` 环境变量或 `~/.workbuddy/mcp.json` 读取，**不写在规格里、不进产物**

### http（拉公开接口）

```json
{
  "id": "github",
  "type": "http",
  "url": "https://api.github.com/repos/hanrixing/mcd-saving-expert",
  "fields": { "star": "stargazers_count", "fork": "forks_count" },
  "fallback": { "star": 1, "fork": 0 }
}
```

`fields` 用点路径取值（支持 `a.b.c`）。

### mock（离线示例值，demo 模式默认走它）

```json
{ "id": "demo", "type": "mock", "values": { "star": 1 } }
```

---

## 3. compute —— 派生字段

从已拉到的字段算出新值，避免把计算逻辑硬编码进讲稿。

| op | 说明 | 示例 |
|---|---|---|
| `last_date` | 从字符串里取最后一个 `YYYY-MM-DD` | 有效期串 → 到期日 |
| `days_until` | 该日期距今还有几天（负数表示已过期） | 到期日 → 剩余天数 |

```json
"compute": {
  "expiry_date": { "op": "last_date",  "from": "coupon_expiry" },
  "expiry_days": { "op": "days_until", "from": "coupon_expiry" }
}
```

---

## 4. script —— 讲稿分镜

每段 = 即梦的一镜。

```json
"script": [
  {
    "shot":   "到期预警",
    "speak":  "重点提醒：{coupon_first}这张券 {expiry_date} 到期，只剩 {expiry_days} 天。",
    "camera": "特写急推，分身抬手提醒，画面轻微震动",
    "visual": "券面浮现红色倒计时「{expiry_days} 天」，红色警示辉光"
  }
]
```

- `speak`：数字分身口播内容
- `camera` / `visual`：镜头与视觉提示词（同样支持占位符）
- 所有 `{占位符}` 在生成时被真实数据替换——**这就是「活」的关键**：数据变，重跑即更新

---

## 隐私模型（重要）

MCP 数据源会拉到**个人资产**（卡包券、积分余额）。生成器据此分两种模式：

| 命令 | 数据 | 产物位置 | 可否公开 |
|---|---|---|---|
| `python generator.py` | 脱敏示例 | `output/` | ✅ |
| `--live` + `sensitive:true` | 真实个人数据 | `output/live/` | ❌ 仅本地 |
| `--live` + `sensitive:false` | 公开数据源 | `output/` | ✅ |

规格作者在 `meta.sensitive` 声明，生成器执行隔离。默认保守值 `true`。

---

## 与「死 PPT 转视频」的本质区别

| | PPT 转视频工具 | LiveDoc |
|---|---|---|
| 数据 | 截图写死在视频里 | 声明式数据源，实时拉 |
| 讲解 | TTS 机器人配音 | 数字分身真人形象 |
| 产物 | 死 MP4 | 数据变 → 重跑 → 自动更新 |

LiveDoc 不重新发明编辑器，它重新定义「文档是什么」：一份**声明**，不是一份**副本**。
