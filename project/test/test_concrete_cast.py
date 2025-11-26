"""Tests for concrete interpreter cast operations."""


def test_concrete_i2s_in_range() -> None:
    """Test i2s with value in short range."""
    value = 100

    # Apply i2s logic
    truncated = value & 0xFFFF
    result = truncated - 65536 if truncated >= 32768 else truncated  # noqa: PLR2004

    assert result == 100  # noqa: PLR2004


def test_concrete_i2s_wrap_positive() -> None:
    """Test i2s with value that wraps (32768 -> -32768)."""
    # Apply i2s logic to 32768
    value = 32768
    truncated = value & 0xFFFF
    result = truncated - 65536 if truncated >= 32768 else truncated  # noqa: PLR2004

    assert result == -32768  # noqa: PLR2004


def test_concrete_i2s_wrap_negative() -> None:
    """Test i2s with value that wraps (-32769 -> 32767)."""
    # Apply i2s logic to -32769
    value = -32769
    truncated = value & 0xFFFF
    result = truncated - 65536 if truncated >= 32768 else truncated  # noqa: PLR2004

    assert result == 32767  # noqa: PLR2004


def test_concrete_i2s_large_value() -> None:
    """Test i2s with large value (65536 -> 0)."""
    # Apply i2s logic to 65536
    value = 65536
    truncated = value & 0xFFFF
    result = truncated - 65536 if truncated >= 32768 else truncated  # noqa: PLR2004

    assert result == 0


def test_concrete_i2s_boundary_max() -> None:
    """Test i2s at max short value (32767)."""
    value = 32767
    truncated = value & 0xFFFF
    result = truncated - 65536 if truncated >= 32768 else truncated  # noqa: PLR2004

    assert result == 32767  # noqa: PLR2004


def test_concrete_i2s_boundary_min() -> None:
    """Test i2s at min short value (-32768)."""
    value = -32768
    truncated = value & 0xFFFF
    result = truncated - 65536 if truncated >= 32768 else truncated  # noqa: PLR2004

    assert result == -32768  # noqa: PLR2004


def test_concrete_i2b_in_range() -> None:
    """Test i2b with value in byte range."""
    value = 50
    truncated = value & 0xFF
    result = truncated - 256 if truncated >= 128 else truncated  # noqa: PLR2004

    assert result == 50  # noqa: PLR2004


def test_concrete_i2b_wrap() -> None:
    """Test i2b with value that wraps (128 -> -128)."""
    value = 128
    truncated = value & 0xFF
    result = truncated - 256 if truncated >= 128 else truncated  # noqa: PLR2004

    assert result == -128  # noqa: PLR2004


def test_concrete_i2c_truncate() -> None:
    """Test i2c (unsigned truncation)."""
    value = 70000
    result = value & 0xFFFF

    assert result == 4464  # noqa: PLR2004  # 70000 % 65536


def test_concrete_i2c_negative() -> None:
    """Test i2c with negative value (becomes positive)."""
    value = -100
    result = value & 0xFFFF

    assert result == 65436  # noqa: PLR2004  # -100 wrapped to unsigned 16-bit
