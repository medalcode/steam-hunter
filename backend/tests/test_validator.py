from app.validator import validate_key_format, validate_gift_link


class TestValidateKeyFormat:
    def test_valid_steam_key(self):
        result = validate_key_format("ABCDE-12345-FGHIJ")
        assert result["valid"] is True

    def test_valid_steam_key_lowercase(self):
        result = validate_key_format("abcde-12345-fghij")
        assert result["valid"] is True

    def test_invalid_key_too_short(self):
        result = validate_key_format("ABC-123-DEF")
        assert result["valid"] is False
        assert "invalid format" in result["reason"].lower()

    def test_invalid_key_empty(self):
        result = validate_key_format("")
        assert result["valid"] is False

    def test_invalid_key_with_spaces(self):
        result = validate_key_format("ABCDE 12345 FGHIJ")
        assert result["valid"] is False

    def test_invalid_key_special_chars(self):
        result = validate_key_format("ABCDE-12$45-FGHIJ")
        assert result["valid"] is False

    def test_valid_gift_link(self):
        result = validate_gift_link("https://store.steampowered.com/gift/abc123/")
        assert result["valid"] is True

    def test_invalid_gift_link(self):
        result = validate_gift_link("https://example.com/not-a-gift")
        assert result["valid"] is False

    def test_empty_gift_link(self):
        result = validate_gift_link("")
        assert result["valid"] is False
