import unittest

from support import DATA, StateTestCase, run_json

from obelisk.indexer import build_index
from obelisk.ingest import ingest_path
from obelisk.models import Document


def make_docs(n):
    return [
        Document(id=f"DOC-{i:04d}", title=f"Doc {i}", type="t", source="x",
                 text=f"alpha marker{i:04d}")
        for i in range(1, n + 1)
    ]


class VaultIndex(StateTestCase):
    def test_index_reports_every_document(self):
        result = run_json("index")
        self.assertEqual(result["indexed"], result["documents"])

    def test_every_document_is_searchable_by_its_marker(self):
        docs = ingest_path(DATA).documents
        for doc in docs:
            marker = f"marker{doc.id.split('-')[1]}"
            result = run_json("search", marker, "--no-cache", "--no-history")
            self.assertEqual([r["id"] for r in result["results"]], [doc.id], doc.id)

    def test_status_counts(self):
        run_json("index")
        status = run_json("status")
        self.assertEqual(status["documents"], 120)


class IndexBuilder(unittest.TestCase):
    def test_all_documents_present_for_various_sizes(self):
        for n in (1, 2, 10, 31, 32, 33, 64, 65, 100):
            index = build_index(make_docs(n))
            self.assertEqual(len(index.doc_ids), n, n)
            self.assertEqual(len(index.postings["alpha"]), n, n)

    def test_empty_input(self):
        self.assertEqual(build_index([]).doc_ids, [])


if __name__ == "__main__":
    unittest.main()
