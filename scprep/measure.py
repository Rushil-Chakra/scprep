import numpy as np
import warnings
import numbers

from . import utils, select
from ._lazyload import statsmodels


def library_size(data):
    """Measure the library size of each cell.

    Parameters
    ----------
    data : array-like, shape=[n_samples, n_features]
        Input data

    Returns
    -------
    library_size : list-like, shape=[n_samples]
        Sum over all genes for each cell
    """
    library_size = utils.matrix_sum(data, axis=1)
    return library_size


def gene_set_expression(data, genes=None, library_size_normalize=False,
                        starts_with=None, ends_with=None,
                        exact_word=None, regex=None):
    """Measure the expression of a set of genes in each cell.

    Parameters
    ----------
    data : array-like, shape=[n_samples, n_features]
        Input data
    genes : list-like, shape<=[n_features], optional (default: None)
        Integer column indices or string gene names included in gene set
    library_size_normalize : bool, optional (default: False)
        Divide gene set expression by library size
    starts_with : str or None, optional (default: None)
        If not None, select genes that start with this prefix
    ends_with : str or None, optional (default: None)
        If not None, select genes that end with this suffix
    exact_word : str, list-like or None, optional (default: None)
        If not None, select genes that contain this exact word.
    regex : str or None, optional (default: None)
        If not None, select genes that match this regular expression

    Returns
    -------
    gene_set_expression : list-like, shape=[n_samples]
        Sum over genes for each cell
    """
    if library_size_normalize:
        from .normalize import library_size_normalize
        data = library_size_normalize(data)
    gene_data = select.select_cols(data, idx=genes, starts_with=starts_with,
                                   ends_with=ends_with,
                                   exact_word=exact_word, regex=regex)
    if len(gene_data.shape) > 1:
        gene_set_expression = library_size(gene_data)
    else:
        gene_set_expression = gene_data
    return gene_set_expression


@utils._with_pkg(pkg="statsmodels")
def variable_genes(data, span=0.7, interpolate=0.2):
    """Measure the variability of each gene in a dataset

    Variability is computed as the deviation from a loess fit of the mean-variance curve

    Parameters
    ----------
    data : array-like, shape=[n_samples, n_features]
        Input data
    span : float, optional (default: 0.7)
        Fraction of genes to use when computing the loess estimate at each point
    interpolate : float, optional (default: 0.2)
        Multiple of the standard deviation of variances at which to interpolate
        linearly in order to reduce computation time.

    Returns
    -------
    variability : list-like, shape=[n_samples]
        Variability for each gene
    """
    data = utils.to_array_or_spmatrix(data)
    data_mean = utils.toarray(np.mean(data, axis=0)).flatten()
    data_std = utils.matrix_std(data, axis=0) ** 2
    delta = np.std(data_std) * interpolate
    lowess = statsmodels.nonparametric.smoothers_lowess.lowess(
        data_std, data_mean,
        delta=delta, frac=span, return_sorted=False)
    return data_std - lowess


def _get_percentile_cutoff(data, cutoff=None, percentile=None, required=False):
    """Get a cutoff for a dataset

    Parameters
    ----------
    data : array-like
    cutoff : float or None, optional (default: None)
        Absolute cutoff value. Only one of cutoff and percentile may be given
    percentile : float or None, optional (default: None)
        Percentile cutoff value between 0 and 100.
        Only one of cutoff and percentile may be given
    required : bool, optional (default: False)
        If True, one of cutoff and percentile must be given.

    Returns
    -------
    cutoff : float or None
        Absolute cutoff value. Can only be None if required is False and
        cutoff and percentile are both None.
    """
    if percentile is not None:
        if cutoff is not None:
            raise ValueError(
                "Only one of `cutoff` and `percentile` should be given."
                "Got cutoff={}, percentile={}".format(cutoff, percentile))
        if not isinstance(percentile, numbers.Number):
            return [_get_percentile_cutoff(data, percentile=p)
                    for p in percentile]
        if percentile < 1:
            warnings.warn(
                "`percentile` expects values between 0 and 100."
                "Got {}. Did you mean {}?".format(percentile,
                                                  percentile * 100),
                UserWarning)
        cutoff = np.percentile(np.array(data).reshape(-1), percentile)
    elif cutoff is None and required:
        raise ValueError(
            "One of either `cutoff` or `percentile` must be given.")
    return cutoff
