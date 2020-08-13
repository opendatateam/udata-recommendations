import logging
import json
import importlib

import click
import mongoengine
import requests
import jsonschema

from flask import current_app

from udata.commands import cli, success, exit_with_error, error
from udata.core.dataset.models import Dataset

log = logging.getLogger(__name__)


@cli.group()
def recommendations():
    '''Recommendations related operations'''
    pass


def clean_datasets_recommendations(source):
    log.info(f'Cleaning up dataset recommendations from source {source}')

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

    with importlib.resources.path('udata_recommendations', 'schema.json') as p:
        schema_path = p

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
        error(f"No recommendation found for dataset {dataset['id']}")


@recommendations.command()
@click.argument('source')
def clean(source):
    clean_datasets_recommendations(source)


@recommendations.command()
@click.option('-u', '--url', default=None, help='The URL to get recommendations from')
@click.option('-s', '--source', default=None, help='The source name associated with this URL')
@click.option('--clean', is_flag=True, help='Clean recommendations before fetching recommendations')
def add(url, source, clean):
    use_config = url is None and source is None

    if use_config:
        sources = current_app.config.get('RECOMMENDATIONS_SOURCES')
    else:
        if url is None or source is None:
            exit_with_error('You should specify a source and a URL')

        sources = {source: url}

    for source, url in sources.items():
        if clean:
            clean_datasets_recommendations(source)
        log.info(f'Fetching dataset recommendations from {url}, source {source}')
        try:
            process_source(source, get_recommendations_data(url))
        except jsonschema.exceptions.ValidationError as e:
            exit_with_error(f"Fetched data is invalid {str(e)}")
