import csv
import unittest

from support import DATA, StateTestCase, run, run_json

from obelisk.models import Transaction
from obelisk.transactions import TransactionTable


def sample(numbers):
    return [Transaction(f"TX-{n}", "CLEARED", "1.00", "2025-01-01", "agent01") for n in numbers]


def source_ids():
    with open(DATA / "transactions" / "transactions.csv", newline="", encoding="utf-8") as fh:
        return [row["id"] for row in csv.DictReader(fh)]


MIDDLE = source_ids()[250]


class TransactionLookup(StateTestCase):
    def test_known_transaction(self):
        code, out, _ = run("transaction", MIDDLE)
        self.assertEqual(code, 0)
        for label in ("TRANSACTION", f"ID: {MIDDLE}", "STATUS:", "AMOUNT:", "DATE:", "OPERATOR:"):
            self.assertIn(label, out)

    def test_lowercase_id(self):
        self.assertEqual(run_json("transaction", MIDDLE.lower())["id"], MIDDLE)

    def test_missing_transaction(self):
        code, _, err = run("transaction", "TX-10003")
        self.assertEqual(code, 3)
        self.assertIn("not found", err)

    def test_out_of_range_transactions(self):
        for tx in ("TX-1", "TX-99999999"):
            self.assertEqual(run("transaction", tx)[0], 3, tx)

    def test_invalid_id(self):
        for bad in ("10005", "TX-", "TX-abc", "hello"):
            self.assertEqual(run("transaction", bad)[0], 4, bad)

    def test_first_and_last_transactions(self):
        ids = source_ids()
        for tx in (ids[0], ids[-1]):
            self.assertEqual(run_json("transaction", tx)["id"], tx)

    def test_every_transaction_is_retrievable(self):
        for tx in source_ids():
            self.assertEqual(run_json("transaction", tx)["id"], tx)


class TableUnit(unittest.TestCase):
    def test_all_sizes(self):
        for size in range(0, 40):
            numbers = [100 + 3 * i for i in range(size)]
            table = TransactionTable(sample(reversed(numbers)))
            for n in numbers:
                self.assertIsNotNone(table.find(f"TX-{n}"), (size, n))
            for n in [99, 101, 100 + 3 * size, 100 + 3 * size + 1]:
                if n not in numbers:
                    self.assertIsNone(table.find(f"TX-{n}"), (size, n))


if __name__ == "__main__":
    unittest.main()
