""" Testing module """

import unittest
import numpy as np

from geocoderpl.super_permutations import SuperPerms
from geocoderpl.geo_utilities import convert_coords

# TODO: Klasa testów dla funkcji "points_in_shape" pochodzącej z modułu "geo_utilities"
# TODO: Klasa testów dla funkcji "reduce_coordinates_precision" pochodzącej z modułu "geo_utilities"


class TestCoordsTransforms(unittest.TestCase):
    """ Class performing tests of coordinates transformations between different coordinates systems """

    def setUp(self) -> None:
        """
        Method containing expected values for coordinates transformations

        :return: The method does not return any values
        """

        # Oczekiwane wartości przetransformowanych współrzędnych wyliczone przy pomocy strony https://epsg.io/
        # 2169 -> 4326
        self.exp_val1 = np.sum([[53.123], [23.444]])
        self.exp_val2 = np.sum([[50.723], [18.398]])

    def test_ct1_2180_4326(self) -> None:
        """
        Test if geographical coordinates are correctly transformed from EPSG 2180 to EPSG 4326

        :return: The method does not return any values
        """

        # noinspection PyTypeChecker
        test_sum1 = np.sum(convert_coords([[593415.2087601414], [797217.5666588726]], '2180', '4326'))
        err_msg1 = 'Geographical coordinates have not been correctly transformed from EPSG 2180 to EPSG 4326!'

        # noinspection PyTypeChecker
        self.assertAlmostEqual(test_sum1, self.exp_val1, 5, err_msg1)

    def test_ct2_2180_4326(self) -> None:
        """
        Test if geographical coordinates are correctly transformed from EPSG 2180 to EPSG 4326

        :return: The method does not return any values
        """

        # noinspection PyTypeChecker
        test_sum2 = np.sum(convert_coords([[317508.550767323], [457519.78638788883]], '2180', '4326'))
        err_msg2 = 'Geographical coordinates have not been correctly transformed from EPSG 2180 to EPSG 4326!'

        # noinspection PyTypeChecker
        self.assertAlmostEqual(test_sum2, self.exp_val2, 5, err_msg2)


class TestSuperPermutations(unittest.TestCase):
    """ Class performing tests of superpermutation class """

    def setUp(self) -> None:
        """
        Method containing expected values of superpermutations with n = 1, 2, 3, 4, 5

        :return: The method does not return any values
        """

        self.exp_val1 = [0]
        self.exp_val2 = [0, 1, 0]
        self.exp_val3 = [0, 1, 2, 0, 1, 0, 2, 1, 0]
        self.exp_val4 = [0, 1, 2, 3, 0, 1, 2, 0, 3, 1, 2, 0, 1, 3, 2, 0, 1, 0, 2, 3, 1, 0, 2, 1, 3, 0, 2, 1, 0, 3, 2, 1,
                         0]
        self.exp_val5 = [0, 1, 2, 3, 4, 0, 1, 2, 3, 0, 4, 1, 2, 3, 0, 1, 4, 2, 3, 0, 1, 2, 4, 3, 0, 1, 2, 0, 3, 4, 1, 2,
                         0, 3, 1, 4, 2, 0, 3, 1, 2, 4, 0, 3, 1, 2, 0, 4, 3, 1, 2, 0, 1, 3, 4, 2, 0, 1, 3, 2, 4, 0, 1, 3,
                         2, 0, 4, 1, 3, 2, 0, 1, 4, 3, 2, 0, 1, 0, 2, 3, 4, 1, 0, 2, 3, 1, 4, 0, 2, 3, 1, 0, 4, 2, 3, 1,
                         0, 2, 4, 3, 1, 0, 2, 1, 3, 4, 0, 2, 1, 3, 0, 4, 2, 1, 3, 0, 2, 4, 1, 3, 0, 2, 1, 4, 3, 0, 2, 1,
                         0, 3, 4, 2, 1, 0, 3, 2, 4, 1, 0, 3, 2, 1, 4, 0, 3, 2, 1, 0, 4, 3, 2, 1, 0]

    def test_superperm_0(self) -> None:
        """
        Test if superpermutation class returns None for string length "n" = 0

        :return: The method does not return any values
        """

        self.assertIs(SuperPerms(0).fin_super_perm_ids, None, 'The superpermutation for n = 0 is not None!')

    def test_superperm_1(self) -> None:
        """
        Test of superpermutation class for string length "n" = 1

        :return: The method does not return any values
        """

        self.assertEqual(SuperPerms(1).fin_super_perm_ids, self.exp_val1, 'The superpermutation for n = 1 is wrong!')

    def test_superperm_2(self) -> None:
        """
        Test of superpermutation class for string length "n" = 2

        :return: The method does not return any values
        """

        self.assertEqual(SuperPerms(2).fin_super_perm_ids, self.exp_val2, 'The superpermutation for n = 2 is wrong!')

    def test_superperm_3(self) -> None:
        """
        Test of superpermutation class for string length "n" = 3

        :return: The method does not return any values
        """

        self.assertEqual(SuperPerms(3).fin_super_perm_ids, self.exp_val3, 'The superpermutation for n = 3 is wrong!')

    def test_superperm_4(self) -> None:
        """
        Test of superpermutation class for string length "n" = 4

        :return: The method does not return any values
        """

        self.assertEqual(SuperPerms(4).fin_super_perm_ids, self.exp_val4, 'The superpermutation for n = 4 is wrong!')

    def test_superperm_5(self) -> None:
        """
        Test of superpermutation class for string length "n" = 5

        :return: The method does not return any values
        """

        self.assertEqual(SuperPerms(5).fin_super_perm_ids, self.exp_val5, 'The superpermutation for n = 5 is wrong!')

    def test_superperm_6(self) -> None:
        """
        Test if superpermutation class returns None for string length "n" = 6

        :return: The method does not return any values
        """

        self.assertIs(SuperPerms(6).fin_super_perm_ids, None, 'The superpermutation for n = 6 is not None!')

    def test_superperm_789(self) -> None:
        """
        Test if superpermutation class returns None for string length "n" = 789

        :return: The method does not return any values
        """

        self.assertIs(SuperPerms(789).fin_super_perm_ids, None, 'The superpermutation for n = 789 is not None!')

    def test_superperm_N967(self) -> None:
        """
        Test if superpermutation class returns None for string length "n" = -967

        :return: The method does not return any values
        """

        self.assertIs(SuperPerms(-967).fin_super_perm_ids, None, 'The superpermutation for n = -967 is not None!')

    def test_superperm_str(self) -> None:
        """
        Test if superpermutation class raises TypeError for string length "n" of type str (convertible to int)

        :return: The method does not return any values
        """

        self.assertRaises(TypeError, SuperPerms, "3")

    def test_superperm_str2(self) -> None:
        """
        Test if superpermutation class raises TypeError for string length "n" of type str (not convertible to int)

        :return: The method does not return any values
        """

        self.assertRaises(TypeError, SuperPerms, "Test")

    def test_superperm_float(self) -> None:
        """
        Test if superpermutation class raises TypeError for string length "n" of type float

        :return: The method does not return any values
        """

        self.assertRaises(TypeError, SuperPerms, 3.14159265359)

    def test_superperm_list(self) -> None:
        """
        Test if superpermutation class raises TypeError for string length "n" of type list

        :return: The method does not return any values
        """

        self.assertRaises(TypeError, SuperPerms, [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
