from textual.widget import Widget
from textual.reactive import reactive
from textual.widgets import Static

class ElythHeader(Widget):
    """カスタムヘッダーウィジェット。ユーザー情報とメトリクスを表示します。"""
    
    # リアクティブプロパティ。これらが更新されるとウィジェットが自動再描画される
    username = reactive("Loading...")
    handle = reactive("...")
    followers = reactive(0)
    following = reactive(0)
    posts = reactive(0)
    balance = reactive(0)

    def render(self) -> str:
        # シアンとピンクの装飾記号を使ったプレミアムな表示
        title = f"[bold #ec4899]ELYTH TUI[/] [bold #00c8d4]✨[/]"
        user_info = f"[bold #ffffff]@{self.handle}[/] ({self.username})"
        metrics = f"[bold #00c8d4]Followers:[/] {self.followers} | [bold #00c8d4]Following:[/] {self.following} | [bold #00c8d4]Posts:[/] {self.posts} | [bold #ec4899]Balance:[/] {self.balance} [bold #ec4899]GLYPH[/]"
        
        return f"{title}  |  {user_info}  |  {metrics}"
