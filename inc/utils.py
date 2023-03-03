import string
import random
from inc.logger import logs


def _find_largest_element(some_list):
    """
    Find the bigger string element in the list
    :param some_list:
    :return:
    """
    fn = lambda item: len(str(item))
    max_item = max(some_list or [''], key=fn)
    return len(max_item)


def _find_longest_item(matrix, headers=False):
    """
    Find the longest item in a column of matrix and assign it to ID of the column
    :param matrix:
        [['test, 'test'],
         ['test, 'test'],
         ['test, 'test']]
    :param headers: bool
    :return: {0: 10, 1: 5, 2: 25, . . .}
    """
    long_dict = {}
    if headers:
        for i, element in enumerate(matrix):
            long_dict[i] = len(element)
        return long_dict

    row_length = len(matrix[0])
    total = []
    for i in range(0, row_length):
        matrix_factory = []
        for row in matrix:
            matrix_factory.append(row[i])
        total.append(matrix_factory)
    if len(total) == 1:
        for i, tot in enumerate(total[0]):
            long_dict[i] = _find_largest_element(tot)
        return long_dict

    for i, tot in enumerate(total):
        long_dict[i] = _find_largest_element(tot)
    return long_dict


def parse_matrix(headers, matrix):
    """
    This function is working with lists in list (matrix) and show it like table in console, ex.:
        ------------------------------------------|
        |ID  |IDENTIFIER     |HOSTNAME  |TEMPLATE |
        ------------------------------------------|
        |190 |jscvwcxdcjckvy |cloudinit |null     |
        ------------------------------------------|
    :param headers: headers of table
    :param matrix: lists in list
        [['test, 'test'],
         ['test, 'test'],
         ['test, 'test']]
    :return:
    """
    schema_matrix = _find_longest_item(matrix)
    schema_header = _find_longest_item(headers, headers=True)
    for k_m, v_m in schema_matrix.items():
        for k_h, v_h in schema_header.items():
            if k_m != k_h:
                continue

            elif v_m >= v_h:
                schema_matrix[k_m] = v_m
                continue

            schema_matrix[k_m] = v_h
    white_space = " "
    header_str = ""
    table_str = ""
    sum_list = []
    sum_list.append(len(headers)*2)
    for i, head in enumerate(headers):
        sum_list.append(schema_matrix[i])
        _number = schema_matrix[i] - len(str(head)) + 1
        _prepare_str = f"| {head.upper()}{white_space*_number}"
        header_str += _prepare_str
    for i, row in enumerate(matrix):
        row_str = ""
        for j, elem in enumerate(row):
            _number = schema_matrix[j] - len(str(elem)) + 1
            row_str += f"| {elem}{white_space*_number}"
        if i+2 > len(matrix):
            table_str += row_str + "| "
            continue

        table_str += row_str + "|\n"
    separator = f'+{("-" * len(header_str))[:-1]}+'
    final_string = f"{separator}\n{header_str}|\n{separator}\n{table_str}\n{separator}"
    return final_string


def generate_random_password(length=24):
    """
    Generates password for User with default length 24
    :param length: (int) the length of password
    :return: (str) password
    """
    characters = list(string.ascii_letters + string.digits + "!@#$%^&*()")
    random.shuffle(characters)
    password = [random.choice(characters) for _ in range(length)]
    random.shuffle(password)
    return "".join(password)


def exit_status_code_handler(exit_code: int, message: str = ''):
    """
    Handler will catch errors and return False, otherwise True
    :param exit_code: 0 or 1
    :param message: "Message"
    :return:
    """
    if exit_code:
        if not message:
            message = f'Exit code is {exit_code}, stopping further process...'
        logs.error(message)
        return False

    return True
