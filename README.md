# infra-model-eval

多模型场景化测评工具。给定一个业务场景（system prompt + 测试用例），对多个 AI 模型并排测试，输出对比结果。

**适用场景**：为新项目选模型、对比 prompt 改动效果、验证模型是否满足具体业务要求。

---

## 两种使用方式

### 方式一：对话快测（无需任何文件）

直接在命令行传 prompt 和用例，适合临时验证一个想法：

```bash
python eval.py \
  --system "把下面的英文翻译成中文，只输出译文，不要任何解释" \
  --cases "hello world,good morning,thank you" \
  --model deepseek-chat,gpt-4.1
```

多行 prompt 用引号包住换行：

```bash
python eval.py \
  --system "你是代码审查助手。只输出：风险等级（高/中/低）+ 一句说明" \
  --cases "eval(user_input),os.system(cmd),int(x)" \
  --model deepseek-chat,gpt-4.1,gpt-4o-mini
```

### 方式二：项目深测（YAML 文件）

为某个项目创建专属场景文件，适合正式调研：

```bash
python eval.py --scenarios-file ./my_project/eval_scenarios.yaml
python eval.py --scenarios-file ./my_project/eval_scenarios.yaml --model deepseek-chat,gpt-4.1
```

**YAML 文件格式**：

```yaml
scenarios:
  - id: "scenario_id"
    name: "场景显示名"
    max_tokens: 500
    system: |
      你是一个...
      输出格式：...
    cases:
      - "用例1"
      - "用例2"

  - id: "another_scenario"
    name: "另一个场景"
    max_tokens: 100
    system: "单行 prompt"
    cases:
      - "测试A"
      - "测试B"
```

---

## 环境配置

```bash
pip install openai python-dotenv pyyaml

cp .env.example .env   # 填入需要的 API key
```

**.env 格式**：

```
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
```

缺少某个 key 时对应模型自动跳过。

---

## 可用模型

| 模型 ID | 显示名 | 需要的 key |
|---------|--------|-----------|
| `gpt-4.1` | GPT-4.1 | `OPENAI_API_KEY` |
| `gpt-4.1-mini` | GPT-4.1-mini | `OPENAI_API_KEY` |
| `gpt-4.1-nano` | GPT-4.1-nano | `OPENAI_API_KEY` |
| `gpt-4o` | GPT-4o | `OPENAI_API_KEY` |
| `gpt-4o-mini` | GPT-4o-mini | `OPENAI_API_KEY` |
| `o4-mini` | o4-mini（推理） | `OPENAI_API_KEY` |
| `deepseek-chat` | DeepSeek V3 | `DEEPSEEK_API_KEY` |
| `deepseek-v4-pro` | DeepSeek V4-pro（推理） | `DEEPSEEK_API_KEY` |

新增模型：在 `eval.py` 的 `MODELS` 列表加一行。

---

## 完整参数

```
--system PROMPT          System prompt（快测模式）
--cases  c1,c2,...       测试用例逗号分隔（快测模式必填）
--max-tokens N           快测模式 max_tokens，默认 800
--scenarios-file PATH    YAML/JSON 场景文件（项目深测模式）
--scenario   ID[,ID]     内置场景过滤（默认模式）
--model      ID[,ID]     模型过滤，默认全部
--no-save                不保存结果文件
```

---

## 结果输出

每次自动保存到 `results/`（已 gitignore）：
- `results/YYYYMMDD_HHMMSS.json` — 完整数据（耗时、token）
- `results/YYYYMMDD_HHMMSS.md`  — 可读报告

---

## 内置场景库

`scenarios.py` 包含来自 app-ai-input 项目的示例场景，可直接参考格式：

```bash
python eval.py --scenario explain --model deepseek-chat,gpt-4.1
```

---

## AI Agent 使用指引

**当用户说"用 infra-model-eval 测一下 XXX"时，执行步骤：**

1. 工具路径：`/Users/cuijianchen/gh-projects/infra-model-eval/`
2. 确认 `.env` 存在并有 key（`DEEPSEEK_API_KEY` 和/或 `OPENAI_API_KEY`）
3. 激活 venv：`source .venv/bin/activate`
4. 选择用法：
   - 临时验证 → `--system` + `--cases` 直接跑
   - 项目场景 → 生成 YAML 文件，用 `--scenarios-file` 加载
5. 推荐默认模型：`--model deepseek-chat,gpt-4.1,gpt-4.1-mini`
6. 跑完分析输出，给用户结论

**当用户提供了项目场景（prompt、数据、需求）时：**

直接生成 YAML 内容写到合适路径，执行 `--scenarios-file` 模式。不需要改 `eval.py` 或 `scenarios.py`。
