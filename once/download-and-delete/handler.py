import os
import io
import json
import logging

import boto3


def is_debug_enabled() -> bool:
    value = os.getenv('DEBUG', 'false').lower()
    if value in ['false', '0']:
        return False
    else:
        return bool(value)


DEBUG = is_debug_enabled()
FILES_BUCKET = os.getenv('FILES_BUCKET')
FILES_TABLE_NAME = os.getenv('FILES_TABLE_NAME')
PRESIGNED_URL_EXPIRES_IN = int(os.getenv('PRESIGNED_URL_EXPIRES_IN', 20))


log = logging.getLogger()
if DEBUG:
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)


def on_event(event, context):
    log.info(f'Event received: {event}')
    log.info(f'Context is: {context}')
    log.debug(f'Debug mode is {DEBUG}')
    log.debug(f'Files bucket is "{FILES_BUCKET}"')

    entry_id = event['pathParameters']['entry_id']
    filename = event['pathParameters']['filename']
    object_name = f'{entry_id}/{filename}'

    dynamodb = boto3.client('dynamodb')
    entry = dynamodb.get_item(
        TableName=FILES_TABLE_NAME,
        Key={'id': {'S': entry_id}})

    log.debug(f'This is the GET_ITEM response: {entry}')

    if 'Item' not in entry or 'deleted' in entry['Item']:
        error_message = f'Entry not found: {object_name}'
        log.info(error_message)
        return {'statusCode': 404, 'body': error_message}

    s3 = boto3.client('s3')
    download_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': FILES_BUCKET, 'Key': object_name},
        ExpiresIn=PRESIGNED_URL_EXPIRES_IN)

    dynamodb.update_item(
        TableName=FILES_TABLE_NAME,
        Key={'id': {'S': entry_id}},
        UpdateExpression='SET deleted = :deleted',
        ExpressionAttributeValues={':deleted': {'BOOL': True}})

    log.info(f'Entry {object_name} marked as deleted')

    return {
        'statusCode': 301,
        'headers': {
            'Location': download_url
        }
    }
