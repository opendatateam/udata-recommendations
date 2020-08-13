import pytest

from udata.core.dataset.factories import DatasetFactory

MOCK_URL = 'http://reco.net'


@pytest.fixture
def datasets():
    return DatasetFactory.create_batch(3)


@pytest.fixture
def mock_invalid_response():
    return [
        {"foo": "bar"}
    ]


@pytest.fixture
def mock_response(datasets):
    ds1, ds2, ds3 = datasets
    return [
        {
            # Invalid ID, but valid reco: should not crash the command
            "id": "1",
            "recommendations": [
                {
                    "id": str(ds1.id),
                    "score": 50
                }
            ]
        },
        {
            # valid ID and recos,
            # should process two elements w/o crashing
            # should reorder by score and handle reco by ID and slug
            "id": str(ds2.id),
            "recommendations": [
                {
                    "id": str(ds3.id),
                    "score": 1
                },
                {
                    "id": str(ds1.slug),
                    "score": 2
                },
                {
                    "id": "nope",
                    "score": 50
                }
            ]
        },
        {
            # Valid ID but recommended dataset does not exist
            "id": str(ds3.id),
            "recommendations": [
                {
                    "id": "nope",
                    "score": 50
                },
            ]
        }
    ]


@pytest.mark.usefixtures('clean_db')
def test_clean_source(cli):
    # Create 3 datasets that should be left untouched
    DatasetFactory.create_batch(3)

    ds = DatasetFactory(extras={
        'recommendations:sources': ['foo', 'bar'],
        'recommendations': [
            {
                'id': 'id1',
                'source': 'bar',
                'score': 50
            },
            {
                'id': 'id2',
                'source': 'foo',
                'score': 50
            },
        ]
    })
    ds2 = DatasetFactory(extras={
        'recommendations:sources': ['foo'],
        'recommendations': [
            {
                'id': 'id2',
                'source': 'foo',
                'score': 50
            },
        ]
    })

    cli('recommendations clean foo')

    ds.reload()
    assert ds.extras == {
        'recommendations:sources': ['bar'],
        'recommendations': [
            {
                'id': 'id1',
                'source': 'bar',
                'score': 50
            }
        ]
    }
    ds2.reload()
    assert ds2.extras == {}


def test_datasets_recommendations_wrong_args(cli):
    result = cli('recommendations add -u https://example.com', check=False)
    assert result.exit_code == -1
    assert "You should specify a source and a URL" in result.output

    result = cli('recommendations add -s fake_source', check=False)
    assert result.exit_code == -1
    assert "You should specify a source and a URL" in result.output


def test_datasets_recommendations_invalid_data(cli, mock_invalid_response, rmock):
    rmock.get(MOCK_URL, json=mock_invalid_response)

    result = cli(f'recommendations add -s fake_source -u {MOCK_URL}', check=False)

    assert result.exit_code == -1
    assert "Fetched data is invalid" in result.output


def test_datasets_recommendations_valid_data(cli, mock_response, rmock, datasets):
    ds1, ds2, ds3 = datasets
    rmock.get(MOCK_URL, json=mock_response)

    cli(f'recommendations add -s fake_source -u {MOCK_URL}')

    # Correct recommendations have been filled
    ds2.reload()
    assert ds2.extras['recommendations:sources'] == ['fake_source']
    assert ds2.extras['recommendations'] == [
        {'id': str(ds1.id), 'source': 'fake_source', 'score': 2},
        {'id': str(ds3.id), 'source': 'fake_source', 'score': 1},
    ]

    # Invalid recommendations have not been filled
    ds1.reload()
    ds3.reload()
    assert ds1.extras == {}
    assert ds3.extras == {}


def test_datasets_recommendations_valid_data_clean(cli, mock_response, rmock, datasets):
    ds1, ds2, ds3 = datasets
    rmock.get(MOCK_URL, json=mock_response)

    ds1.extras['recommendations:sources'] = ['fake_source']
    ds1.extras['recommendations'] = [
        {'id': str(ds2.id), 'source': 'fake_source', 'score': 100}
    ]
    ds1.save()

    cli(f'recommendations add -s fake_source -u {MOCK_URL} --clean')

    # Correct recommendations have been filled
    ds2.reload()
    assert ds2.extras['recommendations:sources'] == ['fake_source']
    assert ds2.extras['recommendations'] == [
        {'id': str(ds1.id), 'source': 'fake_source', 'score': 2},
        {'id': str(ds3.id), 'source': 'fake_source', 'score': 1},
    ]

    # Previous recommendations have been cleaned
    ds1.reload()
    assert ds1.extras == {}


@pytest.mark.options(RECOMMENDATIONS_SOURCES={'fake_source': MOCK_URL})
def test_datasets_recommendations_invalid_data_in_config(cli, mock_invalid_response, rmock):
    rmock.get(MOCK_URL, json=mock_invalid_response)

    result = cli(f'recommendations add', check=False)

    assert result.exit_code == -1
    assert "Fetched data is invalid" in result.output


@pytest.mark.options(RECOMMENDATIONS_SOURCES={'fake_source': MOCK_URL})
def test_datasets_recommendations_from_config_empty_db(cli, rmock, mock_response, datasets):
    ds1, ds2, ds3 = datasets
    rmock.get(MOCK_URL, json=mock_response)

    result = cli('recommendations add')

    # Correct recommendations have been filled
    ds2.reload()
    assert ds2.extras['recommendations:sources'] == ['fake_source']
    assert ds2.extras['recommendations'] == [
        {'id': str(ds1.id), 'source': 'fake_source', 'score': 2},
        {'id': str(ds3.id), 'source': 'fake_source', 'score': 1},
    ]

    # Invalid recommendations have not been filled
    ds1.reload()
    ds3.reload()
    assert ds1.extras == {}
    assert ds3.extras == {}


@pytest.mark.options(RECOMMENDATIONS_SOURCES={'fake_source': MOCK_URL})
def test_datasets_recommendations_from_config(cli, rmock, mock_response, datasets):
    ds1, ds2, ds3 = datasets
    ds4 = DatasetFactory()
    rmock.get(MOCK_URL, json=mock_response)
    ds2.extras['recommendations:sources'] = ['existing']
    ds2.extras['recommendations'] = [
        {'id': str(ds4.id), 'source': 'existing', 'score': 50},
    ]
    ds2.save()

    cli('recommendations add')

    # Recommendations have been merged, new source has been added
    ds2.reload()
    assert set(ds2.extras['recommendations:sources']) == set(['existing', 'fake_source'])
    assert ds2.extras['recommendations'] == [
        {'id': str(ds4.id), 'source': 'existing', 'score': 50},
        {'id': str(ds1.id), 'source': 'fake_source', 'score': 2},
        {'id': str(ds3.id), 'source': 'fake_source', 'score': 1},
    ]

    # Clean recommendations from the `existing` source
    cli('recommendations clean existing')
    ds2.reload()
    assert ds2.extras['recommendations:sources'] == ['fake_source']
    assert ds2.extras['recommendations'] == [
        {'id': str(ds1.id), 'source': 'fake_source', 'score': 2},
        {'id': str(ds3.id), 'source': 'fake_source', 'score': 1},
    ]


@pytest.mark.options(RECOMMENDATIONS_SOURCES={'fake_source': MOCK_URL})
def test_datasets_recommendations_from_config_clean(cli, mock_response, rmock, datasets):
    ds1, ds2, ds3 = datasets
    rmock.get(MOCK_URL, json=mock_response)

    ds1.extras['recommendations:sources'] = ['fake_source']
    ds1.extras['recommendations'] = [
        {'id': str(ds2.id), 'source': 'fake_source', 'score': 100}
    ]
    ds1.save()

    cli(f'recommendations add --clean')

    # Correct recommendations have been filled
    ds2.reload()
    assert ds2.extras['recommendations:sources'] == ['fake_source']
    assert ds2.extras['recommendations'] == [
        {'id': str(ds1.id), 'source': 'fake_source', 'score': 2},
        {'id': str(ds3.id), 'source': 'fake_source', 'score': 1},
    ]

    # Previous recommendations have been cleaned
    ds1.reload()
    assert ds1.extras == {}
