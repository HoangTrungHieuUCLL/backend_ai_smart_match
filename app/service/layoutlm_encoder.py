from __future__ import annotations

from typing import List

import math

try:
    from transformers import AutoTokenizer, AutoModel
    import torch
except Exception:  # optional dependency — caller should handle fallback
    AutoTokenizer = None
    AutoModel = None
    torch = None


class LayoutLMEncoder:
    """Simple encoder wrapper that uses a LayoutLM-family model to produce embeddings.

    If transformers or torch are unavailable, callers should fall back to other
    encoders. This class does a mean pooling over token hidden states to return
    a single vector per input string.
    """

    def __init__(self, model_name: str = "microsoft/layoutlm-base-uncased"):
        if AutoTokenizer is None or AutoModel is None or torch is None:
            raise RuntimeError("transformers or torch not available")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def encode(self, texts: List[str], normalize_embeddings: bool = True) -> List[List[float]]:
        # Basic text-only encoding path (keeps previous behavior)
        inputs = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
        input_ids = inputs["input_ids"].to(self.device)
        attention_mask = inputs["attention_mask"].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            last_hidden = outputs.last_hidden_state

        # mean pooling
        mask = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
        summed = torch.sum(last_hidden * mask, 1)
        counts = torch.clamp(mask.sum(1), min=1e-9)
        mean_pooled = summed / counts

        vectors = mean_pooled.cpu().numpy().tolist()

        if normalize_embeddings:
            normalized = []
            for v in vectors:
                norm = math.sqrt(sum(x * x for x in v)) or 1.0
                normalized.append([x / norm for x in v])
            return normalized

        return vectors

    def encode_with_boxes(self, words_list: List[List[str]], boxes_list: List[List[List[int]]], normalize_embeddings: bool = True) -> List[List[float]]:
        """Encode inputs where `words_list` is a list of pages/documents, each a list of words,
        and `boxes_list` is the corresponding list of word-level bboxes (ints [x0,y0,x1,y1] normalized 0..1000).

        This method tokenizes using `is_split_into_words=True`, maps word-level boxes to token-level boxes,
        and passes `bbox` into the model (required by LayoutLM). Returns mean-pooled embeddings per document.
        """
        # Tokenize with word-splitting so we can map tokens back to words
        encoding = self.tokenizer(words_list, is_split_into_words=True, return_tensors="pt", padding=True, truncation=True)
        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        # Build token-level bbox tensor matching encoding
        token_bboxes = []
        for i in range(input_ids.size(0)):
            word_ids = encoding.word_ids(batch_index=i)
            bboxes_for_example: list[list[int]] = []
            for wid in word_ids:
                if wid is None:
                    # special tokens
                    bboxes_for_example.append([0, 0, 0, 0])
                else:
                    # word-level bbox
                    bboxes_for_example.append(boxes_list[i][wid])

            token_bboxes.append(bboxes_for_example)

        # convert to tensor
        bbox_tensor = torch.tensor(token_bboxes, dtype=torch.long).to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask, bbox=bbox_tensor)
            last_hidden = outputs.last_hidden_state

        mask = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
        summed = torch.sum(last_hidden * mask, 1)
        counts = torch.clamp(mask.sum(1), min=1e-9)
        mean_pooled = summed / counts

        vectors = mean_pooled.cpu().numpy().tolist()

        if normalize_embeddings:
            normalized = []
            for v in vectors:
                norm = math.sqrt(sum(x * x for x in v)) or 1.0
                normalized.append([x / norm for x in v])
            return normalized

        return vectors
