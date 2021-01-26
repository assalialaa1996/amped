# -*- coding: utf-8 -*-
"""
    GitHub Events
    -------------

    Module used for fielding GitHub repository events

"""

import functools
import hashlib
import hmac
import json
import os
from enum import Enum
from typing import Dict

import boto3
from aws_lambda_powertools.logging import Logger

logger = Logger(service='amped')

REGION = os.environ.get('REGION', 'us-east-1')
SSM_CLIENT = boto3.client('ssm', region_name=REGION)


class GithubEvent(Enum):
    """GitHub event type"""

    tag = 'tag'
    pull_request = 'pull_request'
    repository = 'repository'


@functools.lru_cache()
def _get_github_secret() -> str:
    """
    Get GitHub webhook secret from SSM parameter store.

    :returns: GitHub webhook secret value
    """
    response = SSM_CLIENT.get_parameter(Name='/amped/github_webhook_secret', WithDecryption=True)
    return response['Parameter']['Value']


def _valid_signature(headers: Dict, body: str) -> bool:
    """
    Determine if request signature is valid.

    :param headers: dictionary of request headers
    :param body: json encoded webhook body
    :returns: boolean depicting validity of signature received
    """
    signing_secret = _get_github_secret().encode('utf-8')
    signature_parts = headers.get('x-hub-signature', '').split('=', 1)
    computed_signature = hmac.new(signing_secret, body.encode('utf-8'), digestmod=hashlib.sha1).hexdigest()

    if not hmac.compare_digest(signature_parts[1], computed_signature):
        logger.error({'operation': '_valid_signature', 'expected': signature_parts[1], 'computed': computed_signature})
        return False
    return True


@logger.inject_lambda_context
def receive(event: Dict, _c: Dict) -> Dict:
    """
    Lambda function to receive and validate GitHub webhooks before passing along payload.

    :param event: lambda expected event object
    :param _c: lambda expected context object (unused)
    :returns: none
    """
    logger.info(event)
    raw = event.get('body')
    body = json.loads(raw)
    logger.info(body)

    if _valid_signature(headers=event.get('headers'), body=raw):
        return {
            'statusCode': 202,
            'body': 'GitHub signature verified',
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True,
            },
        }
    err = {
        'statusCode': 403,
        'body': 'GitHub signature does not match',
        'headers': {'Content-Type': 'application/json; charset=utf-8'},
    }
    logger.error(err)
    return err


if __name__ == '__main__':
    receive({}, {})
