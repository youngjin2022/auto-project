import configparser
import os
import time
import requests
import socket
import json
import numpy as np
from nptdms import TdmsFile
from scipy.signal import windows
from scipy.fft import rfft, rfftfreq
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from urllib.parse import urlparse

F_MIN = 5
F_MAX = 3000

# config 파일의 경로들을 읽는 로직
config_path = os.getenv('CONFIG_PATH', 'C:/Users/fmtes/Downloads/pythonnew/config/config.ini')
if not os.path.exists(config_path):
    raise FileNotFoundError(f"Config file not found: {config_path}")
config = configparser.ConfigParser()
config.read(config_path)
directory = config['DEFAULT']['directory']
channel_names_url = config['DEFAULT']['channel_names_url']
channel_data_url = config['DEFAULT']['channel_data_url']

# URL에서 호스트와 포트를 추출
parsed_url = urlparse(channel_data_url)
host = parsed_url.hostname
port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)

# 포트 상태 확인 로직
def is_port_open(host, port):
    """호스트와 포트가 열려 있는지 확인"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.connect((host, port))
            return True
        except (socket.error, socket.timeout):
            return False

# 웹소켓 통신 대기 로직
def wait_for_port(host, port):
    """지정된 호스트와 포트를 기다림"""
    print(f"포트 {port} 대기 중...")
    while not is_port_open(host, port):
        time.sleep(5)
    print(f"포트 {port} 연결 완료.")

# 가장 최근 tdms 파일을 찾는 로직
def get_latest_tdms_file(directory):
    tdms_files = [f for f in os.listdir(directory) if f.endswith('.tdms')]
    latest_file = max(tdms_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return os.path.join(directory, latest_file)

# tdms 파일을 읽는 로직
def read_tdms_file(tdms_file_path):
    return TdmsFile.read(tdms_file_path)

# tdms 파일에서 채널 이름을 추출하는 로직
def extract_channel_names(tdms_file):
    channel_names = []
    for group in tdms_file.groups():
        for channel in group.channels():
            channel_name = channel.properties.get("NI_ChannelName")
            if channel_name:
                channel_names.append(channel_name)
    return channel_names

# 추출한 채널 이름을 channel_names_url 엔드포인트로 보내는 로직
def send_channel_names_to_api(channel_names):
    retries = 5
    for _ in range(retries):
        try:
            response = requests.post(channel_names_url, json=channel_names)
            response.raise_for_status()
            return response
        except requests.ConnectionError:
            time.sleep(5)
    if response.status_code != 200:
        raise Exception(f"채널 이름 전송 실패. 상태 코드: {response.status_code}")

# fft를 계산하는 로직
def get_fft(channel_data, wf_increment):
    sample_length = len(channel_data)
    window = windows.hann(sample_length)
    windowed_data = channel_data * window
    frequency_domain_data = rfft(windowed_data)
    frequencies = rfftfreq(sample_length, d=wf_increment)
    magnitudes = np.abs(frequency_domain_data) / sample_length * 2
    window_correction_factor = np.sum(window) / sample_length
    magnitudes /= window_correction_factor
    frequencies = frequencies.astype(float).round(3)
    magnitudes = magnitudes.astype(float).round(3)
    return frequencies, magnitudes

# overall 값을 계산하는 로직
def get_overall(f_min, f_max, frequency, amplitudes):
    target_frequencies = (frequency >= f_min) & (frequency <= f_max)
    target_amplitudes = amplitudes[target_frequencies]
    overall_value = round(np.sqrt(np.sum(target_amplitudes ** 2)) / np.sqrt(1.4), 4)
    return overall_value

# tdms 파일에서 채널 데이터를 추출하는 로직
def extract_channel_data(tdms_file):
    channel_data = []
    for group in tdms_file.groups():
        for channel in group.channels():
            channel_name = channel.properties.get("NI_ChannelName")
            if channel_name:
                data = channel.read_data()
                sample_rate = 10000
                frequencies, magnitudes = get_fft(data, 1/sample_rate)
                overall_value = get_overall(F_MIN, F_MAX, frequencies, magnitudes)
                timestamp = channel.properties.get("wf_start_time")
                data_dict = {
                    "channel_name": channel_name,
                    "feature": "overall",
                    "value": float(overall_value),
                    "timestamp": timestamp
                }
                channel_data.append(data_dict)
    return channel_data

# 추출한 채널 데이터를 channel_data_url 엔드포인트로 보내는 로직
def send_channel_data_to_api(channel_data):
    headers = {'Content-Type': 'application/json'}
    payload = [json.dumps(data) for data in channel_data]
    response = requests.post(channel_data_url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"채널 데이터 전송 실패. 상태 코드: {response.status_code}")

# 파일 시스템 이벤트 핸들러
class TdmsFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.tdms'):
            time.sleep(1)
            try:
                tdms_file = read_tdms_file(event.src_path)
                channel_data = extract_channel_data(tdms_file)
                send_channel_data_to_api(channel_data)
            except Exception as e:
                print(f"에러 발생: {e}")

# 메인 실행 로직
if __name__ == "__main__":
    try:
        wait_for_port(host, port)
        latest_tdms_file = get_latest_tdms_file(directory)
        tdms_file = read_tdms_file(latest_tdms_file)
        channel_names = extract_channel_names(tdms_file)
        send_channel_names_to_api(channel_names)
        channel_data = extract_channel_data(tdms_file)
        send_channel_data_to_api(channel_data)
        event_handler = TdmsFileHandler()
        observer = Observer()
        observer.schedule(event_handler, directory, recursive=False)
        observer.start()
        try:
            while True:
                if not is_port_open(host, port):
                    print("포트가 닫혔습니다. 다시 연결 시도 중...")
                    wait_for_port(host, port)
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    except Exception as e:
        print(f"메인 로직에서 에러 발생: {e}")
