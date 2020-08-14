import logging
import json
import importlib

import mongoengine
import requests
import jsonschema
from flask import current_app

from udata.core.dataset.models import Dataset

from udata.tasks import job
from udata.commands import success, error

log = logging.getLogger(__name__)


def recommendations_clean():
    nb_datasets = Dataset.objects.filter(**{
        f'extras__recommendations:sources__exists': True,
    }).update(**{
        'unset__extras__recommendations': True,
        'unset__extras__recommendations:sources': True,
    })
    success(f"Removed recommendations from {nb_datasets} dataset(s)")


def recommendations_clean_source(source):
    datasets = Dataset.objects.filter(**{
        'extras__recommendations:sources__contains': source,
    })

    for dataset in datasets:
        new_sources = set(
            [s for s in dataset.extras['recommendations:sources'] if s != source]
        )

        # Dataset had only this source: delete all recommendations
        if len(new_sources) == 0:
            dataset.update(**{
                'unset__extras__recommendations': True,
                'unset__extras__recommendations:sources': True,
            })
            continue

        # Dataset had at least one other source, keep only other sources
        new_recommendations = [
            r for r in dataset.extras['recommendations']
            if r['source'] != source
        ]
        dataset.extras['recommendations:sources'] = list(new_sources)
        dataset.extras['recommendations'] = new_recommendations
        dataset.save()

    success(f"Cleaned up {len(datasets)} dataset(s)")


def get_recommendations_data(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    with importlib.resources.path('udata_recommendations', 'schema.json') as schema_path:
        with open(schema_path) as f:
            schema = json.load(f)
        jsonschema.validate(instance=data, schema=schema)

    return data


def get_dataset(id_or_slug):
    obj = Dataset.objects(slug=id_or_slug).first()
    return obj or Dataset.objects.get(id=id_or_slug)


def process_source(source, recommendations_data):
    for dataset in recommendations_data:
        process_dataset(source, dataset)


def process_dataset(source, dataset):
    try:
        target_dataset = get_dataset(dataset['id'])
    except (Dataset.DoesNotExist, mongoengine.errors.ValidationError):
        error(f"Dataset {dataset['id']} not found")
        return

    log.info(f"Processing recommendations for dataset {dataset['id']}")
    valid_recos = []
    for reco in dataset['recommendations']:
        try:
            reco_dataset_obj = get_dataset(reco['id'])
            valid_recos.append({
                'id': str(reco_dataset_obj.id),
                'score': reco['score'],
                'source': source,
            })
        except (Dataset.DoesNotExist, mongoengine.errors.ValidationError):
            error(f"Recommended dataset {reco['id']} not found")
            continue
    if len(valid_recos):
        success(f"Found {len(valid_recos)} new recommendations for dataset {dataset['id']}")

        new_sources = set(target_dataset.extras.get('recommendations:sources', []))
        new_sources.add(source)

        merged_recommendations = target_dataset.extras.get('recommendations', [])
        merged_recommendations.extend(valid_recos)
        new_recommendations = sorted(merged_recommendations, key=lambda k: k['score'], reverse=True)

        target_dataset.extras['recommendations:sources'] = list(new_sources)
        target_dataset.extras['recommendations'] = new_recommendations
        target_dataset.save()
    else:
        error(f"No recommendations found for dataset {dataset['id']}")


def recommendations_add(sources, should_clean):
    for source, url in sources.items():
        if should_clean:
            log.info(f'Cleaning up dataset recommendations from source {source}')
            recommendations_clean_source(source)

        log.info(f'Fetching dataset recommendations from {url}, source {source}')
        process_source(source, get_recommendations_data(url))


@job("recommendations-clean-source")
def run_recommendations_clean(self):
    recommendations_clean()


@job("recommendations-clean-source")
def run_recommendations_clean_source(self, source):
    recommendations_clean_source(source)


@job("recommendations-add")
def run_recommendations_add(self, should_clean=True):
    should_clean = should_clean in [True, 'true', 'True']
    sources = current_app.config.get('RECOMMENDATIONS_SOURCES', {})

    recommendations_add(sources, should_clean)
