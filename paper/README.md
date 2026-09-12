# 论文 LaTeX 工程说明

## 文件结构

```
paper/
├─ main.tex              正文（唯一入口）
├─ figures/              插图，PDF 与 PNG 各一份
│  ├─ fig1_p1_profile    问题 1 径向分布
│  ├─ fig2_p2_profile    问题 2 径向分布
│  ├─ fig3_p3            问题 3 时间演化与剖面
│  ├─ fig4_p4            问题 4 半径路径与含水率
│  └─ fig5_verification  模型检验三联图
└─ tables/               表格，由结果文件自动生成
   ├─ table_01_p1_temperature / table_02_p1_moisture   表 1、表 2
   ├─ table_03_p2_temperature / table_04_p2_moisture   表 3、表 4
   ├─ table_05_p3_moisture              表 5
   └─ table_06_p4_moisture              表 6
```

## 在 Overleaf 上使用

1. Overleaf 首页 → New Project → Upload Project，把整个 `paper` 文件夹压缩成 zip 上传。
2. 打开后进 Menu → Compiler，选 **XeLaTeX**（文档用了 ctex 宏包，pdfLaTeX 编译中文会报错）。
3. 若目录名 `figures/` 被改动，需要同步修改 `main.tex` 里的 `\graphicspath`。

本机没有安装 TeX 发行版，因此这里没有编译产物；`main.tex` 已做过环境配对、`\input` 路径、
`\includegraphics` 路径和 `\label`/`\ref` 一致性检查，未在本地编译验证。

## 图表如何重新生成

表格和插图都由脚本从结果文件直接生成，不手抄数字。改了计算结果后运行：

```powershell
$py = "C:\Users\江润\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py src\make_paper_assets.py
```

数据来源：

| 图表 | 来源 |
|---|---|
| 图 1、表 1、表 2 | `output/p1_fields.npz`、`output/tables/表1~2` |
| 图 2、表 3、表 4 | `output/p2_fields.npz`、`output/tables/表3~4` |
| 图 3、表 5 | `output/p3_fields.npz`、`output/tables/表5` |
| 图 4、表 6 | `output/p4_fields.npz`、`output/tables/表6` |
| 图 5(a)(c) | `logs/verify_p1.json`、`logs/convergence_face_avg.json`、`logs/convergence_extreme.json` |
| 图 5(b) | `logs/sens_km_scale.json` |

## 与提交文件的对应关系

| 论文中 | 提交文件 |
|---|---|
| 表 1、表 2 | `output/result1.xlsx`（1800 行 × 21 列） |
| 表 3、表 4 | `output/result2.xlsx`（整个烘干过程，每 1 s；3 h 节选见 `output/extra/result2_3h.xlsx`） |
| 表 5 | `output/result3.xlsx`（每 60 s 至烘干结束） |
| 表 6 | `output/result4.xlsx`（末列为药材表面） |

## 写作约定

正文按"假设—模型—离散—结果—检验—评价"组织，所有数字取自 `logs/` 下的原始诊断数据。
未在文中出现的中间量（如迭代次数、网格编号）一律不给，避免堆砌。
