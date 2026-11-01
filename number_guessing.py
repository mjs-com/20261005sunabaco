"""日本語CLIの数当てゲーム。"""

from random import randint as random_integer


def _parse_guess(answer):
    """半角整数の回答を検証し、無効ならNoneを返す。"""
    if not answer or not answer.isascii() or not answer.isdigit():
        return None
    normalized = answer.lstrip("0") or "0"
    if len(normalized) > 3:
        return None
    guess = int(normalized)
    return guess if 1 <= guess <= 100 else None


def _hint(guess, secret):
    """数の比較だけを行い、正解ならNoneを返す。"""
    if guess == secret:
        return None
    return "もっと大きい数です" if guess < secret else "もっと小さい数です"


def run(*, input_fn=input, output_fn=print, randint=random_integer):
    try:
        while True:
            output_fn("1〜100の整数を当ててください。回答は10回まで。qで終了します。")
            secret = randint(1, 100)
            attempts = 0
            while attempts < 10:
                output_fn("数を入力してください：")
                answer = input_fn().strip()
                if answer.lower() == "q":
                    return
                guess = _parse_guess(answer)
                if guess is None:
                    output_fn("無効な入力です。1〜100の半角整数を再入力してください。")
                    continue
                attempts += 1
                hint = _hint(guess, secret)
                if hint is None:
                    output_fn(f"正解です！{attempts}回目で当てました。")
                    break
                output_fn(hint)
                if attempts == 10:
                    output_fn(f"残念！正解は{secret}でした。")
                    break
                output_fn(f"残り{10 - attempts}回")
            while True:
                output_fn("もう一度遊びますか？ y: はい / n: いいえ / q: 終了")
                choice = input_fn().strip().lower()
                if choice in ("n", "q"):
                    return
                if choice == "y":
                    break
                output_fn("無効な入力です。y / n / q を再入力してください。")
    except (EOFError, KeyboardInterrupt):
        return


if __name__ == "__main__":
    run()
