from datetime import datetime
from textual.widget import Widget
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual.message import Message

class PostCard(Widget):
    """個別の投稿カードを表示するウィジェット"""

    # カスタムメッセージ定義（親コンポーネントへイベントを伝えるため）
    class ReplyRequested(Message):
        def __init__(self, post_card: "PostCard"):
            self.post_card = post_card
            super().__init__()

    class ThreadRequested(Message):
        def __init__(self, post_card: "PostCard"):
            self.post_card = post_card
            super().__init__()

    def __init__(self, post_data: dict, api_client, **kwargs):
        self.post = post_data
        self.api = api_client
        super().__init__(**kwargs)

    def compose(self):
        # タイムスタンプのフォーマット
        raw_time = self.post.get("created_at", "")
        formatted_time = ""
        if raw_time:
            try:
                # ISO形式の日時をパースして分かりやすく整形
                dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                formatted_time = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                formatted_time = raw_time[:16]

        # 投稿ヘッダー (ユーザー情報と時間)
        header_text = (
            f"[bold #ffffff]{self.post.get('author_name')}[/] "
            f"[#00c8d4]@{self.post.get('author_handle')}[/] "
            f"• [grey]{formatted_time}[/]"
        )
        
        # いいねボタンのラベル
        like_count = self.post.get("like_count", 0)
        liked_by_me = self.post.get("liked_by_me", False)
        like_label = f"♥️ Liked ({like_count})" if liked_by_me else f"♡ Like ({like_count})"
        like_classes = "action-btn like-btn liked" if liked_by_me else "action-btn like-btn"

        # 返信数ラベル
        reply_count = self.post.get("reply_count", 0)
        reply_label = f"💬 Reply ({reply_count})"

        # レイアウト定義
        yield Static(header_text, classes="post-header")
        yield Static(self.post.get("content", ""), classes="post-content")
        with Horizontal(classes="post-actions"):
            yield Button(like_label, id="like-btn", classes=like_classes)
            yield Button(reply_label, id="reply-btn", classes="action-btn reply-btn")
            yield Button("🔍 View Thread", id="thread-btn", classes="action-btn thread-btn")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        
        if button_id == "like-btn":
            await self.toggle_like(event.button)
        elif button_id == "reply-btn":
            self.post_message(self.ReplyRequested(self))
        elif button_id == "thread-btn":
            self.post_message(self.ThreadRequested(self))

    async def toggle_like(self, button: Button) -> None:
        liked_by_me = self.post.get("liked_by_me", False)
        post_id = self.post.get("id")
        
        try:
            if liked_by_me:
                # いいね解除
                res = await self.api.unlike_post(post_id)
                if res.get("success"):
                    self.post["liked_by_me"] = False
                    self.post["like_count"] = max(0, self.post.get("like_count", 0) - 1)
                    self.app.notify("いいねを解除しました", severity="info")
            else:
                # いいね
                res = await self.api.like_post(post_id)
                if res.get("success"):
                    self.post["liked_by_me"] = True
                    self.post["like_count"] = self.post.get("like_count", 0) + 1
                    self.app.notify("いいねしました！", severity="info")
            
            # ボタン表示を更新
            like_count = self.post["like_count"]
            if self.post["liked_by_me"]:
                button.label = f"♥️ Liked ({like_count})"
                button.add_class("liked")
            else:
                button.label = f"♡ Like ({like_count})"
                button.remove_class("liked")
                
        except Exception as e:
            # 本番環境での書き込み制限例外などを表示
            self.app.notify(str(e), severity="error")
