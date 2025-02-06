import asyncio
import os
import logging
import subprocess
import boto3
import pytz

from datetime import datetime, timedelta
from botocore.exceptions import NoCredentialsError

from bot.utils.common.config import (
    DB_PASSWORD,
    DB_USER,
    DB_HOST,
    DB_PORT,
    DB_NAME,
    S3_ACCESS_KEY,
    S3_SECRET_KEY,
    S3_REGION,
    S3_URL
)
from bot.utils.resources.exceptions.exceptions import (
    ExceptionError,
    ValueProcessingError,
    MissingKeyError,
    AttributeAccessError
)

logger = logging.getLogger(__name__)
os.environ['PGPASSWORD'] = DB_PASSWORD


async def create_backup():
    """
    Главная функция создания бэкапа базы данных.
    Выполняется подключение к базе данных, создается резервная копия,
    файл сохраняется локально, затем загружается в S3.
    """
    logger.info('Начинаем процесс создания резервной копии базы данных')

    # Путь к временной папке для хранения бэкапов.
    # Если работаете в Linux/MacOS, можно использовать '/tmp/fasolka_backups'.
    # Если на Windows — укажите соответствующий путь.
    local_backup_dir = '/tmp/fasolka_backups'
    os.makedirs(local_backup_dir, exist_ok=True)

    # Имя файла бэкапа и файла для логирования ошибок
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(local_backup_dir, f'backup_{timestamp}.sql')
    error_log_file = os.path.join(local_backup_dir, 'pg_dump_error.log')

    # Формируем команду для pg_dump в виде списка аргументов
    command = [
        'pg_dump',
        '-U', DB_USER,
        '-h', DB_HOST,
        '-p', str(DB_PORT),
        DB_NAME
    ]

    logger.info(f'Выполняется команда: {" ".join(command)}')
    # Выполняем команду pg_dump в отдельном потоке, чтобы не блокировать event loop.
    result = await asyncio.to_thread(
        subprocess.run,
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Сохраняем стандартный вывод (stdout) в файл бэкапа
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(result.stdout)

    # Сохраняем ошибки (stderr) в файл логов
    with open(error_log_file, 'w', encoding='utf-8') as f:
        f.write(result.stderr)

    logger.info(f"pg_dump завершился с кодом: {result.returncode}")

    if os.path.exists(backup_file):
        if os.path.getsize(backup_file) > 0:
            upload_backup_to_s3(backup_file, f'fasolka_backups/{os.path.basename(backup_file)}')
            os.remove(backup_file)
        else:
            logger.error(f'Файл бэкапа не создан или пуст: {backup_file}')
        logger.info('Временный файл бэкапа успешно удален')
        delete_old_backups_from_s3()
    else:
        logger.error(f'Не удалось создать файл бэкапа: {backup_file}')

def upload_backup_to_s3(local_file: str, s3_file: str):
    """
    Функция загрузки бэкапа в хранилище.
    Происходит подключение к хранилищу, загрузка файла бэкапа по пути '/tmp/fasolka_backups'
    """

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
    """
    Функция удаления бэкапов из хранилища, которым больше 5 дней
    """

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

    except AttributeError as attr_error:
        raise AttributeAccessError(str(attr_error))
    except KeyError as key_error:
        raise MissingKeyError(str(key_error))
    except ValueError as value_error:
        raise ValueProcessingError(str(value_error))
    except Exception as e:
        raise ExceptionError(str(e))


