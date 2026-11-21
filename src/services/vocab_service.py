import difflib
import logging
import os
import random
import re
from typing import Dict, List, Optional
from src.services.api_service import api_service

logger = logging.getLogger(__name__)

# Thư mục chứa các file JS từ vựng
VOCAB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "vocab")
FALLBACK_LOCAL_DIR = r"E:\FullStack\JapanLearnApp\js"


class VocabService:
    """Service quét và quản lý kho từ vựng từ các file JS của JapanLearnApp."""

    def __init__(self):
        self.vocabularies: List[Dict[str, str]] = []
        self.load_vocabularies()

    def _get_target_dir(self) -> str:
        """Lấy đường dẫn thư mục từ vựng (ưu tiên data/vocab trong repo)."""
        if os.path.exists(VOCAB_DIR) and len(os.listdir(VOCAB_DIR)) > 0:
            return VOCAB_DIR
        if os.path.exists(FALLBACK_LOCAL_DIR):
            return FALLBACK_LOCAL_DIR
        return VOCAB_DIR

    def load_vocabularies(self) -> None:
        """Quét và phân tích toàn bộ từ vựng từ các file JS."""
        target_dir = self._get_target_dir()
        if not os.path.exists(target_dir):
            logger.warning("Thư mục từ vựng không tồn tại: %s", target_dir)
            return

        loaded_items: List[Dict[str, str]] = []
        pattern = re.compile(
            r'\{\s*(?:["\']?tv["\']?)\s*:\s*["\'](.*?)["\']\s*,\s*(?:["\']?mean["\']?)\s*:\s*["\'](.*?)["\']\s*\}',
            re.DOTALL
        )

        for filename in sorted(os.listdir(target_dir)):
            if not filename.endswith(".js"):
                continue
            if filename in ["api-config.js", "flipCard.js", "gemini-sentence-service.js", "handleShowCards.js"]:
                continue

            file_path = os.path.join(target_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
                    matches = pattern.findall(content)

                    for raw_tv, raw_mean in matches:
                        tv = raw_tv.strip()
                        mean = raw_mean.strip()
                        if not tv or not mean:
                            continue

                        # Xử lý logic tách dấu ' - ' khi nhiều từ bị ghép chung 1 dòng
                        if " - " in tv:
                            tv_parts = [t.strip() for t in tv.split(" - ") if t.strip()]
                            mean_parts = [m.strip() for m in mean.split(" - ") if m.strip()]

                            if len(tv_parts) == len(mean_parts):
                                for t, m in zip(tv_parts, mean_parts):
                                    loaded_items.append({
                                        "word": t,
                                        "meaning": m,
                                        "source": filename
                                    })
                            else:
                                for t in tv_parts:
                                    clean_mean = mean.replace(" - ", " / ")
                                    loaded_items.append({
                                        "word": t,
                                        "meaning": clean_mean,
                                        "source": filename
                                    })
                        else:
                            loaded_items.append({
                                "word": tv,
                                "meaning": mean,
                                "source": filename
                            })

            except Exception as e:
                logger.error("Lỗi khi đọc file %s: %s", filename, e)

        self.vocabularies = loaded_items
        logger.info("Đã nạp thành công %d từ vựng từ thư mục %s", len(self.vocabularies), target_dir)

    def get_random_vocabs(self, count: int = 3) -> List[Dict[str, str]]:
        """Lấy ngẫu nhiên k từ vựng từ kho."""
        if not self.vocabularies:
            self.load_vocabularies()
        if not self.vocabularies:
            return []
        k = min(count, len(self.vocabularies))
        return random.sample(self.vocabularies, k)

    async def generate_vocab_message(self, count: int = 3, time_label: str = "HÀNG NGÀY") -> str:
        """Tạo tin nhắn từ vựng hoàn chỉnh kèm ví dụ thông minh từ AI."""
        vocabs = self.get_random_vocabs(count)
        if not vocabs:
            return "⚠️ Chưa tìm thấy dữ liệu từ vựng trong hệ thống."

        base_text = f"📖 **[TỪ VỰNG HỌC TẬP - {time_label}]**\n\n"
        for i, v in enumerate(vocabs, 1):
            base_text += f"**{i}. {v['word']}**\n   • Nghĩa: _{v['meaning']}_\n   • Nguồn: `{v['source']}`\n\n"

        prompt = (
            "Dưới đây là 3 từ vựng người dùng cần học hôm nay:\n"
            + "\n".join([f"- {v['word']}: {v['meaning']}" for v in vocabs])
            + "\n\nHãy tạo 1 câu ví dụ ngắn gọn, thực tế và dễ nhớ cho TỪNG từ trên (kèm dịch tiếng Việt). "
            "Trình bày thật gọn gàng, súc tích bằng Markdown."
        )

        try:
            ai_example = await api_service.process_prompt(prompt, user_id=0)
            if ai_example and not ai_example.startswith("⚠️"):
                return f"{base_text}💡 **Câu ví dụ áp dụng:**\n{ai_example}"
        except Exception as e:
            logger.warning("Không thể tạo câu ví dụ bằng AI: %s", e)

        return base_text

    def _score_match(self, term: str, word: str, meaning: str) -> int:
        """Tính điểm phù hợp giữa từ khóa tìm kiếm và từ vựng (thông minh, không phụ thuộc thứ tự từ hay từ chen giữa)."""
        t = term.lower().strip()
        w = word.lower().strip()
        m = meaning.lower().strip()
        full = f"{w} {m}"

        # 1. Khớp chính xác tuyệt đối (100đ)
        if t == w or t == m:
            return 100

        # 2. Khớp cụm từ con trực tiếp (85đ)
        if t in w:
            return 85
        if t in m:
            return 80

        # 3. Khớp tất cả các từ đơn (Token-Set Matching) - VD: 'phanh xe' khớp 'phanh thắng xe' (70đ)
        tokens = [tok for tok in t.split() if tok]
        if len(tokens) > 1 and all(tok in full for tok in tokens):
            return 70

        # 4. Fuzzy Matching (Chống gõ sai chính tả nhẹ - typo tolerance)
        r_w = difflib.SequenceMatcher(None, t, w).ratio()
        r_m = difflib.SequenceMatcher(None, t, m).ratio()
        best_ratio = max(r_w, r_m)
        if best_ratio >= 0.72:
            return int(best_ratio * 60)

        # 5. Khớp ít nhất 1 từ đơn có ý nghĩa (nếu cụm dài)
        if len(tokens) > 1:
            matched_count = sum(1 for tok in tokens if len(tok) >= 2 and tok in full)
            if matched_count >= len(tokens) * 0.6:
                return 40

        return 0

    def search_vocabs(self, query: str, limit: int = 15) -> List[Dict[str, str]]:
        """Tra cứu thông minh: Hỗ trợ tìm từ chen giữa (VD: 'phanh xe' khớp 'phanh thắng xe'),
        chống gõ sai (typo tolerance), tìm ngược thứ tự từ, và tra cứu nhiều từ ngăn cách bằng dấu phẩy."""
        if not self.vocabularies:
            self.load_vocabularies()

        if not query or not query.strip():
            return []

        # Tách các từ cần tìm (ngăn cách bằng dấu phẩy hoặc chấm phẩy)
        raw_terms = [t.strip() for t in query.replace(";", ",").split(",") if t.strip()]
        if not raw_terms:
            return []

        scored_results: List[tuple[int, Dict[str, str]]] = []
        seen = set()

        for term in raw_terms:
            for item in self.vocabularies:
                unique_key = (item["word"], item["meaning"])
                if unique_key in seen:
                    continue

                score = self._score_match(term, item["word"], item["meaning"])
                if score > 0:
                    scored_results.append((score, item))
                    seen.add(unique_key)

        # Sắp xếp theo độ khớp cao nhất lên trước
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [it[1] for it in scored_results[:limit]]


vocab_service = VocabService()
