# Web Backend (FastAPI)

## 役割
ユーザーからの閲覧リクエストを受け、DBからデータを取得してHTMLを生成・返却します。

## 主要ファイル
- `main.py`: FastAPIアプリのエントリポイント
- `src/api/routes.py`: ルーティング定義

## 特徴
- **HTMX採用**: 最小限のJavaScriptで動的なUIを実現（SPAのような体験を軽量に）
- **Jinja2テンプレート**: サーバーサイドでHTML生成
- **将来的拡張**: いいね機能、検索API、推薦API

**具体例**: `/` エンドポイントでは `get_latest_explanations()` で最新20件を取得し、`index.html` に渡します。