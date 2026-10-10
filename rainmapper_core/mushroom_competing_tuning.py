"""Past-only V6 tuning for historical validation; no installed tuning reuse."""
from collections import Counter, defaultdict


def historical_v6_config(reference, prepared, *, diagnostics=None, compact=False, executor=None):
    import numpy as np
    from rainmapper_core import mushroom_ml_holdout as holdout
    from rainmapper_core import mushroom_ml_raw_weather as raw
    from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth

    partial = reference.estimator_id == 'smooth_partial_pooling_logistic_v1'
    default = {'C': .1, 'deviation_scale': 4.0 if partial else None}
    audit = diagnostics if diagnostics is not None else {}
    audit.update(inner_splits=0, used_inner_splits=0,
                 unsupported_validation_occurrences_by_species={}, default_used=True)
    if reference.estimator_id == 'smooth_species_logistic_v1':
        return default
    X, y = prepared['X'], prepared['y']
    samples = list(prepared['samples'])
    species = [s['metadata']['species_id'] for s in samples]
    configs = [{'C': c, 'deviation_scale': scale}
               for c in (.01, .1, 1.) for scale in ((2., 4., 8.) if partial else (None,))]
    wins = Counter()
    unsupported = Counter()
    for train, valid in holdout._inner_splits(samples, 14):
        audit['inner_splits'] += 1
        order = sorted({species[i] for i in train})
        supported = set(order)
        # A species can first appear after the inner training cutoff. It has
        # no fitted species term yet, so cannot score this inner comparison.
        # Keep all rows in the outer fit and in later temporal comparisons.
        unsupported.update(species[i] for i in valid if species[i] not in supported)
        audit['unsupported_validation_occurrences_by_species'] = dict(sorted(unsupported.items()))
        valid = np.asarray([i for i in valid if species[i] in supported], dtype=int)
        if not len(valid):
            continue
        audit['used_inner_splits'] += 1
        # Unlike the old research selector, preprocessing is also fitted only
        # on the inner training side. The protocol has its own cache identity.
        window = smooth.window_days_from_profile_id(reference.profile_id)
        preprocessor = (smooth.SmoothLagPreprocessor(channels=raw.RAW_CHANNELS, window_days=window)
                        if window is not None else smooth.SmoothLagPreprocessor())
        preprocessor.fit(X[train])
        a, b = preprocessor.transform(X[train]), preprocessor.transform(X[valid])
        scores = defaultdict(dict)
        train_species = [species[i] for i in train]
        valid_species = [species[i] for i in valid]
        species_masks = {sid: np.array([value == sid for value in valid_species]) for sid in order}
        # C changes regularization, not the design. Keep just one scale's
        # matrices live and reuse them across its three C values.
        for scale in ((2., 4., 8.) if partial else (None,)):
            build_design = compact_pooled_design if compact else smooth.pooled_design
            design = build_design(a, train_species, species_order=order, deviation_scale=scale)
            validation = build_design(b, valid_species, species_order=order, deviation_scale=scale)
            options = [(index, config) for index, config in enumerate(configs)
                       if config['deviation_scale'] == scale]
            def score_config(option):
                index, config = option
                model = smooth.fit_logistic(design, y[train], C=config['C'])
                probabilities = model.predict_proba(validation)[:, 1]
                return index, {sid:float(np.mean((y[valid][mask]-probabilities[mask])**2))
                               for sid,mask in species_masks.items() if mask.any()}
            results = executor.map(score_config, options) if executor is not None else map(score_config, options)
            for index, values in results:
                for sid, value in values.items():
                    scores[sid][index] = value
        for values in scores.values():
            best = min(values.values())
            for index, score in values.items():
                if abs(score - best) <= 1e-6:
                    wins[index] += 1
    if not wins:
        return default
    audit['default_used'] = False
    chosen = min(wins, key=lambda i: (-wins[i], configs[i]['C'], -(configs[i]['deviation_scale'] or 0)))
    return configs[chosen]


def compact_pooled_design(values, species, *, species_order, deviation_scale):
    """Same V6 columns without allocating the zero blocks for other species.

    Used only during historical inner tuning. The selected final fit and map
    inference retain the established dense production path.
    """
    import numpy as np
    from scipy.sparse import csr_matrix, hstack
    lookup = {sid:i for i,sid in enumerate(species_order)}
    indices = []
    for sid in species:
        if sid not in lookup:
            raise ValueError(f'unknown hold-out species: {sid}')
        indices.append(lookup[sid])
    indices = np.asarray(indices,dtype=np.int32)
    matrix = csr_matrix(np.asarray(values,dtype=float))
    if len(indices) != matrix.shape[0]:
        raise ValueError('V6 species and matrix row counts differ')
    selected = np.flatnonzero(indices)
    one_hot = csr_matrix((np.ones(len(selected)),(selected,indices[selected]-1)),
                         shape=(len(indices),max(0,len(species_order)-1)))
    blocks = [matrix,one_hot]
    if deviation_scale is not None:
        if deviation_scale <= 0:
            raise ValueError('deviation_scale must be positive')
        offsets = np.repeat(indices*matrix.shape[1],np.diff(matrix.indptr))
        blocks.append(csr_matrix((matrix.data/deviation_scale,matrix.indices+offsets,matrix.indptr),
                                 shape=(matrix.shape[0],matrix.shape[1]*len(species_order))))
    return hstack(blocks,format='csr')
