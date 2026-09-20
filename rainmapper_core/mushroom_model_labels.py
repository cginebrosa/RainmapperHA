"""Compact model provenance shared by the predictor and point map."""

ESTIMATOR_SHORT_NAMES = {'logistic_regression_reduced_v1': 'LR',
 'random_forest_restricted_v1': 'RF',
 'extra_trees_restricted_v1': 'ET',
 'hist_gradient_boosting_restricted_v1': 'HGB',
 'knn_distance_v1': 'KNN',
 'knn_distance_beta_smoothed_v2': 'KNN',
 'rbf_svm_calibrated_v1': 'SVM',
 'elastic_net_logistic_raw365_v1': 'Elastic Net',
 'sparse_group_logistic_raw365_v1': 'Sparse Group',
 'smooth_species_logistic_v1': 'Smooth Species',
 'smooth_shared_logistic_v1': 'Smooth Shared',
 'smooth_partial_pooling_logistic_v1': 'Smooth Partial'}

VERSION_SHORT_NAMES = {
    "altitude_v2": "V2",
    "biology_v3": "V3",
    "biology_v4": "V4",
    "biology_v5_raw_weather_discovery": "V5",
    "biology_v6_smooth_hierarchical": "V6",
    "biology_v5_windowed_raw_weather": "V5w",
    "biology_v6_windowed_smooth_hierarchical": "V6w",
}


def model_source_label(reference):
    """Only identify a concrete model; missing provenance stays missing."""
    estimator = reference.get("estimator_id")
    version = reference.get("version_id")
    if not estimator or not version:
        return ""
    return f"{ESTIMATOR_SHORT_NAMES.get(estimator, estimator)}–{VERSION_SHORT_NAMES.get(version, version)}"


MODEL_INPUT_PREFIXES = {
    "smi": ("soil_water_",),
    "balance": ("climatic_water_balance_", "climatic_balance_mm"),
    "et": ("eto0_",),
    "rain": ("rain_", "days_since_rain", "days_since_significant_rain", "dry_spell_"),
    "temperature": ("temp_",),
    "humidity": ("humidity_",),
    "season": ("target_day_", "day_of_year_"),
}


def model_input_details(reference, columns, catalog_profiles):
    """Describe actual artifact inputs, without inferring usage from its version.

    These are declared inputs, not an attribution of their fitted importance.
    Only a tiny summary escapes the already loaded artifact.
    """
    if not columns or reference.get('estimator_id') not in ESTIMATOR_SHORT_NAMES:
        return None
    profile = next((p for p in catalog_profiles
                    if p['version_id'] == reference.get('version_id')
                    and p['profile_id'] == reference.get('profile_id')), {})
    window = (profile.get('input_requirements') or {}).get('predictive_window_days')
    return {
        'estimator': reference.get('estimator_id', ''),
        'inputs': [key for key, prefixes in MODEL_INPUT_PREFIXES.items()
                   if any(column.startswith(prefixes) for column in columns)],
        'window_days': window if type(window) is int and 0 < window <= 365 else None,
    }


def valid_model_details(details):
    return details is None or (
        isinstance(details, dict) and set(details) == {'estimator', 'inputs', 'window_days'}
        and isinstance(details['estimator'], str) and details['estimator'] in ESTIMATOR_SHORT_NAMES
        and isinstance(details['inputs'], list)
        and all(isinstance(key, str) and key in MODEL_INPUT_PREFIXES for key in details['inputs'])
        and len(details['inputs']) == len(set(details['inputs']))
        and (details['window_days'] is None or
             type(details['window_days']) is int and 0 < details['window_days'] <= 365))
