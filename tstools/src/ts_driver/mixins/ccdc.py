""" Mixins for reading CCDC results
"""


def CCDCResultsReader(object):
    """ Methods and attributes for reading and working with CCDC results
    """
    config = ['_results_folder']
    config_names = ['CCDC results folder']

    def fetch_results(self, path, row, col):
        """ Return CCDC results as NumPy structured array

        Args:
            path (str): path to results
            row (int): retrieve results for row
            col (int): retrieve results for column

        Returns:
            np.ndarray: structured array containing results

        """
        pass
