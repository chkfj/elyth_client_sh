import sys
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static, ContentSwitcher
from textual.containers import Vertical, ScrollableContainer
from textual.content import Content
from textual.markup import MarkupError
from client.tui.widgets.header import ElythHeader
from client.tui.widgets.post_card import PostCard
from client.tui.widgets.modal import PostInputModal, SettingsModal
from client.tui.widgets.thread import ThreadView
from client.api import ElythApiClient
from client.settings import load_settings, save_settings

class ElythApp(App):
    """ELYTH TUI クライアントのメインアプリケーション"""
    
    CSS_PATH = "styles.tcss"
    
    BINDINGS = [
        ("q", "quit", "終了"),
        ("n", "new_post", "新規投稿"),
        ("r", "refresh_all", "再読み込み"),
        ("s", "open_settings", "設定"),
    ]

    def __init__(self, mock_mode=False, readonly_mode=False, **kwargs):
        super().__init__(**kwargs)
        self.mock_mode = mock_mode
        self.readonly_mode = readonly_mode
        self.api = ElythApiClient(mock_mode=self.mock_mode, readonly_mode=self.readonly_mode)
        self.current_thread_id = None
        self.auto_refresh_enabled = True
        self.auto_refresh_interval = 30
        self._refresh_timer = None

    def compose(self) -> ComposeResult:
        # カスタムヘッダーと標準フッター
        yield ElythHeader(id="app-header")
        
        # メイン画面切り替え器 (タブ表示とスレッド詳細表示の切り替え用)
        with ContentSwitcher(id="main-switcher", initial="tabs-view"):
            # タブ表示
            with TabbedContent(id="tabs-view"):
                with TabPane("タイムライン", id="timeline-tab"):
                    yield ScrollableContainer(id="timeline-container", classes="scroll-container")
                with TabPane("自分の投稿", id="my-posts-tab"):
                    yield ScrollableContainer(id="my-posts-container", classes="scroll-container")
                with TabPane("ヘルプ & ショートカット", id="help-tab"):
                    yield Static(self._get_help_text(), id="help-text-widget")
            
            # スレッド表示用のコンテナ (動的にThreadViewを出し入れする)
            yield Vertical(id="thread-view-container")
            
        yield Footer()

    def _get_help_text(self) -> str:
        """ヘルプ画面のテキスト"""
        mode_str = "[bold #ff6b6b]MOCK モード[/]" if self.mock_mode else "[bold #00c8d4]本番モード[/]"
        refresh_status = "[bold #00c8d4]有効[/]" if self.auto_refresh_enabled else "[bold #ff6b6b]無効[/]"
        refresh_interval = self.auto_refresh_interval
        text = (
            f"\n"
            f"  [bold #00c8d4]ELYTH TUI クライアントへようこそ！[/] (現在のモード: {mode_str})\n\n"
            f"  [bold #ec4899]基本操作ショートカット:[/]\n"
            f"    * [bold #ffffff]Tab[/]           : タブの切り替え\n"
            f"    * [bold #ffffff]n[/]             : 新規ルート投稿の作成\n"
            f"    * [bold #ffffff]r[/]             : タイムラインとマイ投稿の再読み込み\n"
            f"    * [bold #ffffff]s[/]             : 設定画面を開く\n"
            f"    * [bold #ffffff]q[/]             : アプリケーションの終了\n\n"
            f"  [bold #ec4899]投稿カード内の操作 (マウス操作対応):[/]\n"
            f"    * [bold #ffffff]Likeボタン[/]    : 投稿に「いいね」します。(※本番モードではモックのみ動作)\n"
            f"    * [bold #ffffff]Replyボタン[/]   : 投稿へ返信します。(※本番モードではモックのみ動作)\n"
            f"    * [bold #ffffff]View Thread[/]   : 返信ツリーと会話詳細スレッドを表示します。\n\n"
            f"  [bold #ec4899]スレッド表示内での操作:[/]\n"
            f"    * [bold #ffffff]←ボタン[/]      : タイムライン表示に戻ります。\n"
            f"    * [bold #ffffff]Esc / Backspace[/]: タイムライン表示に戻ります。\n\n"
            f"  [bold #5c6370]※ 自動更新: {refresh_status} (間隔: {refresh_interval}秒)[/]。設定画面(s)で変更できます。\n"
        )
        Content.from_markup(text)
        return text

    async def on_mount(self) -> None:
        """アプリ起動時の初期化と自動更新タイマー設定"""
        self.title = "ELYTH TUI"
        self.sub_title = "Mock Mode" if self.mock_mode else "Live API Connection"
        
        # 設定の読み込み
        settings = load_settings()
        self.auto_refresh_enabled = settings.get("auto_refresh_enabled", True)
        self.auto_refresh_interval = settings.get("auto_refresh_interval", 30)
        
        # 初回データ取得
        await self.action_refresh_all()
        
        # 自動更新タイマーのセットアップ
        self._setup_refresh_timer()

    def _setup_refresh_timer(self) -> None:
        """自動更新タイマーをセットアップ"""
        # 既存のタイマーをクリア
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
            self._refresh_timer = None
        
        # 自動更新が有効な場合のみタイマーをセット
        if self.auto_refresh_enabled and self.auto_refresh_interval > 0:
            self._refresh_timer = self.set_interval(
                self.auto_refresh_interval, 
                self.action_refresh_all,
                name="auto_refresh"
            )

    async def action_refresh_all(self) -> None:
        """すべての表示データを最新化する"""
        await self.refresh_header_metrics()
        await self.refresh_timeline()
        await self.refresh_my_posts()
        
        # もし現在スレッド詳細を表示中なら、そのスレッドもリフレッシュする
        switcher = self.query_one("#main-switcher", ContentSwitcher)
        if switcher.current == "thread-view-container" and self.current_thread_id:
            thread_container = self.query_one("#thread-view-container", Vertical)
            for child in thread_container.walk_children():
                if isinstance(child, ThreadView):
                    await child.load_thread()

    async def refresh_header_metrics(self) -> None:
        """ヘッダーのユーザーメトリクスを更新"""
        try:
            # informationから timeline と my_metrics を取得
            res = await self.api.get_information(include=["my_metrics"])
            metrics = res.get("my_metrics", {})
            
            header = self.query_one("#app-header", ElythHeader)
            header.followers = metrics.get("follower_count", 0)
            header.following = metrics.get("following_count", 0)
            header.posts = metrics.get("post_count", 0)
            header.balance = metrics.get("glyph_balance", 0)
            
            # APIキーに対応するアカウントのハンドル・名前の取得 (モックか本番かで切り替え)
            if self.mock_mode:
                header.handle = self.api.mock_db.my_handle
                header.username = self.api.mock_db.my_name
            else:
                # 本番は自分の過去の投稿からアカウント名とハンドルを取得する (キャッシュがない場合のみ実行)
                if header.handle == "..." or header.handle == "my_account":
                    try:
                        my_posts_res = await self.api.get_my_posts(limit=1)
                        posts = my_posts_res.get("posts", [])
                        if posts:
                            header.handle = posts[0].get("author_handle", "my_account")
                            header.username = posts[0].get("author_name", "AITuber")
                        else:
                            header.handle = "my_account"
                            header.username = "AITuber"
                    except Exception:
                        header.handle = "my_account"
                        header.username = "AITuber"
        except Exception as e:
            self.notify(f"メトリクスの取得に失敗: {e}", severity="error")

    async def refresh_timeline(self) -> None:
        """タイムラインタブの中身を更新"""
        container = self.query_one("#timeline-container", ScrollableContainer)
        
        # 現在のスクロール位置を保存（y座標のみ）
        try:
            current_scroll_y = container.scroll_y
        except AttributeError:
            # scroll_y プロパティが存在しない場合は0とする
            current_scroll_y = 0
        
        try:
            res = await self.api.get_information(include=["timeline"], timeline_limit=20)
            new_timeline = res.get("timeline", [])
            
            if not new_timeline:
                # タイムラインが空の場合は従来通り全削除してメッセージ表示
                for child in container.walk_children():
                    await child.remove()
                await container.mount(Static("[grey]タイムラインに投稿がありません。[/]"))
                # スクロール位置を復元しようとするが、エラーなら無視
                try:
                    container.scroll_to(y=current_scroll_y, animate=False)
                except Exception:
                    pass
                return
            
            # 既存のPostCardウィジェットを投稿IDでマッピング
            existing_cards = {
                card.post["id"]: card 
                for card in container.walk_children(PostCard)
            }
            
            # 新しいデータに基づいてウィジェットを更新・追加・削除
            new_card_ids = {post["id"] for post in new_timeline}
            existing_card_ids = set(existing_cards.keys())
            
            # 削除が必要なウィジェット (新しいデータに存在しないもの)
            to_remove = existing_card_ids - new_card_ids
            for post_id in to_remove:
                await existing_cards[post_id].remove()
            
            # すべての既存ウィジェットを一旦削除
            for child in list(container.walk_children()):
                await child.remove()
                
            # 新しいデータ順序でウィジェットを作成・マウント
            for post in new_timeline:
                await container.mount(PostCard(post, self.api))
            
            # スクロール位置を復元しようとするが、エラーなら無視
            try:
                container.scroll_to(y=current_scroll_y, animate=False)
            except Exception:
                pass
                
        except Exception as e:
            # エラー時は従来通りの表示
            for child in container.walk_children():
                await child.remove()
            await container.mount(Static(f"[bold #ff6b6b]タイムライン取得エラー: {e}[/]"))
            # エラー時もスクロール位置を復元しようとするが、エラーなら無視
            try:
                container.scroll_to(y=current_scroll_y, animate=False)
            except Exception:
                pass

    async def refresh_my_posts(self) -> None:
        """マイ投稿タブの中身を更新"""
        container = self.query_one("#my-posts-container", ScrollableContainer)
        
        # 現在のスクロール位置を保存（y座標のみ）
        try:
            current_scroll_y = container.scroll_y
        except AttributeError:
            # scroll_y プロパティが存在しない場合は0とする
            current_scroll_y = 0
        
        try:
            res = await self.api.get_my_posts(limit=20)
            new_posts = res.get("posts", [])
            
            if not new_posts:
                # 投稿が空の場合は従来通り全削除してメッセージ表示
                for child in container.walk_children():
                    await child.remove()
                await container.mount(Static("[grey]過去の投稿がありません。[/]"))
                # スクロール位置を復元しようとするが、エラーなら無視
                try:
                    container.scroll_to(y=current_scroll_y, animate=False)
                except Exception:
                    pass
                return
            
            # 既存のPostCardウィジェットを投稿IDでマッピング
            existing_cards = {
                card.post["id"]: card 
                for card in container.walk_children(PostCard)
            }
            
            # 新しいデータに基づいてウィジェットを更新・追加・削除
            new_post_ids = {post["id"] for post in new_posts}
            existing_post_ids = set(existing_cards.keys())
            
            # 削除が必要なウィジェット (新しいデータに存在しないもの)
            to_remove = existing_post_ids - new_post_ids
            for post_id in to_remove:
                await existing_cards[post_id].remove()
            
            # すべての既存ウィジェットを一旦削除
            for child in list(container.walk_children()):
                await child.remove()
                
            # 新しいデータ順序でウィジェットを作成・マウント
            for post in new_posts:
                await container.mount(PostCard(post, self.api))
            
            # スクロール位置を復元しようとするが、エラーなら無視
            try:
                container.scroll_to(y=current_scroll_y, animate=False)
            except Exception:
                pass
                
        except Exception as e:
            # エラー時は従来通りの表示
            for child in container.walk_children():
                await child.remove()
            await container.mount(Static(f"[bold #ff6b6b]マイ投稿取得エラー: {e}[/]"))
            # エラー時もスクロール位置を復元しようとするが、エラーなら無視
            try:
                container.scroll_to(y=current_scroll_y, animate=False)
            except Exception:
                pass

    # --- 新規投稿アクション ---
    
    async def action_new_post(self) -> None:
        """新規ルート投稿のダイアログを開く"""
        async def on_submit(text: str | None) -> None:
            if text is None:
                return
            try:
                res = await self.api.create_post(text)
                if res.get("success"):
                    self.notify("投稿を作成しました！", severity="info")
                    await self.action_refresh_all()
            except Exception as e:
                self.notify(str(e), severity="error")

        self.push_screen(PostInputModal(title="新規投稿 (Ctrl+Sで送信)"), on_submit)

    # --- メッセージハンドラー (ウィジェットからのイベント受信) ---

    async def on_post_card_reply_requested(self, event: PostCard.ReplyRequested) -> None:
        """返信ボタンが押されたとき"""
        post = event.post_card.post
        
        async def on_submit(text: str | None) -> None:
            if text is None:
                return
            try:
                res = await self.api.create_reply(text, post["id"])
                if res.get("success"):
                    self.notify("返信を送信しました！", severity="info")
                    await self.action_refresh_all()
            except Exception as e:
                self.notify(str(e), severity="error")

        title = f"@{post['author_handle']} への返信 (Ctrl+Sで送信)"
        self.push_screen(PostInputModal(title=title), on_submit)

    async def on_post_card_thread_requested(self, event: PostCard.ThreadRequested) -> None:
        """詳細スレッドボタンが押されたとき"""
        post = event.post_card.post
        post_id = post["id"]
        
        # ThreadViewを構築して切り替える
        container = self.query_one("#thread-view-container", Vertical)
        
        # 古いThreadViewがあれば削除
        for child in container.walk_children():
            await child.remove()
            
        self.current_thread_id = post_id
        
        # 新しいThreadViewを配置
        thread_view = ThreadView(post_id, self.api, self.switch_back_to_timeline)
        await container.mount(thread_view)
        
        # スイッチャーでスレッド画面を表示
        self.query_one("#main-switcher", ContentSwitcher).current = "thread-view-container"

    def switch_back_to_timeline(self) -> None:
        """スレッドビューからタイムラインに戻る"""
        self.query_one("#main-switcher", ContentSwitcher).current = "tabs-view"
        self.current_thread_id = None

    def action_open_settings(self) -> None:
        """設定画面を開く"""
        self.push_screen(SettingsModal(self))

    def update_refresh_settings(self, enabled: bool, interval: int) -> None:
        """自動更新設定を更新"""
        self.auto_refresh_enabled = enabled
        self.auto_refresh_interval = interval
        
        # 設定を保存
        settings = load_settings()
        settings["auto_refresh_enabled"] = enabled
        settings["auto_refresh_interval"] = interval
        save_settings(settings)
        
        # タイマーを再セットアップ
        self._setup_refresh_timer()
        
        status = "有効" if enabled else "無効"
        interval_text = f"{interval}秒" if interval > 0 else "無効"
        self.notify(f"自動更新を {status} に設定しました (間隔: {interval_text})", severity="info")

    def on_key(self, event) -> None:
        """キーボードのグローバルバインド"""
        if event.key in ("escape", "backspace"):
            # スレッド画面ならタイムラインに戻る
            switcher = self.query_one("#main-switcher", ContentSwitcher)
            if switcher.current == "thread-view-container":
                self.switch_back_to_timeline()
                event.prevent_default()

    async def on_shutdown(self) -> None:
        """終了時のクリーンアップ"""
        await self.api.close()
