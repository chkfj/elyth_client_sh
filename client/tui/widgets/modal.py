from textual.screen import ModalScreen
from textual.widgets import Static, Button, TextArea, Checkbox, Input
from textual.containers import Vertical, Horizontal, Grid
from textual.events import Key

class PostInputModal(ModalScreen[str]):
    """新規投稿または返信用のテキスト入力用モーダル"""

    def __init__(self, title: str = "新規投稿", placeholder: str = "", **kwargs):
        self.modal_title = title
        self.placeholder = placeholder
        super().__init__(**kwargs)

    def compose(self):
        with Vertical(id="modal-container"):
            yield Static(self.modal_title, id="modal-title")
            
            # テキストエリア (高さ5)
            text_area = TextArea(id="modal-input", classes="modal-textarea")
            text_area.focus()
            yield text_area
            
            # 文字数カウンター
            yield Static("0 / 500 文字", id="char-counter")
            
            # ボタンエリア
            with Horizontal(id="modal-footer"):
                yield Button("キャンセル", id="cancel-btn", classes="modal-btn modal-cancel-btn")
                yield Button("送信", id="submit-btn", classes="modal-btn modal-submit-btn")

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """文字数の更新と500文字制限のバリデーション"""
        text = event.text_area.text
        length = len(text)
        counter = self.query_one("#char-counter", Static)
        
        if length > 500:
            counter.update(f"[bold #ff6b6b]{length} / 500 文字 (上限を超えています)[/]")
            self.query_one("#submit-btn", Button).disabled = True
        else:
            counter.update(f"{length} / 500 文字")
            self.query_one("#submit-btn", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            text = self.query_one("#modal-input", TextArea).text.strip()
            if text:
                self.dismiss(text)
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def on_key(self, event: Key) -> None:
        """ショートカットキー処理: Ctrl+S で送信、Esc で閉じる"""
        if event.key == "ctrl+s":
            text = self.query_one("#modal-input", TextArea).text.strip()
            submit_btn = self.query_one("#submit-btn", Button)
            if text and not submit_btn.disabled:
                self.dismiss(text)
        elif event.key == "escape":
            self.dismiss(None)


class SettingsModal(ModalScreen[None]):
    """自動更新設定を変更するモーダル"""

    def __init__(self, main_app, **kwargs):
        self.main_app = main_app
        super().__init__(**kwargs)

    def compose(self):
        with Vertical(id="settings-modal-container"):
            yield Static("設定", id="settings-title")
            
            with Vertical(id="settings-form"):
                yield Static("自動更新", classes="settings-section-title")
                
                checkbox = Checkbox(
                    "自動更新を有効化",
                    id="auto-refresh-checkbox",
                    value=self.main_app.auto_refresh_enabled
                )
                yield checkbox
                
                yield Static("更新間隔 (秒) ※30秒以上", classes="settings-label")
                input_widget = Input(
                    str(self.main_app.auto_refresh_interval),
                    id="interval-input",
                    type="integer",
                    classes="settings-input"
                )
                input_widget.focus()
                yield input_widget
            
            with Horizontal(id="settings-footer"):
                yield Button("キャンセル", id="settings-cancel-btn", classes="modal-btn modal-cancel-btn")
                yield Button("保存", id="settings-save-btn", classes="modal-btn modal-submit-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "settings-save-btn":
            self._save_settings()
        elif event.button.id == "settings-cancel-btn":
            self.dismiss(None)

    def _save_settings(self) -> None:
        """設定を保存してモーダルを閉じる"""
        checkbox = self.query_one("#auto-refresh-checkbox", Checkbox)
        input_widget = self.query_one("#interval-input", Input)
        
        enabled = checkbox.value
        
        try:
            interval = int(input_widget.value)
            if interval < 30:
                interval = 30
                self.main_app.notify("更新間隔は最低30秒に設定されます", severity="warning")
        except ValueError:
            interval = self.main_app.auto_refresh_interval
            self.main_app.notify("無効な値が入力されました", severity="error")
            return
        
        self.main_app.update_refresh_settings(enabled, interval)
        self.dismiss(None)

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            self.dismiss(None)
