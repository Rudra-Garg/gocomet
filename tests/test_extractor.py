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
          "invoice_number": {"value": "INV-1", "confidence": 0.9},
          "consignee_name": {"value": "ACME Corporation", "confidence": 0.9},
          "hs_code": {"value": "8471.30", "confidence": 0.9},
          "port_of_loading": {"value": "Shanghai, CN", "confidence": 0.9},
          "port_of_discharge": {"value": "Los Angeles, US", "confidence": 0.9},
          "incoterms": {"value": "FOB", "confidence": 0.9},
          "description_of_goods": {"value": "Laptops", "confidence": 0.9},
          "gross_weight": {"value": "100 KG", "confidence": 0.9}
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
    assert len(prompts) == 2
    assert "Previous output failed with:" in prompts[1]
    assert "Return corrected JSON." in prompts[1]
