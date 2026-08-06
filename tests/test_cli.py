from mr_rao.cli import main


def test_cli_health():
    assert main(["health"]) == 0


def test_cli_convert_txt(tmp_path):
    src = tmp_path / "x.txt"
    src.write_text("cli test content", encoding="utf-8")
    out = tmp_path / "out.md"
    code = main(
        [
            "convert",
            str(src),
            "-o",
            str(out),
            "--no-privacy",
            "--no-tables",
        ]
    )
    assert code == 0
    assert out.exists()
    assert "cli test content" in out.read_text(encoding="utf-8")
