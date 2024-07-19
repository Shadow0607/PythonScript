import configparser
import os
import platform

def load_NAS_config(config_file='config.ini'):
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    
    # 使用 UTF-8 編碼讀取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        config.read_file(f)

    system = platform.system()

    return {
        'NAS_IP': config['NAS']['IP'],
        'NAS_USERNAME': config['NAS']['USERNAME'],
        'NAS_PASSWORD': config['NAS']['PASSWORD'],
        'NAS_PATH': config['NAS']['PATH'],
        'MIN_SIZE': int(config['DOWNLOAD']['MIN_SIZE']),
        'MAX_SIZE': int(config['DOWNLOAD']['MAX_SIZE']),
        'WINDOWS_PATH' :config['NAS']['WINDOWS_PATH'],
        'ROOT_FOLDER':config['NAS']['ROOT_FOLDER']
    }

def load_log_config(config_file='config.ini'):
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    # 使用 UTF-8 編碼讀取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        config.read_file(f)
    system = platform.system()
    return {
        'LOG_FOLDER': config['LOG']['LINUX_FOLDER'] if system == 'Linux' else config['LOG']['WINDOWS_FOLDER'],
    }

def load_NAS_ROOT_config(config_file='config.ini'):
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    # 使用 UTF-8 編碼讀取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        config.read_file(f)
    system = platform.system()
    return config['NAS']['PATH'] if system == 'Linux' else config['NAS']['WINDOWS_PATH']

def load_MYSQL_config(config_file='config.ini'):
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    
    # 使用 UTF-8 編碼讀取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        config.read_file(f)

    return {
        'DB_HOST': config['MYSQL']['DB_HOST'],
        'DB_USER': config['MYSQL']['DB_USER'],
        'DB_PASSWORD': config['MYSQL']['DB_PASSWORD'],
        'DB_NAME': config['MYSQL']['DB_NAME'],
        'DB_PORT': int(config['MYSQL']['DB_PORT'])
    }