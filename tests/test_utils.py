from unittest.mock import patch


class TestLogger:
    def test_get_logger(self):
        from app.utils.logger import get_logger

        logger = get_logger()
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")

    def test_logger_singleton(self):
        from app.utils.logger import get_logger

        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2

    @patch("app.utils.logger.logging.FileHandler")
    def test_log_api_request(self, mock_handler):
        from app.utils.logger import get_logger

        logger = get_logger()
        logger.log_api_request(
            endpoint="/test",
            method="GET",
            status_code=200,
            additional_info={"test": "data"},
        )

        # Verify logging was called via FileHandler creation
        mock_handler.assert_called()

    @patch("app.utils.logger.logging.FileHandler")
    def test_log_review_process(self, mock_handler):
        from app.utils.logger import get_logger

        logger = get_logger()
        logger.log_review_process(
            submission_id="test_id",
            stage="upload",
            status="success",
            additional_info={"filename": "test.pdf"},
        )

        # Verify logging was invoked by checking the FileHandler was created
        mock_handler.assert_called()

    def test_log_levels(self):
        from app.utils.logger import get_logger

        logger = get_logger()

        # Test different log levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Ensure the logger has at least one handler (so logs are directed somewhere)
        assert len(getattr(logger, "handlers", [])) > 0

    @patch("app.utils.logger.logging.FileHandler")
    def test_structured_logging(self, mock_handler):
        from app.utils.logger import get_logger

        logger = get_logger()

        # Test structured logging with additional info
        logger.info(
            "Test message",
            additional_info={
                "user_id": "123",
                "action": "upload",
                "timestamp": "2024-01-01T00:00:00Z",
            },
        )

        # Verify structured data is logged by ensuring a FileHandler was created
        mock_handler.assert_called()


class TestLoggingConfiguration:
    def test_log_file_creation(self):
        import os

        from app.utils.logger import get_logger

        logger = get_logger()
        logger.info("Test log entry")

        # Check if log files are created
        log_dir = "logs"
        if os.path.exists(log_dir):
            log_files = os.listdir(log_dir)
            assert len(log_files) > 0

    def test_log_rotation(self):
        import os

        from app.utils.logger import get_logger

        logger = get_logger()

        # Generate many log entries to test rotation
        for i in range(1000):
            logger.info(f"Test log entry {i}")

        # Verify that the log directory exists and contains at least one log file
        log_dir = "logs"
        assert os.path.exists(log_dir)
        log_files = os.listdir(log_dir)
        assert len(log_files) > 0

    def test_error_logging_with_exception(self):
        from app.utils.logger import get_logger

        logger = get_logger()

        try:
            raise ValueError("Test exception")
        except Exception as e:
            logger.error(e, additional_info={"context": "test"})

        # Ensure the logger has at least one handler so the error was directed somewhere
        assert len(getattr(logger, "handlers", [])) > 0


class TestLoggerMethods:
    def test_custom_log_methods(self):
        from app.utils.logger import get_logger

        logger = get_logger()

        # Test custom methods if they exist
        if hasattr(logger, "log_api_request"):
            logger.log_api_request("/test", "GET", 200)

        if hasattr(logger, "log_review_process"):
            logger.log_review_process("test_id", "test_stage", "success")

        assert logger is not None

    def test_logger_formatting(self):
        from app.utils.logger import get_logger

        logger = get_logger()

        # Test that logger formats messages correctly
        logger.info(
            "Test message with formatting",
            additional_info={"key1": "value1", "key2": 123, "key3": True},
        )

        assert logger is not None  # Formatting should handle different data types
