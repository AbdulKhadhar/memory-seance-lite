import httpx
import pytest

from app import llm


def test_connection_refused_maps_to_unavailable(mock_http):
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(llm.OllamaUnavailable):
        llm.chat([{"role": "user", "content": "hi"}], "gemma3:1b", "http://localhost:11434", client=mock_http(handler))


def test_missing_model_maps_to_model_not_installed(mock_http):
    def handler(request):
        return httpx.Response(404, json={"error": "model 'gemma3:1b' not found"})

    with pytest.raises(llm.ModelNotInstalled) as err:
        llm.chat([], "gemma3:1b", "http://localhost:11434", client=mock_http(handler))
    assert "ollama pull gemma3:1b" in err.value.message


def test_think_blocks_removed_and_qwen_think_disabled(mock_http):
    seen = {}

    def handler(request):
        seen["body"] = request.read().decode()
        return httpx.Response(200, json={"message": {"content": "<think>hmm</think>Hello."}})

    out = llm.chat([], "qwen3:0.6b", "http://x", client=mock_http(handler))
    assert out == "Hello." and '"think":false' in seen["body"].replace(" ", "")


def test_empty_or_garbled_response(mock_http):
    with pytest.raises(llm.BadLLMOutput):
        llm.chat([], "m", "http://x", client=mock_http(lambda r: httpx.Response(200, json={"message": {"content": " "}})))
    with pytest.raises(llm.BadLLMOutput):
        llm.chat([], "m", "http://x", client=mock_http(lambda r: httpx.Response(200, text="not json")))


def test_list_models_and_is_installed(mock_http):
    handler = lambda r: httpx.Response(200, json={"models": [{"name": "gemma3:1b"}, {"name": "tiny:latest"}]})  # noqa: E731
    names = llm.list_models("http://x", client=mock_http(handler))
    assert llm.is_installed("gemma3:1b", names) and llm.is_installed("tiny", names)
    assert not llm.is_installed("qwen3:0.6b", names)


def test_parse_ofrenda_variants():
    good = '{"remembrance": "r", "remembered": ["a","b","c","d"], "closing": "c"}'
    assert llm.parse_ofrenda(good)["remembered"] == ["a", "b", "c"]
    assert llm.parse_ofrenda("Sure!\n```json\n" + good + "\n```")["closing"] == "c"
    for bad in ["", "no json", '{"remembrance": "r"}', '{"remembrance":"r","remembered":[],"closing":"c"}']:
        with pytest.raises(llm.BadLLMOutput):
            llm.parse_ofrenda(bad)
