import unittest

import mock
from onapp2vhi.inc.utils import (
    _find_largest_element,
    _find_longest_item,
    exit_status_code_handler,
    generate_random_password,
    parse_matrix,
)


class Test_find_largest_element(unittest.TestCase):
    def test_empty_list(self):
        some_list = []
        self.assertEqual(_find_largest_element(some_list), 0)

    def test_list_with_one_element(self):
        some_list = ["a"]
        self.assertEqual(_find_largest_element(some_list), 1)

    def test_list_with_multiple_elements(self):
        some_list = ["aaa", "bbbbb", "c"]
        self.assertEqual(_find_largest_element(some_list), 5)


class Test_find_longest_item(unittest.TestCase):
    def test_matrix_with_one_row(self):
        matrix = [["aaa", "bbbbb", "c"]]
        self.assertEqual(_find_longest_item(matrix), {0: 3, 1: 5, 2: 1})

    def test_matrix_with_multiple_rows(self):
        matrix = [["123", "1234", "1", "11"], ["123", "123", "11111", "1"]]
        self.assertEqual(_find_longest_item(matrix), {0: 3, 1: 4, 2: 5, 3: 2})

    def test_matrix_with_headers(self):
        matrix = [["123", "1234", "1", "11"], ["123", "123", "11111"]]
        self.assertEqual(_find_longest_item(matrix, True), {0: 4, 1: 3})


class Test_parse_matrix(unittest.TestCase):
    def test_matrix(self):
        headers = ["ID", "IDENTIFIER", "HOSTNAME", "TEMPLATE"]
        matrix = [["190", "jscvwcxdcjckvy", "cloudinit", "null"]]
        expected_output = (
            "+---------------------------------------------+\n"
            "| ID  | IDENTIFIER     | HOSTNAME  | TEMPLATE |\n"
            "+---------------------------------------------+\n"
            "| 190 | jscvwcxdcjckvy | cloudinit | null     | \n"
            "+---------------------------------------------+"
        )

        self.assertEqual(parse_matrix(headers, matrix), expected_output)


class Test_generate_random_password(unittest.TestCase):
    def test_password_with_default_length(self):
        password = generate_random_password()
        self.assertEqual(len(password), 24)

    def test_password_with_custom_length(self):
        password = generate_random_password(length=13)
        self.assertEqual(len(password), 13)


class Test_exit_status_code_handler(unittest.TestCase):
    def test_zero_exit_code(self):
        self.assertTrue(exit_status_code_handler(0))

    @mock.patch("onapp2vhi.inc.utils.logs", autospec=True)
    def test_non_zero_exit_code(self, mock_logs):
        self.assertFalse(exit_status_code_handler(1))
        mock_logs.error.assert_called_once_with(
            "Exit code is 1, stopping further process..."
        )

    @mock.patch("onapp2vhi.inc.utils.logs", autospec=True)
    def test_custom_message(self, mock_logs):
        self.assertFalse(exit_status_code_handler(1, "custom message"))
        mock_logs.error.assert_called_once_with("custom message")


if __name__ == "__main__":
    unittest.main()
