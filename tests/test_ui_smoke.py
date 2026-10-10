from src.app import main


def test_ui_entrypoint() -> None:
    assert callable(main)
