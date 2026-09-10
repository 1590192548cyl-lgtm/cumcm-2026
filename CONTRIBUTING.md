# 三人协作规则

## 分支

- `main`：随时可运行、可交付的稳定版本。
- `feat/<topic>`：新增模型、数据处理或图表。
- `fix/<topic>`：修正错误。
- `docs/<topic>`：论文、说明或记录。

示例：`feat/baseline-model`、`fix/missing-values`、`docs/method-section`。

每人同一时间尽量只维护一个短生命周期分支，完成一小块就合并，避免比赛后期出现巨大冲突。

## 提交信息

格式：

```text
<类型>: <简短说明>
```

类型仅用：

- `feat`：新增功能、模型或分析
- `fix`：修复错误
- `data`：数据处理或数据更新
- `plot`：图表更新
- `docs`：文档或论文说明
- `refactor`：重构但不改变结果
- `test`：测试和验证
- `chore`：环境、依赖或杂项

示例：

```text
feat: add entropy weight model
fix: correct missing value interpolation
plot: export sensitivity analysis figure
```

## 比赛期间工作流

开始任务前：

```bash
git switch main
git pull --rebase origin main
git switch -c feat/short-topic
```

完成任务后：

```bash
git add 具体文件路径
git commit -m "feat: short description"
git push -u origin feat/short-topic
```

随后发起 Pull Request，请至少一位队友检查“能否运行、输入输出路径、结果是否一致”。

## 冲突与安全

- 不要三个人同时改同一个 Notebook；核心逻辑应拆到 `src/` 下的脚本。
- 不要用 `git push --force` 覆盖共享分支。
- 不要提交 `.env`、Token、密码、身份证号、手机号等敏感信息。
- 不要提交虚拟环境、缓存和可重新生成的大型临时文件。
- 如果结果会变，先保存旧结果并递增版本号，再生成新结果。
- 每次重大模型调整都在 `docs/` 写一条简短决策记录。

## 合并前最小检查

- 脚本能从项目根目录运行。
- 输入文件存在且路径为相对路径。
- 输出写入规定目录，未覆盖原始数据。
- 随机种子、关键参数和软件版本已记录。
- 图表标题、坐标轴、单位、图例完整。
- `git status` 中没有密钥、缓存或无关大文件。

