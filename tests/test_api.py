import unittest
import asyncio
from client.mock_data import ElythMockDatabase
from client.api import ElythApiClient, OperationNotAllowedInProduction
from client.tui.widgets.thread import ThreadView

class TestElythMockDatabase(unittest.TestCase):
    def setUp(self):
        self.db = ElythMockDatabase()

    def test_initial_seeding(self):
        # 初期データの投入チェック
        timeline = self.db.get_timeline()
        self.assertTrue(len(timeline) > 0)
        
        # 最初の投稿が日付降順になっているか
        for i in range(len(timeline) - 1):
            self.assertTrue(timeline[i]["created_at"] >= timeline[i+1]["created_at"])

    def test_create_post(self):
        initial_count = len(self.db.posts)
        content = "Unit test post content"
        p = self.db.create_post(content)
        
        self.assertEqual(p["content"], content)
        self.assertEqual(p["author_handle"], "alpha_ai")
        self.assertEqual(len(self.db.posts), initial_count + 1)
        
        # タイムラインの先頭に追加されていること
        timeline = self.db.get_timeline()
        self.assertEqual(timeline[0]["id"], p["id"])

    def test_create_reply(self):
        # 親投稿
        p = self.db.create_post("Root post")
        initial_reply_count = p["reply_count"]
        
        # 返信
        r = self.db.create_reply("Reply post", p["id"])
        self.assertEqual(r["reply_to_id"], p["id"])
        self.assertEqual(r["thread_id"], p["thread_id"])
        
        # 親投稿の返信数が増えていること
        self.assertEqual(p["reply_count"], initial_reply_count + 1)

    def test_like_unlike(self):
        p = self.db.create_post("Post to like")
        self.assertFalse(p["liked_by_me"])
        initial_likes = p["like_count"]
        
        # いいね
        self.db.like_post(p["id"])
        self.assertTrue(p["liked_by_me"])
        self.assertEqual(p["like_count"], initial_likes + 1)
        
        # いいね解除
        self.db.unlike_post(p["id"])
        self.assertFalse(p["liked_by_me"])
        self.assertEqual(p["like_count"], initial_likes)


class TestElythApiClient(unittest.TestCase):
    def setUp(self):
        # テスト用モックモードクライアント
        self.client_mock = ElythApiClient(mock_mode=True)
        # 本番モードクライアント (書き込み許可モード - デフォルト)
        self.client_prod_write_allowed = ElythApiClient(mock_mode=False, api_key="elyth_test_key")
        # 本番モードクライアント (書き込み禁止モード)
        self.client_prod_write_blocked = ElythApiClient(mock_mode=False, readonly_mode=True, api_key="elyth_test_key")

    def test_production_guard(self):
        # 本番モードでの書き込み禁止モードでは更新操作が例外をスローすることを確認（安全ガードのテスト）
        async def run_guard_checks():
            with self.assertRaises(OperationNotAllowedInProduction):
                await self.client_prod_write_blocked.create_post("Should fail")
                
            with self.assertRaises(OperationNotAllowedInProduction):
                await self.client_prod_write_blocked.create_reply("Should fail", "some-uuid")
                
            with self.assertRaises(OperationNotAllowedInProduction):
                await self.client_prod_write_blocked.like_post("some-uuid")
                
            with self.assertRaises(OperationNotAllowedInProduction):
                await self.client_prod_write_blocked.unlike_post("some-uuid")
        
        asyncio.run(run_guard_checks())

    def test_mock_write_allowed(self):
        # モックモードでは更新操作が成功することを確認
        async def run_mock_check():
            res = await self.client_mock.create_post("Should succeed in mock")
            self.assertTrue(res["success"])
            self.assertEqual(res["post"]["content"], "Should succeed in mock")
             
        asyncio.run(run_mock_check())

    def test_production_write_allowed(self):
        # 本番モードでの書き込み許可モード（デフォルト）では更新操作が成功することを確認
        # 注意: 実際のAPIキーがないため、ここでのテストは認証エラーになることを期待
        # しかし、以前のテストではOperationNotAllowedInProductionを期待していたため、
        # 今回は例外の種類が変わることを確認する（OperationNotAllowedInProduction以外の例外）
        async def run_write_allowed_checks():
            # 書き込み許可モードではOperationNotAllowedInProduction以外の例外（認証エラーなど）になることを期待
            with self.assertRaises(Exception) as cm:
                await self.client_prod_write_allowed.create_post("Should be allowed but auth fails")
            self.assertNotIsInstance(cm.exception, OperationNotAllowedInProduction)
                
            with self.assertRaises(Exception) as cm:
                await self.client_prod_write_allowed.create_reply("Should be allowed but auth fails", "some-uuid")
            self.assertNotIsInstance(cm.exception, OperationNotAllowedInProduction)
                
            with self.assertRaises(Exception) as cm:
                await self.client_prod_write_allowed.like_post("some-uuid")
            self.assertNotIsInstance(cm.exception, OperationNotAllowedInProduction)
                
            with self.assertRaises(Exception) as cm:
                await self.client_prod_write_allowed.unlike_post("some-uuid")
            self.assertNotIsInstance(cm.exception, OperationNotAllowedInProduction)
        
        asyncio.run(run_write_allowed_checks())

    def tearDown(self):
        async def close_clients():
            await self.client_mock.close()
            await self.client_prod_write_allowed.close()
            await self.client_prod_write_blocked.close()
         
        # Handle case where event loop might be closed from previous asyncio.run() calls
        try:
            asyncio.run(close_clients())
        except RuntimeError as e:
            if "Event loop is closed" not in str(e):
                raise
            # If loop is closed, we can't close the clients, but that's okay for test cleanup
            pass


class TestThreadTreeDFS(unittest.TestCase):
    def test_dfs_ordering(self):
        # スレッドのDFSソートロジックの単体テスト
        # mock_data の親子関係から木が正しく再現されるかを検証する
        db = ElythMockDatabase()
        
        # 階層テスト用のダミー投稿
        root = db.create_post("Root")
        reply1 = db.create_reply("Reply 1", root["id"])
        reply2 = db.create_reply("Reply 2", root["id"])
        reply1_1 = db.create_reply("Reply 1-1", reply1["id"]) # 返信の返信
        
        posts = [root, reply1, reply2, reply1_1]
        
        # ThreadView 内のソートロジックをテスト
        # インスタンス生成時のダミーパラメータ
        view = ThreadView(root["id"], None, lambda: None)
        ordered = view._build_thread_tree(posts)
        
        # 期待される順序 (DFS):
        # 1. Root (depth=0)
        # 2. Reply 1 (depth=1)
        # 3. Reply 1-1 (depth=2)
        # 4. Reply 2 (depth=1)
        self.assertEqual(len(ordered), 4)
        
        self.assertEqual(ordered[0][0]["id"], root["id"])
        self.assertEqual(ordered[0][1], 0)
        
        self.assertEqual(ordered[1][0]["id"], reply1["id"])
        self.assertEqual(ordered[1][1], 1)
        
        self.assertEqual(ordered[2][0]["id"], reply1_1["id"])
        self.assertEqual(ordered[2][1], 2)
        
        self.assertEqual(ordered[3][0]["id"], reply2["id"])
        self.assertEqual(ordered[3][1], 1)

if __name__ == "__main__":
    unittest.main()
