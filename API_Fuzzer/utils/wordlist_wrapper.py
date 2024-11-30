from typing import List
from utils.loaders import load_wordlist
import itertools


class Wordlist:
    """
    Wrapper class for Wordlists of endpoints and payloads
    """

    def __init__(self, source: str | list):
        if isinstance(source, list):
            self.wordlist = source
        else:
            self.wordlist = load_wordlist(source)
        self.index = 0

    def next(self):
        if self.index < len(self.wordlist):
            current_word = self.wordlist[self.index]
            self.index += 1
            return current_word
        else:
            return None

    def reset_index(self):
        self.index = 0

    @staticmethod
    def reset_wordlists(wordlists: list):

        for wordlist in wordlists:
            if isinstance(wordlist, Wordlist):
                wordlist.reset_index()

    def wordlist_length(self):
        return len(self.wordlist)

    @staticmethod
    def create_product_list(lists: list[list]):
        """
        Takes a list of lists and returns the cartesian product of items in a list of tuples
        [[1, 2], ['a', 'b']] ==> [(1, 'a'), (1, 'b'), (2, 'a'), (2, 'b')]
        :param self:
        :param lists:
        :return: list containing the product of all lists (in tuples)
        """
        return list(itertools.product(*lists))

    @staticmethod
    def create_zip_list(lists: list[list]):
        """
        Takes a list of lists and returns the zip combination of items in a list of tuples
        useful for combining credential lists

        The elements from each list are paired together in order.
        [[1, 2], ['a', 'b'], ['x', 'y']] ==> [(1, 'a', 'x'), (2, 'b', 'y')]
        :param self:
        :param lists: list of lists
        :return: list containing the zip of all lists (in tuples)
        """
        return list(zip(*lists))

    @staticmethod
    def create_chain_list(lists: list[list]):
        """
        Takes a list of lists and returns a list of chained values
        :param self:
        :param lists: list of lists
        :return: list containing tha values of all lists (in tuples)
        """
        return list(itertools.chain(*lists))

    @staticmethod
    def merge_into_wordlist(wordlists, merge_type, separator=''):

        # create a list of wordlist lists instead of a list of stings
        wordlists_in_lists = [item.splitlines() for item in wordlists]
        lst = None
        match merge_type:
            case 'chain':
                lst = Wordlist.create_chain_list(wordlists_in_lists)
                print(lst)

            case 'zip':
                lst = Wordlist.create_zip_list(wordlists_in_lists)
                print(lst)

            case 'product':
                lst = Wordlist.create_product_list(wordlists_in_lists)
                print(lst)

        # format result list into a wordlist with chosen separator ( for zip and product)
        result_wordlist = format_wordlist(lst, separator)
        return result_wordlist


def format_wordlist(wordlist: list, separator: str):
    """
    Formats a list into a wordlist with each item on a new line.
    - If the list contains strings, each string will be on a separate line.
    - If the list contains tuples, each tuple's items will be joined by the separator and written on a new line.

    Parameters:
    - wordlist (list): A list of strings or tuples containing strings.
    - separator (str): The separator used to join tuple elements. Default is a comma.

    Returns:
    - str: A formatted wordlist as a string with each item or tuple on a new line.
    """
    if separator == '\\t':
        separator = '\t'

    formatted_lines = []

    for item in wordlist:
        if isinstance(item, tuple):
            # Convert each element in the tuple to a string, then join
            line = separator.join(str(element) for element in item)
        else:
            # Convert non-tuple items to strings directly
            line = str(item)
        formatted_lines.append(line)

        # Join all lines with newlines to create the final wordlist
    return "\n".join(formatted_lines)


def process_wordlists_dict(wordlists):
    proc_wlist = {}
    for key, value in wordlists.items():
        proc_wlist[key] = value['content'].splitlines()

    return proc_wlist


if __name__ == '__main__':
    '''print(Wordlist.create_chain_list([[1, 2], [3, 4], [5, 6], [7, 8]]))
    print(Wordlist.create_zip_list([[1, 2], [3, 4], [5, 6], [7, 8]]))
    print(Wordlist.create_product_list([[1, 2], [3, 4], [5, 6], [7, 8]]))
'''
    print(Wordlist.merge_into_wordlist([[1, 2], [3, 4], [5, 6], [7, 8]], 'chain'))
    print(Wordlist.merge_into_wordlist([[1, 2], [3, 4], [5, 6], [7, 8]], 'zip', ';'))
    print(Wordlist.merge_into_wordlist([[1, 2], [3, 4], [5, 6], [7, 8]], 'product', ';'))
