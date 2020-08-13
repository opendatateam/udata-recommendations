from flask import Blueprint

from udata import theme

from udata.core.dataset.models import Dataset
from udata.frontend import template_hook

blueprint = Blueprint('recommendations', __name__, template_folder='templates')


NB_RECOMMENDATIONS = 2


def has_recommendations(ctx):
    dataset = ctx['dataset']
    return dataset and len(dataset.extras.get('recommendations', []))


@template_hook('dataset.display.after-description', when=has_recommendations)
def dataset_recommendations(ctx):
    reco_ids = []
    recommendations = ctx['dataset'].extras['recommendations']

    # Get at most NB_RECOMMENDATIONS unique recommendations
    # Recommendations are already sorted by score in desc order
    while len(reco_ids) < NB_RECOMMENDATIONS:
        try:
            recommendation = recommendations.pop(0)
            if recommendation['id'] not in reco_ids:
                reco_ids.append(recommendation['id'])
        except IndexError:
            break

    return theme.render(
        'dataset-recommendations.html',
        recommendations=Dataset.objects.filter(id__in=reco_ids)
    )
