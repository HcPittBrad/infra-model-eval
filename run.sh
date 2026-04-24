#!/bin/bash
# infra-model-eval 入口，自动激活 venv
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/.venv/bin/activate"
python "$DIR/eval.py" "$@"
