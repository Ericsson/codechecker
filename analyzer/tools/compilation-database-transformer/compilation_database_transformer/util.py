import json
import logging

LOG = logging.getLogger('util')


def load_json_or_empty(path, default=None, kind=None):
    """
    Load the contents of the given file as a JSON and return it's value,
    or default if the file can't be loaded.
    """

    ret = default
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
            ret = json.loads(handle.read())

    except IOError as ex:
        LOG.warning("Failed to open %s file: %s",
                    kind if kind else 'json',
                    path)
        LOG.warning(ex)
    except OSError as ex:
        LOG.warning("Failed to open %s file: %s",
                    kind if kind else 'json',
                    path)
        LOG.warning(ex)
    except ValueError as ex:
        LOG.warning("'%s' is not a valid %s file.",
                    kind if kind else 'json',
                    path)
        LOG.warning(ex)
    except TypeError as ex:
        LOG.warning('Failed to process json file: %s', path)
        LOG.warning(ex)

    return ret
