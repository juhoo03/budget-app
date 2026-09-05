import unittest
import tempfile
import shutil
import os
from budget_app.storage import StorageManager
from budget_app.services import BudgetService
from budget_app.decorators import BudgetAppError


class TestBudgetApp(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.storage = StorageManager(self.test_dir)
        self.service = BudgetService(self.storage)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_add_and_list_transaction(self):
        # 영문 'food' -> 한글 기본 카테고리 '식비'로 변경
        tx = self.service.add_transaction("2024-01-15", "expense", "식비", 12000, "점심", ["meal"])
        self.assertEqual(tx.id, "TX-000001")
        
        txs = self.service.list_transactions(limit=10)
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].amount, 12000)

    def test_category_remove_with_replace(self):
        # '식비' 카테고리로 거래 추가
        self.service.add_transaction("2024-01-15", "expense", "식비", 12000, "점심", [])
        
        # 대체 카테고리 옵션 없이 삭제 시 예외 발생 검증
        with self.assertRaises(BudgetAppError):
            self.service.remove_category("식비")
            
        # '식비' 거래들을 '기타'로 일괄 변경하며 삭제 검증
        self.service.remove_category("식비", replace_with="기타")
        txs = self.service.list_transactions(limit=10)
        self.assertEqual(txs[0].category, "기타")
        self.assertNotIn("식비", self.storage.get_all_categories())

    def test_import_strict_rollback(self):
        csv_path = os.path.join(self.test_dir, "test.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("date,type,category,amount,memo,tags\n")
            f.write("2024-01-01,expense,식비,1000,정상,tag\n")
            f.write("invalid-date,expense,식비,2000,오류행,\n")
            
        # strict 모드에서는 오류 행이 있으면 예외 발생 및 반영 0건 보장
        with self.assertRaises(BudgetAppError):
            self.service.import_from_csv(csv_path, strict=True)
            
        txs = self.service.list_transactions(limit=10)
        self.assertEqual(len(txs), 0)


if __name__ == "__main__":
    unittest.main()