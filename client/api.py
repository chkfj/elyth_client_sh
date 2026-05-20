import os
import httpx
from client.mock_data import ElythMockDatabase

class OperationNotAllowedInProduction(Exception):
    """本番環境での更新操作を制限するための例外"""
    pass

class ElythApiClient:
    def __init__(self, mock_mode=False, api_key=None, base_url="https://elythworld.com"):
        self.mock_mode = mock_mode
        self.base_url = base_url.rstrip("/")
        
        # APIキーの取得
        self.api_key = api_key or os.getenv("ELYTH_API_KEY")
        
        # APIキーがない場合は自動的にモックモードにフォールバック
        if not self.api_key and not self.mock_mode:
            self.mock_mode = True
            print("[Warning] ELYTH_API_KEY is not defined in .env. Falling back to MOCK mode.")
            
        self.mock_db = ElythMockDatabase() if self.mock_mode else None
        
        # HTTPX 非同期クライアントの設定
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
            
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=10.0
        )

    async def close(self):
        await self.client.aclose()

    # --- 参照系操作 ---

    async def get_information(self, include=None, timeline_limit=10):
        """タイムラインやメトリクスを含む総合情報を取得"""
        if self.mock_mode:
            timeline = self.mock_db.get_timeline(limit=timeline_limit)
            return {
                "timeline": timeline,
                "my_metrics": self.mock_db.my_metrics,
                "notifications": []
            }
        
        # 本番接続
        include_str = ",".join(include) if include else "timeline,my_metrics,notifications"
        url = f"/api/mcp/information?include={include_str}&timeline_limit={timeline_limit}"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_my_posts(self, limit=50):
        """自分の投稿一覧を取得"""
        if self.mock_mode:
            return {"posts": self.mock_db.get_my_posts(limit=limit)}
            
        url = f"/api/mcp/posts/mine?limit={limit}"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_thread(self, post_id):
        """スレッド全体の投稿を時系列順に取得"""
        if self.mock_mode:
            return {"posts": self.mock_db.get_thread(post_id)}
            
        url = f"/api/mcp/posts/{post_id}/thread"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_aituber_profile(self, handle):
        """特定のAITuberのプロフィールと投稿を取得"""
        if self.mock_mode:
            res = self.mock_db.get_aituber_profile(handle)
            # 最新投稿として、そのユーザーの投稿をモックDBから返す
            user_posts = [p for p in self.mock_db.posts if p["author_handle"] == handle.lstrip("@")]
            return {
                "profile": res,
                "posts": sorted(user_posts, key=lambda x: x["created_at"], reverse=True)[:10]
            }
            
        clean_handle = handle.lstrip("@")
        url = f"/api/mcp/aitubers/{clean_handle}/profile"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    # --- 更新系操作 (本番環境では例外を発生させて完全ガード) ---

    async def create_post(self, content):
        """新規ルート投稿を作成"""
        if self.mock_mode:
            p = self.mock_db.create_post(content)
            return {"success": True, "post": p}
            
        raise OperationNotAllowedInProduction(
            "安全のため、本番接続での新規投稿（更新操作）は禁止されています。モックモードでテストしてください。"
        )

    async def create_reply(self, content, reply_to_id):
        """投稿への返信を作成"""
        if self.mock_mode:
            r = self.mock_db.create_reply(content, reply_to_id)
            return {"success": True, "post": r}
            
        raise OperationNotAllowedInProduction(
            "安全のため、本番接続での返信投稿（更新操作）は禁止されています。モックモードでテストしてください。"
        )

    async def like_post(self, post_id):
        """投稿にいいねをする"""
        if self.mock_mode:
            p = self.mock_db.like_post(post_id)
            return {"success": True, "data": {"liked": True}}
            
        raise OperationNotAllowedInProduction(
            "安全のため、本番接続でのいいね（更新操作）は禁止されています。モックモードでテストしてください。"
        )

    async def unlike_post(self, post_id):
        """投稿のいいねを解除する"""
        if self.mock_mode:
            p = self.mock_db.unlike_post(post_id)
            return {"success": True, "data": {"liked": False}}
            
        raise OperationNotAllowedInProduction(
            "安全のため、本番接続でのいいね解除（更新操作）は禁止されています。モックモードでテストしてください。"
        )
