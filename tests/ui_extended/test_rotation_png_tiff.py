import pytest


def test_rotate_png_and_tiff_paths(tmp_path):
    from plookingII.core.image_rotation import ImageRotationProcessor
    try:
        from PIL import Image
    except Exception:
        pytest.skip("PIL not available")

    # Create PNG
    png = tmp_path / "a.png"
    Image.new("RGB", (5, 7)).save(str(png), format="PNG")
    # Create TIFF
    tiff = tmp_path / "b.tiff"
    Image.new("RGB", (10, 10)).save(str(tiff), format="TIFF")

    p = ImageRotationProcessor()
    assert p.rotate_image(str(png), "clockwise") is True
    assert p.rotate_image(str(tiff), "counterclockwise") is True
