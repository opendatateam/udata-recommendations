import pytest

from flask import render_template_string, g

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory


def render_hook(dataset):
    return render_template_string(
        '{{ hook("dataset.display.after-description") }}',
        dataset=dataset
    )


@pytest.fixture
def datasets():
    return DatasetFactory.create_batch(3)


@pytest.fixture
def reuses():
    return ReuseFactory.create_batch(1)


@pytest.mark.frontend
@pytest.mark.usefixtures('clean_db')
@pytest.mark.usefixtures('app')
@pytest.mark.options(THEME='gouvfr')
class TestViews:
    def test_view_dataset_no_extras(self):
        assert '' == render_hook(dataset=DatasetFactory(extras={}))

    @pytest.mark.options(RECOMMENDATIONS_NB_RECOMMENDATIONS=2)
    def test_view_dataset_with_recommendations(self, datasets, reuses):
        g.lang_code = 'fr'
        ds1, ds2, ds3 = datasets
        r1 = reuses[0]
        dataset = DatasetFactory(extras={
            'recommendations': [
                {'id': str(ds1.id), 'score': 100, 'source': 'dummy'},
                {'id': str(ds2.id), 'score': 50, 'source': 'dummy'},
                {'id': str(ds3.id), 'score': 25, 'source': 'dummy'},
            ],
            'recommendations-reuses': [
                {'id': str(r1.id), 'score': 100, 'source': 'dummy'},
            ]
        })

        content = render_hook(dataset=dataset)

        assert ds1.full_title in content
        assert ds2.full_title in content
        assert ds3.full_title not in content
        assert r1.title in content

    @pytest.mark.options(RECOMMENDATIONS_NB_RECOMMENDATIONS=2)
    def test_view_dataset_with_recommendations_dedupe(self, datasets, reuses):
        g.lang_code = 'fr'
        ds1, ds2, ds3 = datasets
        r1 = reuses[0]
        dataset = DatasetFactory(extras={
            'recommendations': [
                {'id': str(ds1.id), 'score': 100, 'source': 'dummy'},
                {'id': str(ds1.id), 'score': 50, 'source': 'other'},  # Duplicate ID
                {'id': str(ds3.id), 'score': 25, 'source': 'dummy'},
            ],
            'recommendations-reuses': [
                {'id': str(r1.id), 'score': 100, 'source': 'dummy'},
                {'id': str(r1.id), 'score': 50, 'source': 'other'},
            ]
        })

        content = render_hook(dataset=dataset)

        assert content.count(f'href="{ds1.external_url}"') == 1
        assert content.count(f'href="{r1.external_url}"') == 1
        assert ds1.full_title in content
        assert ds2.full_title not in content
        assert ds3.full_title in content

    @pytest.mark.options(RECOMMENDATIONS_NB_RECOMMENDATIONS=2)
    def test_view_dataset_without_enough_recommendations(self, datasets):
        g.lang_code = 'fr'
        ds1, _, _ = datasets
        dataset = DatasetFactory(extras={
            'recommendations': [
                {'id': str(ds1.id), 'score': 100, 'source': 'dummy'},
            ]
        })

        content = render_hook(dataset=dataset)

        assert ds1.full_title in content

    @pytest.mark.options(RECOMMENDATIONS_NB_RECOMMENDATIONS=4)
    def test_view_dataset_deleted_recommendations(self, datasets):
        ds1, _, _ = datasets

        dataset = DatasetFactory(extras={
            'recommendations': [
                {'id': str(ds1.id), 'score': 100, 'source': 'dummy'},
            ],
            'recommendations-reuses': [
                # we don't care if the id is a dataset or a reuse here
                {'id': str(ds1.id), 'score': 100, 'source': 'dummy'},
            ]
        })

        ds1.delete()

        assert "" == render_hook(dataset=dataset)
