from flask import Blueprint, current_app

from udata.core.dataset.models import Dataset
from udata.core.reuse.models import Reuse
from udata.i18n import get_current_locale, default_lang
from udata_front import theme
from udata_front.frontend import template_hook


blueprint = Blueprint('recommendations', __name__, template_folder='templates')


def has_dataset_recommendations(ctx):
    dataset = ctx['dataset']
    return dataset and dataset.extras.get('recommendations', [])


def has_reuse_recommendations(ctx):
    dataset = ctx['dataset']
    return dataset and dataset.extras.get('recommendations-reuses', [])


def has_external_recommendations(ctx):
    dataset = ctx['dataset']
    return dataset and (
        dataset.extras.get('recommendations-externals', [])
    )


@template_hook('dataset.display.after-files', when=has_dataset_recommendations)
def dataset_recommendations(ctx):
    recommendations = ctx['dataset'].extras.get('recommendations', [])

    # Get at most n unique recommendations
    # Recommendations are already sorted by score in desc order
    limit = current_app.config.get('RECOMMENDATIONS_NB_RECOMMENDATIONS')
    # Ordered sets don't exist but dicts are ordered since 3.7
    # https://stackoverflow.com/a/51145737
    reco_ids = list({r['id']: 0 for r in recommendations})[:limit]

    return theme.render(
        'dataset-recommendations.html',
        reco_datasets=Dataset.objects.filter(id__in=reco_ids),
    )


@template_hook('dataset.display.after-reuses', when=has_reuse_recommendations)
def dataset_reuse_recommendations(ctx):
    recommendations_reuses = ctx['dataset'].extras.get('recommendations-reuses', [])

    # Get at most n unique recommendations
    # Recommendations are already sorted by score in desc order
    limit = current_app.config.get('RECOMMENDATIONS_NB_RECOMMENDATIONS')
    # Ordered sets don't exist but dicts are ordered since 3.7
    # https://stackoverflow.com/a/51145737
    reco_reuses_ids = list({r['id']: 0 for r in recommendations_reuses})[:limit]

    return theme.render(
        'dataset-recommendations-reuses.html',
        reco_reuses=Reuse.objects.filter(id__in=reco_reuses_ids),
    )


@template_hook('dataset.display.after-description', when=has_external_recommendations)
def dataset_external_recommendations(ctx):
    recommendations_externals = ctx['dataset'].extras.get('recommendations-externals', [])
    reco_external = list(recommendations_externals)[0]
    messages = reco_external["messages"] if "messages" in reco_external else None
    current_language = get_current_locale().language
    messages = messages[current_language] if current_language in messages else messages[default_lang]

    return theme.render(
        'dataset-recommendations-externals.html',
        messages=messages,
        id=reco_external["id"]
    )
