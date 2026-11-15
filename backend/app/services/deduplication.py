import hashlib
import re

STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "or",
    "is", "are", "was", "were", "by", "from", "with", "as", "about", "into"
}

def normalize_title(title: str) -> str:
    """Normalize headline: lowercase, alphanumeric tokens sorted to detect order changes."""
    cleaned = re.sub(r"[^\w\s]", "", title.lower())
    tokens = [w for w in cleaned.split() if w not in STOP_WORDS]
    tokens.sort()
    return " ".join(tokens)

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

class DeduplicationService:
    def __init__(self):
        self.seen_hashes = set()
        self.seen_urls = set()

    def is_duplicate(self, title: str, url: str) -> bool:
        if url in self.seen_urls:
            return True
        norm_title = normalize_title(title)
        title_hash = compute_hash(norm_title)
        if title_hash in self.seen_hashes:
            return True

        self.seen_urls.add(url)
        self.seen_hashes.add(title_hash)
        return False

    def clear(self):
        self.seen_hashes.clear()
        self.seen_urls.clear()

dedup_service = DeduplicationService()
