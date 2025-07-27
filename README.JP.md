# iRacing MCP Server

iRacingのテレメトリデータとゲーム機能にアクセスするためのMCP（Model Context Protocol）サーバーです。

## 概要

このプロジェクトは、iRacingのリアルタイムテレメトリデータ、リーダーボード情報、カメラ制御、ピットコマンド、リプレイ機能などをMCPプロトコルを通じて提供します。AIアシスタントやその他のアプリケーションがiRacingのデータに簡単にアクセスできるようになります。

## 主な機能

### 📊 テレメトリデータ
- リアルタイムテレメトリ値の取得
- 利用可能なテレメトリ変数の一覧取得

### 🏁 レース情報
- リーダーボードの取得（競争的ポジションのみ）
- ドライバー情報、セッション情報、ウィークエンド情報の取得、スプリットタイム情報
- 現在のフラグとエンジン警告の監視

### 📹 カメラ制御
- 利用可能なカメラグループの取得
- カメラの切り替え（車両番号、ポジション、グループ指定）
- 現在のカメラ状態の確認

### 🔧 ピット操作
- ピットサービス状態の確認
- ピットコマンドの実行（燃料補給、タイヤ交換、修理など）
- 安全なピット操作の管理

### 🎬 リプレイ機能
- リプレイの検索とナビゲーション
- セッション間、ラップ間、フレーム間の移動
- インシデントマーカーへのジャンプ

## 必要条件

- Python 3.13以上
- iRacing（実行中である必要があります）
- uv

## 使用方法

### 1. mcp.jsonの設定
```json
{
    "mcpServers": {
        "iracing-mcp-server": {
            "command": "uvx",
            "args":["iracing-mcp-server"]
        }
    }
}
```

## 利用可能なツール

### テレメトリ関連
- `get_telemetry_names()` - 利用可能なテレメトリ変数を取得
- `get_telemetry_values(names)` - 指定したテレメトリ値を取得

### レース情報
- `get_leaderboard()` - リーダーボードを取得
- `get_driver_info()` - ドライバー情報を取得
- `get_session_info()` - セッション情報を取得
- `get_qualify_results_info()` - 予選結果情報を取得
- `get_weekend_info()` - ウィークエンド情報を取得
- `get_split_time_info()` - スプリットタイム情報を取得
- `get_radio_info()` - ラジオ情報を取得
- `get_current_flags()` - 現在のフラグを取得
- `get_current_engine_warnings()` - エンジン警告を取得

### カメラ制御
- `get_camera_info()` - カメラ情報を取得
- `get_current_camera_status()` - 現在のカメラ状態を取得
- `cam_switch(group_number, car_number_raw, position)` - カメラを切り替え

### ピット操作
- `get_current_pit_service_status()` - 現在のピットサービス状態を取得
- `pit_command(commands_and_values)` - ピットコマンドを実行

### リプレイ機能
- `replay_search(search_commands)` - リプレイを検索・ナビゲート

## 開発

### 依存関係
- `mcp[cli]>=1.12.2` - MCPプロトコル実装
- `pyirsdk>=1.3.5` - iRacing SDK Pythonバインディング

### プロジェクト構造
```
iracing-mcp-server/
├── src/iracing_mcp_server/
│   ├── __init__.py          # メインエントリーポイント
│   ├── server.py            # MCPサーバーの実装
│   ├── leaderboard.py       # リーダーボード処理
│   └── prompt.py            # プロンプトテンプレート
├── pyproject.toml           # プロジェクト設定
└── README.md               # このファイル
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 謝辞

- [pyirsdk](https://github.com/kutu/pyirsdk) - iRacing SDKのPythonバインディング
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol 