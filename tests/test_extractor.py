from backend.agents import extractor
from backend.config import Settings


def test_extractor_retry_feeds_validation_errors(monkeypatch) -> None:
    prompts = []

    def fake_generate(settings, prompt, **kwargs):
        prompts.append(prompt)
        if len(prompts) == 1:
            return '{"run_id": "run-1"}'
        return """
        {
          "run_id": "run-1",
          "invoice_number": {"value": "INV-1", "confidence": 0.9, "source_snippet": "Invoice No: INV-1"},
          "consignee_name": {"value": "ACME Corporation", "confidence": 0.9, "source_snippet": "Consignee: ACME Corporation"},
          "hs_code": {"value": "8471.30", "confidence": 0.9, "source_snippet": "HS Code 8471.30"},
          "port_of_loading": {"value": "Shanghai, CN", "confidence": 0.9, "source_snippet": "Port of Loading: Shanghai, CN"},
          "port_of_discharge": {"value": "Los Angeles, US", "confidence": 0.9, "source_snippet": "Port of Discharge: Los Angeles, US"},
          "incoterms": {"value": "FOB", "confidence": 0.9, "source_snippet": "Incoterms: FOB"},
          "description_of_goods": {"value": "Laptops", "confidence": 0.9, "source_snippet": "Goods: Laptops"},
          "gross_weight": {"value": "100 KG", "confidence": 0.9, "source_snippet": "Gross Weight: 100 KG"}
        }
        """

    monkeypatch.setattr(extractor, "generate_text_with_document", fake_generate)

    result = extractor.extract_document(
        run_id="run-1",
        document_bytes=b"pdf",
        document_mime="application/pdf",
        settings=Settings(gemini_api_key="test"),
    )

    assert result.run_id == "run-1"
    assert result.invoice_number.source_snippet == "Invoice No: INV-1"
    assert "source_snippet" in prompts[0]
    assert "120 characters or fewer" in prompts[0]
    assert "copied exactly from the document" in prompts[0]
    assert len(prompts) == 2
    assert "Previous output failed with:" in prompts[1]
    assert "Return corrected JSON." in prompts[1]
