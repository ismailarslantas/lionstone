from lionstone.effects.ffmpeg_fx import CHAR_W, MAX_LINES, fit_lines


def test_short_title_stays_one_line():
    lines, size = fit_lines("Episode 12", 81, 1690)
    assert lines == ["Episode 12"] and size == 81


def test_long_vertical_title_wraps_inside_frame():
    # 9:16 at 1080 wide: the old height-based size was 144 px and ran off both edges
    max_w = 1080 * 0.88
    lines, size = fit_lines("Bunu bilen çok az kişi var", 144, max_w)
    assert 1 < len(lines) <= MAX_LINES
    assert all(len(l) * CHAR_W * size <= max_w for l in lines)
    assert " ".join(lines) == "Bunu bilen çok az kişi var"


def test_too_long_title_shrinks_instead_of_overflowing():
    text = "Bu başlık dikey bir videoya sığmayacak kadar uzun ve çok kelimeden oluşuyor gerçekten"
    lines, size = fit_lines(text, 144, 950)
    assert len(lines) <= MAX_LINES and size < 144
    assert all(len(l) * CHAR_W * size <= 950 for l in lines)
