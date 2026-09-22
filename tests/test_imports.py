"""Basic import smoke tests for the StockBallDB package."""


def test_stockballdb_importable() -> None:
    import stockballdb

    assert stockballdb.__version__


def test_core_modules_importable() -> None:
    from stockballdb import check_db, config, db, logging_config
    from stockballdb.app import catalog, status
    from stockballdb.api import create_app

    assert config.ConfigError is not None
    assert callable(db.check_connection)
    assert callable(logging_config.configure_logging)
    assert callable(check_db.main)
    assert callable(catalog.list_instruments)
    assert callable(status.get_status)
    assert callable(create_app)
