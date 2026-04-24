#!/usr/bin/env python3
"""
infra-model-eval — 场景化多模型测评工具

两种用法：

1. 对话快测（不需要任何文件）
   python eval.py --system "把下面的英文翻译成中文，只输出译文" \
                  --cases "hello,good morning,thank you" \
                  --model deepseek-chat,gpt-4.1

2. 项目深测（YAML 文件）
   python eval.py --scenarios-file ./my_project/eval_scenarios.yaml

3. 用内置场景库（scenarios.py）
   python eval.py                              # 全部场景 + 全部模型
   python eval.py --scenario explain           # 指定场景
   python eval.py --model gpt-4.1,deepseek-chat  # 指定模型
"""
import argparse, json, os, sys, time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

# ── 模型注册表 ─────────────────────────────────────────────────────────────
MODELS = [
    # OpenAI
    {"id": "gpt-4.1",         "label": "GPT-4.1",         "base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY",   "reasoning": False},
    {"id": "gpt-4.1-mini",    "label": "GPT-4.1-mini",    "base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY",   "reasoning": False},
    {"id": "gpt-4.1-nano",    "label": "GPT-4.1-nano",    "base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY",   "reasoning": False},
    {"id": "gpt-4o",          "label": "GPT-4o",          "base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY",   "reasoning": False},
    {"id": "gpt-4o-mini",     "label": "GPT-4o-mini",     "base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY",   "reasoning": False},
    {"id": "o4-mini",         "label": "o4-mini",         "base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY",   "reasoning": True},
    # DeepSeek
    {"id": "deepseek-chat",   "label": "DeepSeek V3",     "base_url": "https://api.deepseek.com",  "key_env": "DEEPSEEK_API_KEY", "reasoning": False},
    {"id": "deepseek-v4-pro", "label": "DeepSeek V4-pro", "base_url": "https://api.deepseek.com",  "key_env": "DEEPSEEK_API_KEY", "reasoning": True},
]


# ── 场景加载 ───────────────────────────────────────────────────────────────
def load_scenarios(args) -> list[dict]:
    """三种来源：外部文件 > CLI 快测 > 内置 scenarios.py"""

    # 来源1：外部 YAML / JSON 文件
    if getattr(args, "scenarios_file", None):
        path = Path(args.scenarios_file)
        if not path.exists():
            print(f"❌ 文件不存在: {path}"); sys.exit(1)
        text = path.read_text(encoding="utf-8")
        if path.suffix in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(text)
            except ImportError:
                print("❌ 需要 pyyaml：pip install pyyaml"); sys.exit(1)
        else:
            data = json.loads(text)
        return data["scenarios"]

    # 来源2：CLI 快测（--system + --cases）
    if getattr(args, "system", None):
        cases = [c.strip() for c in args.cases.split(",")]
        return [{
            "id":         "quick",
            "name":       "Quick Test",
            "max_tokens": getattr(args, "max_tokens", 800),
            "system":     args.system,
            "cases":      cases,
        }]

    # 来源3：内置场景库
    from scenarios import SCENARIOS
    return SCENARIOS


# ── 核心执行 ───────────────────────────────────────────────────────────────
def get_client(model_cfg: dict) -> OpenAI | None:
    key = os.environ.get(model_cfg["key_env"], "")
    if not key:
        return None
    return OpenAI(api_key=key, base_url=model_cfg["base_url"])


def run_one(client, model_id, system, user, max_tokens, is_reasoning) -> dict:
    effective_max = max_tokens * 6 if is_reasoning else max_tokens
    token_param   = "max_completion_tokens" if is_reasoning else "max_tokens"
    t0 = time.time()
    r  = client.chat.completions.create(
        model=model_id,
        **{token_param: effective_max},
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
    )
    msg = r.choices[0].message
    return {
        "content":         (msg.content or "").strip(),
        "reasoning_chars": len(getattr(msg, "reasoning_content", None) or ""),
        "elapsed_s":       round(time.time() - t0, 1),
        "total_tokens":    r.usage.total_tokens,
        "finish_reason":   r.choices[0].finish_reason,
    }


def sep(char="=", n=60): return char * n


# ── 主逻辑 ─────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(
        description="infra-model-eval：场景化多模型测评",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    # 场景来源（三选一）
    g = p.add_mutually_exclusive_group()
    g.add_argument("--scenarios-file", metavar="PATH",
                   help="YAML/JSON 场景文件（项目深测）")
    g.add_argument("--system", metavar="PROMPT",
                   help="System prompt（对话快测，配合 --cases 使用）")

    # 快测参数
    p.add_argument("--cases",      metavar="c1,c2,...", default="",
                   help="测试用例，逗号分隔（--system 模式必填）")
    p.add_argument("--max-tokens", type=int, default=800,
                   help="快测模式 max_tokens（默认 800）")

    # 过滤（内置场景库模式）
    p.add_argument("--scenario", metavar="ID[,ID]",
                   help="内置场景 id 过滤，逗号分隔")

    # 通用
    p.add_argument("--model", metavar="ID[,ID]",
                   help="模型 id 过滤，逗号分隔，默认全部")
    p.add_argument("--no-save", action="store_true",
                   help="不保存结果文件")

    args = p.parse_args()

    # 快测模式校验
    if args.system and not args.cases:
        p.error("--system 模式需要同时提供 --cases")

    # 加载场景
    all_scenarios = load_scenarios(args)

    # 内置场景库支持 --scenario 过滤
    if not args.scenarios_file and not args.system and args.scenario:
        wanted = set(args.scenario.split(","))
        all_scenarios = [s for s in all_scenarios if s["id"] in wanted]

    # 模型过滤
    wanted_models = set(args.model.split(",")) if args.model else None
    models = [m for m in MODELS if not wanted_models or m["id"] in wanted_models]

    if not all_scenarios:
        print("没有匹配的场景"); sys.exit(1)
    if not models:
        print("没有匹配的模型"); sys.exit(1)

    # ── 执行测评 ──────────────────────────────────────────────────────────
    all_results  = {"timestamp": datetime.now().isoformat(), "runs": []}
    report_lines = [f"# Model Eval Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]

    for scenario in all_scenarios:
        print(f"\n{sep()}")
        print(f"  场景: {scenario['name']}  [{scenario['id']}]")
        print(sep())
        report_lines.append(f"\n## {scenario['name']}\n")

        for case in scenario["cases"]:
            print(f"\n  输入: 「{case}」")
            print(f"  {sep('-', 56)}")
            report_lines.append(f"\n### `{case}`\n")

            for model_cfg in models:
                client = get_client(model_cfg)
                label  = model_cfg["label"]

                if not client:
                    print(f"  [{label}] ⚠️  缺少 {model_cfg['key_env']}，跳过")
                    continue

                print(f"\n  [{label}]")
                try:
                    res    = run_one(client, model_cfg["id"],
                                     scenario["system"], case,
                                     scenario["max_tokens"], model_cfg["reasoning"])
                    output = res["content"] or "(空输出)"
                    print(output)
                    meta   = f"  ⏱ {res['elapsed_s']}s | tokens: {res['total_tokens']}"
                    if res["reasoning_chars"]:
                        meta += f" | 推理: {res['reasoning_chars']} chars"
                    print(meta)

                    report_lines.append(f"**{label}** ⏱{res['elapsed_s']}s / {res['total_tokens']} tok\n")
                    report_lines.append(f"```\n{output}\n```\n")
                    all_results["runs"].append({
                        "scenario": scenario["id"], "case": case,
                        "model": model_cfg["id"], "model_label": label, **res,
                    })
                except Exception as e:
                    print(f"  ❌ {e}")
                    report_lines.append(f"**{label}** ❌ `{e}`\n")

    # ── 保存结果 ──────────────────────────────────────────────────────────
    if not args.no_save:
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_out = results_dir / f"{ts}.json"
        md_out   = results_dir / f"{ts}.md"
        json_out.write_text(json.dumps(all_results, ensure_ascii=False, indent=2))
        md_out.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"\n{sep()}\n  结果已保存:\n    {json_out}\n    {md_out}")


if __name__ == "__main__":
    main()
