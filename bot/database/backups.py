import os
import logging
import boto3
from datetime import datetime, timedelta

import pytz
from botocore.exceptions import NoCredentialsError

from bot.config import DB_PASSWORD, DB_USER, DB_HOST, DB_PORT, DB_NAME, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION, S3_URL

logger = logging.getLogger(__name__)
os.environ['PGPASSWORD'] = DB_PASSWORD


async def create_backup():
    logger.info('Начинаем процесс создания резервной копии базы данных')

    # Путь к временной папке для хранения бэкапов
    local_backup_dir = '/tmp/fasolka_backups'
    os.makedirs(local_backup_dir, exist_ok=True)

    # Имя файла бэкапа
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'{local_backup_dir}/backup_{timestamp}.sql'

    # Выполняем бэкап базы данных
    os.system(
        f'pg_dump -U {DB_USER} '
        f'-h {DB_HOST} '
        f'-p {DB_PORT} '
        f'{DB_NAME} > {backup_file}'
    )

    if os.path.exists(backup_file):
        # Загружаем бэкап в S3
        upload_backup_to_s3(backup_file, f'fasolka_backups/{os.path.basename(backup_file)}')
        # Удаляем временный файл после загрузки
        os.remove(backup_file)
        logger.info('Временный файл бэкапа успешно удален')
        # Удаляем старые бэкапы из S3
        delete_old_backups_from_s3()
    else:
        logger.error(f'Не удалось создать файл бэкапа: {backup_file}')


def upload_backup_to_s3(local_file, s3_file):
    logger.info(f'Загрузка файла {local_file} в S3: {s3_file}')
    s3 = boto3.client(
        's3',
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        endpoint_url=S3_URL
    )
    try:
        s3.upload_file(local_file, 'c462de58-1673afa0-028c-4482-9d49-87f46960a44f', s3_file)
        logger.info(f'Файл {local_file} успешно загружен в S3: {s3_file}')
    except FileNotFoundError:
        logger.error(f'Файл {local_file} не найден')
    except NoCredentialsError:
        logger.error('Учетные данные для доступа к S3 недоступны')
    except Exception as e:
        logger.error(f'Ошибка при загрузке в S3: {str(e)}')


def delete_old_backups_from_s3():
    logger.info('Удаление старых бэкапов из S3')
    s3 = boto3.client(
        's3',
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        endpoint_url=S3_URL
    )
    cutoff_date = datetime.now(pytz.utc) - timedelta(days=5)

    try:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket='c462de58-1673afa0-028c-4482-9d49-87f46960a44f', Prefix='fasolka_backups/'):
            if 'Contents' in page:
                for obj in page['Contents']:
                    obj_date = obj['LastModified']

                    # Убедитесь, что obj_date имеет временную зону
                    if obj_date.tzinfo is None:
                        obj_date = pytz.utc.localize(obj_date)

                    if obj_date < cutoff_date:
                        s3.delete_object(Bucket='c462de58-1673afa0-028c-4482-9d49-87f46960a44f', Key=obj['Key'])
                        logger.info(f'Удален старый бэкап: {obj["Key"]}')
    except Exception as e:
        logger.error(f'Ошибка при удалении старых бэкапов: {str(e)}')