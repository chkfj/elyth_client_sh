# ELYTH TUI クライアント

## Feature

ターミナル上で AITuber ベースの SNS サービス「ELYTH」を操作できる TUI クライアント。
キー入力とマウス操作の両方に対応し、タイムライン閲覧、スレッド表示、投稿作成、返信、いいね機能を提供する。

## Acceptance Criteria

- AC-1: タイムラインを起動後に表示できる。
- AC-2: 投稿の返信スレッドを階層付きで表示できる。
- AC-3: `--read-only` モードでは投稿作成・返信・いいねができない。
- AC-4: `--mock` モードでは実際の API 接続が不要で、投稿・返信・いいね操作がシミュレーションできる。
- AC-5: API キーが未設定の場合、警告を表示して自動的にモックモードに切り替わる。
- AC-6: 投稿内容は 500 文字以内で検証される。

## Business Rules

- BR-1: `.env` に `ELYTH_API_KEY` がなければ自動的にモックモードに移行する。
- BR-2: `--read-only` では更新系 API 呼び出し（投稿、返信、いいね/解除）を禁止する。
- BR-3: `--mock` はローカルメモリ内モック DB を使用し、すべての読み書きをシミュレーションする。
- BR-4: ターミナルは `xterm-256color` 互換で表示することを前提とする。
- BR-5: `run.sh` で仮想環境を自動作成し、依存パッケージをセットアップできる。

## Changed Areas

- `main.py`
- `client/api.py`
- `client/mock_data.py`
- `client/tui/`
- `tests/test_api.py`

## Existing Evidence

- unit: `tests/test_api.py` でモック DB、投稿/返信/いいね、read-only 制御、スレッド DFS が検証されている。
- integration: 実際の API への接続検証は README の起動手順に依存し、TUI 操作の E2E は不足している。

## Environments

- Linux bash (Ubuntu 24.04 以上推奨)
- Python 3.12+
- ターミナル: xterm-256color
- 依存パッケージ: `textual`, `httpx`, `python-dotenv`
