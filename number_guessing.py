"""日本語CLIの数当てゲーム。"""

from random import randint as random_integer

MIN_NUMBER = 1
MAX_NUMBER = 100
MAX_ATTEMPTS = 10


def _parse_guess(answer):
    """半角整数の回答を検証し、無効ならNoneを返す。"""
    if not answer or not answer.isascii() or not answer.isdigit():
        return None
    normalized = answer.lstrip("0") or "0"
    if len(normalized) > len(str(MAX_NUMBER)):
        return None
    guess = int(normalized)
    return guess if MIN_NUMBER <= guess <= MAX_NUMBER else None


def _hint(guess, secret):
    """数の比較だけを行い、正解ならNoneを返す。"""
    if guess == secret:
        return None
    return "もっと大きい数です" if guess < secret else "もっと小さい数です"


def _play_round(secret, input_fn, output_fn):
    """1ゲームを進め、勝敗確定ならTrue、途中終了ならFalseを返す。"""
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        output_fn("数を入力してください：")
        answer = input_fn().strip()
        if answer.lower() == "q":
            return False
        guess = _parse_guess(answer)
        if guess is None:
            output_fn(
                f"無効な入力です。{MIN_NUMBER}〜{MAX_NUMBER}の半角整数を再入力してください。"
            )
            continue
        attempts += 1
        hint = _hint(guess, secret)
        if hint is None:
            output_fn(f"正解です！{attempts}回目で当てました。")
            return True
        output_fn(hint)
        if attempts < MAX_ATTEMPTS:
            output_fn(f"残り{MAX_ATTEMPTS - attempts}回")
    output_fn(f"残念！正解は{secret}でした。")
    return True


def _ask_replay(input_fn, output_fn):
    """有効な再プレイ選択を受け取る。nとqは終了として扱う。"""
    while True:
        output_fn("もう一度遊びますか？ y: はい / n: いいえ / q: 終了")
        choice = input_fn().strip().lower()
        if choice in ("n", "q"):
            return False
        if choice == "y":
            return True
        output_fn("無効な入力です。y / n / q を再入力してください。")


def run(*, input_fn=input, output_fn=print, randint=random_integer):
    """各ゲームと再プレイをつなぎ、EOFとCtrl+Cを正常終了として扱う。"""
    try:
        while True:
            output_fn(
                f"{MIN_NUMBER}〜{MAX_NUMBER}の整数を当ててください。"
                f"回答は{MAX_ATTEMPTS}回まで。qで終了します。"
            )
            secret = randint(MIN_NUMBER, MAX_NUMBER)
            if not _play_round(secret, input_fn, output_fn):
                return
            if not _ask_replay(input_fn, output_fn):
                return
    except (EOFError, KeyboardInterrupt):
        return


if __name__ == "__main__":
    run()
