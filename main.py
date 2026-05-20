#!/usr/bin/env python3
import sys
import argparse
from dotenv import load_dotenv
from client.tui.app import ElythApp

def main():
    # .env ファイルのロード
    load_dotenv()

    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(description="ELYTH TUI Client - ELYTH SNSの端末内操作クライアント")
    parser.add_argument(
        "--mock", 
        action="store_true", 
        help="モックモードでローカルシミュレーションを起動します (本番APIとの通信を行いません)"
    )
    parser.add_argument(
        "--read-only", 
        action="store_true", 
        help="書き込みを禁止するモードで起動します (本番環境での更新操作をブロック)"
    )
    args = parser.parse_args()

    # アプリケーションの構築と実行
    app = ElythApp(mock_mode=args.mock, readonly_mode=args.read_only)
    app.run()

if __name__ == "__main__":
    main()
