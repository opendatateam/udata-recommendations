# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from udata.core.dataset.factories import DatasetFactory

pytestmark = pytest.mark.options(plugins=['recommendations'])

MOCK_URL = 'http://reco.net'


@pytest.fixture
def datasets():
    return DatasetFactory.create_batch(3)


@pytest.fixture
def mock_response(datasets):
    ds1, ds2, ds3 = datasets
    return [
        {
            # invalid ID, should not crash the command
            "id": "1",
            "recommendations": [
                {
                    "id": str(ds1.id)
                }
            ]
        },
        {
            # valid ID and recos, expect for third element
            # should process two elements w/o crashing
            "id": str(ds2.id),
            "recommendations": [
                {
                    "id": str(ds1.id)
                },
                {
                    "id": str(ds3.id)
                },
                {
                    "id": "%s1234" % str(ds3.id)
                }
            ]
        },
        {
            # empty recos, should not crash the command
            "id": str(ds3.id),
            "recommendations": []
        },
        {
            # invalid schema, should not crash the command
            "dataset": "xxx"
        }
    ]


@pytest.mark.options(RECOMMENDATIONS_DATASETS_SOURCE_URL=MOCK_URL)
def test_dataset_reco_command(cli, rmock, mock_response, datasets):
    ds1, ds2, ds3 = datasets
    ds4 = DatasetFactory(extras={'recommendations': ['xxx']})
    rmock.get(MOCK_URL, json=mock_response)
    result = cli('recommendations datasets')
    assert 'Dataset recommendations filled for 1 dataset' in result.output
    # previous recommendations have been cleaned up
    ds4.reload()
    assert ds4.extras == {}
    # correct recommendations have been filled
    ds2.reload()
    assert ds2.extras['recommendations'] == [str(ds1.id), str(ds3.id)]
    # wrong recommendations have not been filled
    ds1.reload()
    ds3.reload()
    assert ds1.extras == {}
    assert ds3.extras == {}
