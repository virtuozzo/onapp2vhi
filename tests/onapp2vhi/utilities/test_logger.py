from unittest import TestCase
from mock import patch, call


class TestLogger(TestCase):

    @patch("os.getpid")
    @patch("os.path.exists")
    @patch("os.path.join")
    def setUp(self, mock_path_join, mock_path_exists, mock_getpid):

        from onapp2vhi.utilities.logs.logger import OnAppVHILogger
        self.logs = OnAppVHILogger()

    @patch("onapp2vhi.utilities.logs.logger.OnAppVHILogger.error")
    @patch("onapp2vhi.utilities.logs.logger.OnAppVHILogger.warn")
    @patch("onapp2vhi.utilities.logs.logger.OnAppVHILogger.debug")
    @patch("onapp2vhi.utilities.logs.logger.OnAppVHILogger.info")
    def test_logger_method(self, mock_info, mock_debug, mock_warn, mock_error):

        for method in [self.logs.info, self.logs.debug]:
            method("test_with_separator", separator=True)
            method("test_without_separator", separator=False)

        for mock_method in [mock_info, mock_debug]:
            mock_method.assert_has_calls([call("test_with_separator", separator=True),
                                          call("test_without_separator", separator=False)])

        for method in [self.logs.warn, self.logs.error]:
            method("test_warn_error")

        for mock_method in [mock_warn, mock_error]:
            mock_method.assert_has_calls([call("test_warn_error")])
