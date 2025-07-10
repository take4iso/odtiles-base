import random
import string

LETTERS = string.ascii_letters
#LETTERS = string.ascii_letters + string.digits + string.punctuation

SETTING_FILE = '/opt/odtiles/odtiles/settings.py'

def get_random_string(num):

    random_letters = random.choices(LETTERS, k=num)
    random_string = ''.join(random_letters)
    return random_string

# テキストファイルの読み込み
def read_text_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return None

# テキストファイルの書き込み
def write_text_file(file_path, content):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Content written to {file_path}")
    except Exception as e:
        print(f"Error writing to file {file_path}: {e}")


settingfile = read_text_file(SETTING_FILE)
if settingfile is None:
    print("Error reading the settings file.")


elif settingfile.find("UPLOAD_API_TOKEN = \'\'") != -1:
    ix = settingfile.find("UPLOAD_API_TOKEN = \'\'")
    # UPLOAD_API_TOKENが設定ファイルに存在しない場合、ランダムな文字列を生成して追加
    upload_api_token = get_random_string(50)
    setupfile = settingfile.replace("UPLOAD_API_TOKEN = \'\'", f"UPLOAD_API_TOKEN = \'{upload_api_token}\'")
    write_text_file(SETTING_FILE, setupfile)

    print()
    print('***********************************************************')
    print(f'token = {upload_api_token}')
    print('***********************************************************')
    print()