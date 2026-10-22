import pytest

from psd2ui.naming import export_name, inside


@pytest.mark.parametrize("raw,expected", [
    ("img_中文 空格", "中文 空格"), ("a/b\\c:d*e?f", "a_b_c_d_e_f"),
    ("../../outside", "____outside"), ("CON", "_CON"), ("NUL.txt", "_NUL.txt"),
    ("x[IMG]", "x[IMG]"), ("legal.name", "legal.name"),
    ("hbox_列表", "列表"), ("vhox_列表", "列表"), ("panel_窗口", "窗口"),
    ("iconimg_", "iconimg_"), ("IMG_icon", "icon"),
    ("btn_settings_close", "settings_close"), ("unknown_a_b", "unknown_a_b"),
    ("$btn_old", "$btn_old"), ("$img_old", "$img_old"),
    ("txt_player_name", "player_name"), ("text_player_name", "player_name"),
    ("input_account", "account"), ("pnl_settings", "settings"),
    ("[img]icon", "[img]icon"), ("[image]icon", "[image]icon"),
    ("Button", "Button"), ("txt", "txt"), ("Icon", "Icon"), ("hbox", "hbox"),
    ("ico_player_avatar", "player_avatar"), ("ico", "ico"),
    ("bar_health", "health"), ("bar", "bar"),
])
def test_safe_names(raw, expected):
    assert export_name(raw) == expected


@pytest.mark.parametrize("raw", ["", "img_", "hbox_", "vhox_", "panel_", " . "])
def test_empty_names_fail(raw):
    with pytest.raises(ValueError):
        export_name(raw)


def test_path_escape_and_symlink(tmp_path):
    with pytest.raises(ValueError):
        inside(tmp_path, "../bad")
    (tmp_path / "link").symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        inside(tmp_path, "link/bad.png")

