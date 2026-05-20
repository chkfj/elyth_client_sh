from collections import defaultdict
from textual.widget import Widget
from textual.widgets import Static, Button
from textual.containers import Vertical, ScrollableContainer
from client.tui.widgets.post_card import PostCard

class ThreadView(Widget):
    """特定のスレッド全体を階層構造（ツリー形式）で表示するウィジェット"""

    def __init__(self, post_id: str, api_client, on_back_callback, **kwargs):
        self.post_id = post_id
        self.api = api_client
        self.on_back = on_back_callback
        self.posts_data = []
        super().__init__(**kwargs)

    def compose(self):
        # 戻るボタン
        yield Button("← タイムラインに戻る", id="back-to-timeline-btn", classes="thread-back-btn")
        
        # 投稿カードを挿入するスクロール容器
        yield ScrollableContainer(id="thread-cards-container", classes="scroll-container")

    async def on_mount(self) -> None:
        await self.load_thread()

    async def load_thread(self) -> None:
        container = self.query_one("#thread-cards-container", ScrollableContainer)
        # 既存のカードをクリア
        for child in container.walk_children():
            await child.remove()

        try:
            # スレッドデータのロード
            res = await self.api.get_thread(self.post_id)
            posts = res.get("posts", [])
            self.posts_data = posts
            
            if not posts:
                await container.mount(Static("[bold #ff6b6b]スレッドが空か、見つかりません。[/]"))
                return
                
            # ツリー構造の構築 (DFS)
            ordered_posts = self._build_thread_tree(posts)
            
            for post, depth in ordered_posts:
                card = PostCard(post, self.api)
                # インデント幅を設定 (深さ1につき4スペース相当のマージン)
                card.styles.margin_left = depth * 4
                # インデントがある場合は枠線の色やスタイルを変えるなどの演出も可能
                if depth > 0:
                    card.styles.border = ("round", "#30363d")
                await container.mount(card)
                
        except Exception as e:
            await container.mount(Static(f"[bold #ff6b6b]スレッドの読み込みに失敗しました: {e}[/]"))

    def _build_thread_tree(self, posts: list) -> list:
        """フラットな投稿リストから、返信関係に基づくツリー構造を構築し、DFS順の(post, depth)リストを返します。"""
        post_map = {p["id"]: p for p in posts}
        
        # ルート投稿を探す
        # reply_to_idがNoneのもの、またはreply_to_idが取得したスレッド内に存在しないものをルートとする
        root = None
        for p in posts:
            parent_id = p.get("reply_to_id")
            if not parent_id or parent_id not in post_map:
                root = p
                break
                
        if not root:
            # 万が一ルートが見つからなければ最初のものをルートとする
            root = posts[0]

        # 親IDから子投稿へのマップを作成
        children_map = defaultdict(list)
        for p in posts:
            if p["id"] != root["id"]:
                children_map[p.get("reply_to_id")].append(p)

        # 各親ノードの子リストを作成時間順でソート
        for parent_id in children_map:
            children_map[parent_id].sort(key=lambda x: x.get("created_at", ""))

        # DFSトラバーサルによる並び替え
        result = []
        
        def dfs(node, depth):
            result.append((node, depth))
            for child in children_map[node["id"]]:
                dfs(child, depth + 1)

        dfs(root, 0)
        return result

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-to-timeline-btn":
            self.on_back()
