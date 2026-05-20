#!/bin/bash
set -e

# プロジェクトのディレクトリに移動
cd "$(dirname "$0")"

# 仮想環境がなければ作成
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# 仮想環境のアクティベート
source .venv/bin/activate

# 依存パッケージのインストール/更新
echo "Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# メインプログラムの起動
echo "Starting ELYTH TUI Client..."
python main.py "$@"
