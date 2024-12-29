# /// script
# requires-python = ">=3.11,<4"
# dependencies = ["requests<3"]
# ///

import csv
import dataclasses
import operator
import sys
from typing import Optional, TextIO

import httpx


def _filter_japanese_name(items: list[dict]) -> Optional[str]:
    """
    名称のリストから日本語名称を選択する. 見つからないときは None を返す.
    """
    return next(
        (item["name"] for item in items if item["language"]["name"] == "ja"),
        None,
    ) or next(
        (item["name"] for item in items if item["language"]["name"] == "ja-Hrkt"),
        None,
    )


@dataclasses.dataclass(frozen=True)
class PokemonForm:
    id: int
    name: str | None
    type1: str
    type2: str | None = None


def convert_pokemon_form(form: dict) -> PokemonForm:
    """
    Pokemon Form を DTO に変換する.
    """
    assert not form["is_mega"], "メガシンカは事前に取り除いているはず"

    types = [type["type"]["name"] for type in sorted(form["types"], key=_TYPE_SORT_KEY)]
    assert len(types) in (1, 2), "タイプが 1 つか 2 つであることが前提"

    return PokemonForm(form["id"], _filter_japanese_name(form["form_names"]), *types)


def is_acceptable_pokemon_form(name: str) -> bool:
    """
    採用可能な Pokemon Form の名前かどうか判定する.

    ピチュー: SV ではギザミミがいなくなった
    >>> is_acceptable_pokemon_form('pichu')
    True
    >>> is_acceptable_pokemon_form('pichu-spiky-eared')
    False

    マホイップ: SV ではストロベリーしかいないのでそれだけにする
    >>> is_acceptable_pokemon_form('alcremie-vanilla-cream-strawberry-sweet')
    True
    >>> is_acceptable_pokemon_form('alcremie-vanilla-cream-berry-sweet')
    False
    """
    if name.startswith("pichu-"):
        return not name.endswith("-spiky-eared")
    if name.startswith("alcremie-"):
        return "-strawberry-" in name
    return True


_TYPE_SORT_KEY = operator.itemgetter("slot")


@dataclasses.dataclass(frozen=True)
class Pokemon:
    id: int
    forms: list[PokemonForm]


def convert_pokemon(pokemon: dict) -> Pokemon:
    """
    Pokemon を DTO に変換する.
    """
    forms = sorted(
        (
            httpx.get(form["url"]).json()
            for form in pokemon["forms"]
            if is_acceptable_pokemon_form(form["name"])
        ),
        key=operator.itemgetter("form_order"),
    )

    # 進化前後の都合でフォルムが複数あるポケモン
    if pokemon["species"]["name"] in {"mothim", "scatterbug", "spewpa"}:
        forms = forms[:1]
    return Pokemon(pokemon["id"], [convert_pokemon_form(f) for f in forms])


def is_acceptable_pokemon(name: str) -> bool:
    """
    採用可能な Pokemon の名前かどうか判定する.

    メガシンカ, キョダイマックスのすがたを省く
    >>> is_acceptable_pokemon('venusaur')
    True
    >>> is_acceptable_pokemon('venusaur-mega')
    False
    >>> is_acceptable_pokemon('venusaur-gmax')
    False

    ゲンシカイキのすがたを省く
    >>> is_acceptable_pokemon('kyogre')
    True
    >>> is_acceptable_pokemon('kyogre-primal')
    False

    ぬしポケモンを省く
    >>> is_acceptable_pokemon('mimikyu-disguised')
    True
    >>> is_acceptable_pokemon('mimikyu-totem-disguised')
    False

    ピカブイパートナーを省く
    >>> is_acceptable_pokemon('eevee')
    True
    >>> is_acceptable_pokemon('eevee-starter')
    False

    ピカチュウ: SV では帽子違いしか確認できなかったのでそれ以外を省く
    >>> is_acceptable_pokemon('pikachu')
    True
    >>> is_acceptable_pokemon('pikachu-world-cap')
    True
    >>> is_acceptable_pokemon('pikachu-rock-star')
    False

    ゲッコウガ: 特性違いで別ポケモン扱いなので重複を省く
    >>> is_acceptable_pokemon('greninja')
    True
    >>> is_acceptable_pokemon('greninja-battle-bond')
    False
    >>> is_acceptable_pokemon('greninja-battle-ash')
    False

    ジガルデ: 特性違いで別ポケモン扱いなので重複を省く
    >>> is_acceptable_pokemon('zygarde-10')
    True
    >>> is_acceptable_pokemon('zygarde-10-power-construct')
    False

    イワンコ: マイペースが別ポケモン扱いなので重複を省く
    >>> is_acceptable_pokemon('rockruff')
    True
    >>> is_acceptable_pokemon('rockruff-own-tempo')
    False

    メテノ: りゅうせいのすがたが重複するので, あかいろのコアだけ受け入れる
    >>> is_acceptable_pokemon('minior-red-meteor')
    True
    >>> is_acceptable_pokemon('minior-orange-meteor')
    False
    >>> is_acceptable_pokemon('minior-orange')
    True

    コライドン: 表示が存在するフォルムだけ受け入れる
    >>> is_acceptable_pokemon('koraidon')
    True
    >>> is_acceptable_pokemon('koraidon-limited-build')
    True
    >>> is_acceptable_pokemon('koraidon-sprinting-build')
    False

    ミライドン: 表示が存在するフォルムだけにする
    >>> is_acceptable_pokemon('miraidon')
    True
    >>> is_acceptable_pokemon('miraidon-low-power-mode')
    True
    >>> is_acceptable_pokemon('miraidon-drive-mode')
    False
    """
    if name.endswith("-starter"):
        return False
    if name.startswith("pikachu-"):
        return name.endswith("-cap")
    if name.startswith("greninja-"):
        return False
    if name.startswith("zygarde-"):
        return not name.endswith("-power-construct")
    if name.startswith("rockruff-"):
        return not name.endswith("-own-tempo")
    if name.startswith("minior-") and name.endswith("-meteor"):
        return name == "minior-red-meteor"
    if name.startswith("koraidon-"):
        return name.endswith("-limited-build")
    if name.startswith("miraidon-"):
        return name.endswith("-low-power-mode")

    components = frozenset(name.split("-"))
    if any(
        word in components for word in ("mega", "primal", "totem", "gmax", "starter")
    ):
        return False
    return True


@dataclasses.dataclass(frozen=True)
class PokemonSpecies:
    id: int
    name: str
    pokemons: list[Pokemon]


def convert_pokemon_species(species: dict) -> PokemonSpecies:
    name = _filter_japanese_name(species["names"])
    assert name

    pokemons = sorted(
        (
            httpx.get(variety["pokemon"]["url"]).json()
            for variety in species["varieties"]
            if is_acceptable_pokemon(variety["pokemon"]["name"])
        ),
        key=_pokemon_sort_key,
    )
    assert pokemons
    assert pokemons[0]["is_default"]

    return PokemonSpecies(species["id"], name, [convert_pokemon(p) for p in pokemons])


def _pokemon_sort_key(pokemon: dict) -> tuple[bool, int]:
    order: int = pokemon["order"]
    if order < 0:
        order = 999999999
    return not pokemon["is_default"], order


def main(out: TextIO = sys.stdout) -> None:
    pokedex = httpx.get("https://pokeapi.co/api/v2/pokedex/national").json()

    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    species = (
        (
            e["entry_number"],
            convert_pokemon_species(httpx.get(e["pokemon_species"]["url"]).json()),
        )
        for e in pokedex["pokemon_entries"]
    )
    writer.writerows(
        [entry_number, idx, s.name, f.name, f.type1, f.type2]
        for entry_number, s in species
        for idx, (_, f) in enumerate((p, f) for p in s.pokemons for f in p.forms)
    )


if __name__ == "__main__":
    main()
