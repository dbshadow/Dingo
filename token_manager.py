
import argparse
import json
import secrets
import os
from datetime import datetime

TOKEN_FILE = 'api_tokens.json'
ENV_FILE = '.env'

def load_tokens():
    """從 JSON 檔案載入 tokens。如果檔案不存在，回傳一個空列表。"""
    if not os.path.exists(TOKEN_FILE):
        return []
    try:
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_tokens(tokens):
    """將 tokens 儲存到 JSON 檔案。"""
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, indent=4, ensure_ascii=False)

def generate_api_token(length=40):
    """產生一個指定長度的安全隨機 token。"""
    return secrets.token_urlsafe(length)

def add_token(name):
    """新增一個 API token。"""
    tokens = load_tokens()
    
    # 檢查名稱是否已存在
    if any(token_info.get('name') == name for token_info in tokens):
        print(f"錯誤：名稱 '{name}' 已經存在。")
        return

    new_token = generate_api_token()
    token_data = {
        'name': name,
        'token': new_token,
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }
    
    tokens.append(token_data)
    save_tokens(tokens)
    
    print(f"成功為 '{name}' 新增了 API token：")
    print(f"Token: {new_token}")

def delete_token(token_to_delete):
    """刪除指定的 API token。"""
    tokens = load_tokens()
    
    original_count = len(tokens)
    tokens_after_delete = [t for t in tokens if t.get('token') != token_to_delete]
    
    if len(tokens_after_delete) == original_count:
        print(f"錯誤：找不到指定的 token。")
        return
        
    save_tokens(tokens_after_delete)
    print(f"成功刪除 token。")

def list_tokens():
    """列出所有儲存的 API tokens。"""
    tokens = load_tokens()
    if not tokens:
        print("目前沒有任何 API token。")
        return
        
    print("目前儲存的 API tokens：")
    for token_info in tokens:
        print(
            f"- 名稱: {token_info.get('name', 'N/A')}, "
            f"Token: {token_info.get('token', 'N/A')}, "
            f"建立時間: {token_info.get('created_at', 'N/A')}"
        )

def export_to_env():
    """將所有 API tokens 匯出到 .env 檔案。"""
    tokens = load_tokens()
    if not tokens:
        print("沒有 token 可以匯出。")
        return

    token_list_str = ','.join([t['token'] for t in tokens])
    env_var_line = f'API_TOKENS="{token_list_str}"'
    
    env_content = []
    found = False
    
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('API_TOKENS='):
                    env_content.append(env_var_line + '\n')
                    found = True
                else:
                    env_content.append(line)

    if not found:
        env_content.append(env_var_line + '\n')

    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        f.writelines(env_content)
        
    print(f"成功將 {len(tokens)} 個 token 匯出到 {ENV_FILE}。")


def main():
    """主函式，處理命令列參數。"""
    parser = argparse.ArgumentParser(description="一個用來管理 API token 的工具。" )
    subparsers = parser.add_subparsers(dest='command', required=True, help='可用的指令')

    # 新增 token
    parser_add = subparsers.add_parser('add', help='新增一個 API token。')
    parser_add.add_argument('--name', type=str, required=True, help='與 token 綁定的使用者名稱。')

    # 刪除 token
    parser_delete = subparsers.add_parser('delete', help='刪除一個指定的 API token。')
    parser_delete.add_argument('--token', type=str, required=True, help='要刪除的 token 字串。')

    # 列出 tokens
    subparsers.add_parser('list', help='列出所有已儲存的 API tokens。')

    # 匯出 tokens
    subparsers.add_parser('export', help=f'將所有 tokens 匯出到 {ENV_FILE} 檔案。')

    args = parser.parse_args()

    if args.command == 'add':
        add_token(args.name)
    elif args.command == 'delete':
        delete_token(args.token)
    elif args.command == 'list':
        list_tokens()
    elif args.command == 'export':
        export_to_env()

if __name__ == '__main__':
    main()
