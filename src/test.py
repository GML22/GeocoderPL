""" Testing module """

import unittest
import numpy as np

from pyproj.crs import CRSError
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
        # 2180 -> 4326
        self.exp_val1 = np.sum([[53.123], [23.444]])
        self.exp_val2 = np.sum([[55.237, 54.672, 53.641, 52.9654, 51.3245, 50.23423, 49.3121, 48.4567, 47.8884],
                                [17.529, 18.4342, 19.44343, 20.5621, 21.345, 22.456, 23.784, 24.2356, 25.2343]])

        # 4326 -> 2180
        self.exp_val3 = np.sum([[317508.550767323, 715578.2249603242], [457519.78638788883, 587702.5546628572]])
        self.exp_val4 = np.sum([[558742.5008345963, 124709.68333851639, 376329.7954527512],
                                [567192.4343290976, 851622.1212396007, 648197.1329118722]])

    def test_ct1_2180_4326(self) -> None:
        """
        Test if geographical coordinates are correctly transformed from EPSG 2180 to EPSG 4326

        :return: The method does not return any values
        """

        # Testowe koordynaty
        test_coords1 = [[593415.2087601414], [797217.5666588726]]

        # noinspection PyTypeChecker
        test_sum1 = np.sum(convert_coords(test_coords1, '2180', '4326'))
        err_msg1 = 'Geographical coordinates have not been correctly transformed from EPSG 2180 to EPSG 4326!'

        # noinspection PyTypeChecker
        self.assertAlmostEqual(test_sum1, self.exp_val1, 5, err_msg1)

    def test_ct2_2180_4326(self) -> None:
        """
        Test if geographical coordinates are correctly transformed from EPSG 2180 to EPSG 4326

        :return: The method does not return any values
        """

        # Testowe koordynaty
        test_coords2 = np.array([[820314.203902998, 406489.40976672835], [756621.6274770098, 463523.10154106584],
                                 [641887.8945878604, 529307.2601361987], [567801.785547792, 604881.8547989755],
                                 [386815.23930981196, 663338.2845925333], [268718.6531911418, 746374.9381498817],
                                 [171526.4596051555, 847557.4199094148], [78700.16428317595, 886911.7302979091],
                                 [21140.37740988657, 965819.9583809776]])

        # noinspection PyTypeChecker
        test_sum2 = np.sum(convert_coords(test_coords2, '2180', '4326'))
        err_msg2 = 'Geographical coordinates have not been correctly transformed from EPSG 2180 to EPSG 4326!'

        # noinspection PyTypeChecker
        self.assertAlmostEqual(test_sum2, self.exp_val2, 5, err_msg2)

    def test_ct3_2180_4326(self) -> None:
        """
        Test if geographical coordinates are correctly transformed from EPSG 4326 to EPSG 2180

        :return: The method does not return any values
        """

        # Testowe koordynaty
        test_coords3 = [[50.723, 53.111], [18.398, 22.222]]

        # noinspection PyTypeChecker
        test_sum3 = np.sum(convert_coords(test_coords3, '4326', '2180'))
        err_msg3 = 'Geographical coordinates have not been correctly transformed from EPSG 4326 to EPSG 2180!'

        # noinspection PyTypeChecker
        self.assertAlmostEqual(test_sum3, self.exp_val3, 5, err_msg3)

    def test_ct4_4326_2180(self) -> None:
        """
        Test if geographical coordinates are correctly transformed from EPSG 4326 to EPSG 2180

        :return: The method does not return any values
        """

        # Testowe koordynaty
        test_coords4 = np.array([[52.89, 19.999], [48.89, 23.799], [51.2344, 21.12344]])

        # noinspection PyTypeChecker
        test_sum4 = np.sum(convert_coords(test_coords4, '4326', '2180'))
        err_msg4 = 'Geographical coordinates have not been correctly transformed from EPSG 4326 to EPSG 2180!'

        # noinspection PyTypeChecker
        self.assertAlmostEqual(test_sum4, self.exp_val4, 5, err_msg4)

    def test_ct5_dict(self) -> None:
        """
        Test if function "convert_coords" returns TypeError for dict object

        :return: The method does not return any values
        """

        # Testowe koordynaty
        test_coords5 = dict({52.4556: 21.1234, 47.567: 25.7865})
        self.assertRaises(TypeError, convert_coords, test_coords5, '4326', '2180')

    def test_ct6_tuple(self) -> None:
        """
        Test if function "convert_coords" returns TypeError for tuple object

        :return: The method does not return any values
        """

        # Testowe koordynaty
        test_coords6 = ((52.4556, 47.567), (21.1234, 25.7865))
        self.assertRaises(TypeError, convert_coords, test_coords6, '4326', '2180')

    def test_ct7_str(self) -> None:
        """
        Test if function "convert_coords" returns TypeError for string coordinate

        :return: The method does not return any values
        """

        # Testowe koordynaty
        test_coords7 = [[52.4556, "47.567"], [21.1234, 25.7865]]
        self.assertRaises(TypeError, convert_coords, test_coords7, '4326', '2180')

    def test_ct8_empty(self) -> None:
        """
        Test if function "convert_coords" returns IndexError for empty list

        :return: The method does not return any values
        """

        # Testowe koordynaty
        test_coords8 = []
        self.assertRaises(IndexError, convert_coords, test_coords8, '4326', '2180')

    def test_ct9_epsg(self) -> None:
        """
        Test if function "convert_coords" returns CRSError error for wrong EPSG number

        :return: The method does not return any values
        """

        # Testowe koordynaty
        test_coords9 = np.array([[52.89, 19.999], [48.89, 23.799], [51.2344, 21.12344]])
        self.assertRaises(CRSError, convert_coords, test_coords9, '-32323232', '2180')

    def test_ct10_epsg_fmt(self) -> None:
        """
        Test if function "convert_coords" returns TypeError for wrong EPSG number format

        :return: The method does not return any values
        """

        # Testowe koordynaty
        test_coords10 = np.array([[52.89, 19.999], [48.89, 23.799], [51.2344, 21.12344]])
        self.assertRaises(TypeError, convert_coords, test_coords10, '4326', 2180)


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
