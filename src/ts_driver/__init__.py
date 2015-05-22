""" Time series drivers and utilities """


def parse_landsat_MTL(mtl_file, key):
    """ Returns the value of specified key for a given Landsat MTL file

    Args:
      mtl_file (str): filename of MTL file
      key (str): metadata key to search for

    Returns:
      str or int: returns integer representation of value if possible, else
        as a string

    """
    with open(mtl_file, 'rb') as f:
        for line in f:
            if key in line:
                value = line.strip().split('=')[1].strip()
                try:
                    value = int(value)
                    return value
                except:
                    return value
