# 复习资料阅读器

离线知识点复习阅读器（uni-app x 工程）。四份复习资料的结构化数据在构建时编译进安装包，运行期零网络请求、零文件 I/O，断网完全可用。

> 本仓库前身是 DCloud `hello-uni-app-x` 演示工程，demo 页面已全部移除。与原设计文档的偏差记录见 `doc/实现说明.md`。

## 功能

- **资料**：4 份资料卡片，显示科目、知识点数与复习进度，支持「继续学习」直达上次阅读位置
- **章节目录**：按 章 → 节 层级浏览，已复习标记
- **阅读**：连续滚动内容（标题 / 正文 / 术语卡 / 列表 / 口诀 / 表格），上一节 / 标记已复习 / 下一节，收藏本节
- **搜索**：标题与全文检索（正文、术语、表格单元格），结果定位到小节
- **收藏**：跨资料收藏列表，可取消收藏
- **设置**：资料统计，二次确认后清除全部复习进度 / 收藏
- **暗黑模式**：跟随系统，颜色全部走 `common/uni.css` 主题变量

## 目录结构

```
pages.json                  页面注册（4 tab + 2 普通页）
manifest.json               应用配置（appid 为空，需自行获取）
App.uvue / main.uts         入口
theme.json                  pages.json @var 主题变量（亮/暗）
common/uni.css              主题变量作用域（.uni-theme-root）
common/materials/           资料数据资产
  types.uts                 Material / MaterialSection / ContentBlock 类型
  loader.uts                静态导入 + 章节导航、内容索引（模块级缓存）
  search.uts                全文检索
  index.json                资料索引
  *.json × 4                四份资料的结构化内容
store/study.uts             学习状态（已复习 / 收藏 / 阅读位置，Storage 持久化）
components/                 easycom 组件：content-block、progress-bar、empty-state、
                            page-head、bottom-safe-area
pages/                      index / search / favorites / settings / material.detail / material.read
scripts/check.py            静态一致性校验（不需要 HBuilderX）
doc/                        原设计文档与实现说明
package/                    应用图标素材（manifest.json 引用）
```

## 如何运行

1. 用 HBuilderX（建议 4.x 以上，需支持 uni-app x / UTS）打开本目录。
2. 首次运行需在 `manifest.json` 填入自己的 appid（当前为空字符串；HBuilderX 登录 DCloud 账号后可重新获取）。
3. 菜单「运行」→ 运行到浏览器（Web 快速预览）或 Android 真机/基座。
4. 交付前可跑一次静态校验：`python scripts/check.py`（仅标准库，无需安装依赖）。

## 数据格式

`index.json`：

```json
{ "schemaVersion": 1, "materials": [{ "id", "title", "subject", "file", "sectionCount", "blockCount", "updatedAt" }] }
```

资料文件（如 `mechanical-drawing.json`）：

```json
{
  "schemaVersion": 1, "id", "title", "subject",
  "sections": [{ "id", "title", "level": 1|2, "parentId": "string|null", "blockIds": ["blk-..."] }],
  "blocks":   [{ "id", "type", "level", "text", "label", "marker", "ordered", "headers", "rows", "depth" }]
}
```

`blocks` 所有字段统一存在（缺省给空值），保证 UTS 侧可以整体 `as ContentBlock[]` 转型。`type` 取值：

| type | 含义 | 关键字段 |
|---|---|---|
| `heading` | 标题（level 1/2/3） | `text` |
| `paragraph` | 正文段落 | `text` |
| `kv` | 术语卡「标签：内容」 | `label`, `text` |
| `list_item` | 有序列表项 | `marker`, `text` |
| `quote` | 口诀 / 引用 | `text` |
| `table` | 表格（实测均为 2~4 列等宽） | `headers`, `rows` |

**阅读单元**定义为「拥有非 heading 内容块的 section」——机械制图的「附录二」是无子节点的 level 1，另外三份资料的每章各带一段【考情分析】/【核心逻辑】导语，按 level 过滤会漏掉这些内容。上一节 / 下一节 / 进度都按这个序列计。

## 如何新增一份资料

1. 把新资料按上述 schema 整理为 `common/materials/<id>.json`（来源是 Word 文档时，可参考 `doc/复习资料文档处理方法文档.md` 的结构约定：章节号在 `numbering.xml` 自动编号里，必须还原后写入 `title`）。
2. 在 `common/materials/index.json` 追加一条（`id`/`title`/`subject`/`file`/`sectionCount`/`blockCount`）。
3. 在 `common/materials/loader.uts` 顶部加一行静态导入，并在 `loadMaterial` 里加对应分支。
4. 运行 `python scripts/check.py`，确认引用闭合与计数一致。

进度数据按 `review:state:{materialId}` 存 Storage，新资料 id 无需迁移。

## 已知限制

- `manifest.json` 的 appid 为空，鸿蒙 `bundleName` 为占位值 `com.reviewmaterials.app`，发布前需替换。
- `harmony-configs/` 内是 DCloud demo 的签名证书（`io.dcloud.uniappx`），打包鸿蒙前必须换成自己的证书。
- tabBar 未配置图标（纯文字），需要图标时自行补 PNG 并更新 `pages.json`。
