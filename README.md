# Pokéscreader Database

[Pokéscreader for SV](https://takosavi.net/pokescreader-sv/)
で使用するポケモンデータベースを出力する.

データ出典元は [PokéAPI](https://pokeapi.co/) です.
内部で PokéAPI を逐次呼び出しています.
[PokéAPI の Fair Use Policy](https://pokeapi.co/docs/v2#fairuse)
に従って実行してください.

## Format

ヘッダなしのタブ区切りテキストで, 次の項目が出力されます.

1. 全国図鑑番号
2. フォルムの通し番号 (0 始まり)
3. ポケモン名
4. フォルム名 (明記すべきものがなければ空欄)
5. フォルムに対応するタイプ 1
6. フォルムに対応するタイプ 2 (なければ空欄)

## Usage

```shell
pip install git+https://takosavi.net/pokescreader-sv.git
create-db
```

結果はテキストとして標準出力に出力されます.
保存する際はリダイレクト等を使ってください.

## For Developers

プロジェクト管理に [Poetry](https://python-poetry.org/)
を使用しています.

```shell
poetry install
```

### テスト・コード解析

```shell
poetry run pytest
poetry run black --check .
poetry run ruff check .
poetry run mypy .
```

## ライセンス

[![MIT License](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://opensource.org/licenses/MIT)

Copyright (c) 2024 もち (Mochi)
