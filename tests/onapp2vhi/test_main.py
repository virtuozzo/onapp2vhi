import unittest
from click import BadParameter
from onapp2vhi.main import validate_flavor

class ClickCallbackTest(unittest.TestCase):
    
    def test_validate_flavor_wrong_ram_format(self):
        mock_flavor = "flavor_test_1"

        with self.assertRaises(BadParameter):
            validate_flavor("", "", mock_flavor)

    def test_validate_flavor_wrong_cpus_format(self):
        mock_flavor = "flavor_1_test"

        with self.assertRaises(BadParameter):
            validate_flavor("", "", mock_flavor)

    def test_validate_flavor_wrong_format(self):
        mock_flavor = "flavortest"

        with self.assertRaises(BadParameter):
            validate_flavor("", "", mock_flavor)

    def test_validate_flavor_success(self):
        mock_flavor = "flavor_4_1024"
        mock_result = {
            "name": "flavor",
            "vcpus": "4",
            "ram": "1024"
        }

        result = validate_flavor("", "", mock_flavor)
        self.assertEqual(mock_result, result)
