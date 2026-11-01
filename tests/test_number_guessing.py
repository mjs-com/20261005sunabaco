"""承認済みREQ-01〜06のCLI受け入れテスト。実装は含めない。"""

import importlib
import io
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, call


WIN = r"正解(?:です|[!！]|しました)|おめでとう|勝利|当たり"
LOSE = r"残念|ゲームオーバー|敗北"
REPLAY = r"もう一度|もう一回|再プレイ"
RETRY = r"再入力|もう一度|入力し直|入力して|入力してください"


class Session:
    """入力列と出力を記録するテスト用の入出力。ゲーム判定は行わない。"""

    def __init__(self, inputs, secrets):
        self.inputs = iter(inputs)
        self.outputs = []
        self.before_reads = []
        self.read_count = 0
        self.randint = Mock(side_effect=secrets)

    def read(self, prompt=""):
        if prompt:
            self.write(prompt)
        self.before_reads.append(self.text)
        self.read_count += 1
        try:
            item = next(self.inputs)
        except StopIteration:
            raise AssertionError("予定外の追加入力：終了条件を確認してください") from None
        if isinstance(item, BaseException):
            raise item
        return item

    def write(self, message):
        if not isinstance(message, str):
            raise AssertionError("output_fnには日本語の表示文字列を渡してください")
        self.outputs.append(message)

    @property
    def text(self):
        return "\n".join(self.outputs)


class NumberGuessingTests(unittest.TestCase):
    def setUp(self):
        # 実装がない間も全テストを発見でき、各ケースが未実装を理由に失敗する。
        self.run_game = importlib.import_module("number_guessing").run

    def play(self, inputs, secrets=(50,)):
        session = Session(inputs, secrets)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.run_game(
                input_fn=session.read,
                output_fn=session.write,
                randint=session.randint,
            )
        self.assertEqual(stdout.getvalue(), "", "表示はoutput_fnへ渡す")
        self.assertEqual(stderr.getvalue(), "", "終了時に例外詳細を表示しない")
        return session

    def assert_won_in(self, text, attempts):
        self.assertRegex(text, WIN)
        self.assertRegex(text, rf"(?<!\d){attempts}\s*回(?:目|で|でした|です|の)")
        self.assertNotRegex(text, LOSE)

    def test_req01_rules_appear_before_first_answer(self):
        s = self.play(["q"])
        first = s.before_reads[0]
        self.assertRegex(first, r"(?<!\d)1\s*(?:〜|～|~|から|[-–－])\s*100")
        self.assertRegex(first, r"10\s*回")
        self.assertRegex(first, r"[qQ].*(?:終了|やめ)|(?:終了|やめ).*[qQ]")

    def test_req01_draws_once_with_inclusive_bounds(self):
        s = self.play(["30", "70", "50", "n"])
        s.randint.assert_called_once_with(1, 100)
        self.assert_won_in(s.text, 3)

    def test_req01_does_not_reveal_secret_before_outcome(self):
        s = self.play(["30", "70", "q"], secrets=(53,))
        self.assertNotRegex(s.text, r"(?<!\d)53(?!\d)")
        self.assertNotRegex(s.text, WIN)
        self.assertNotRegex(s.text, LOSE)

    def test_req02_accepts_boundary_answers(self):
        for secret in (1, 100):
            with self.subTest(secret=secret):
                s = self.play([str(secret), "n"], secrets=(secret,))
                self.assert_won_in(s.text, 1)

    def test_req02_trims_whitespace_and_accepts_leading_zeroes(self):
        for answer in ("007", " 007 ", "\t007\t", "0007"):
            with self.subTest(answer=answer):
                s = self.play([answer, "n"], secrets=(7,))
                self.assert_won_in(s.text, 1)

    def test_req02_rejects_invalid_answers_without_using_attempt(self):
        invalid = (
            "", "   ", "abc", "1.5", "+7", "-7", "７", "５０", "٠٧",
            "0", "000", "101", "999", "1e1", "7_0", "7 0", "7\n0",
        )
        for answer in invalid:
            with self.subTest(answer=repr(answer)):
                s = self.play([answer, "50", "n"])
                feedback = s.before_reads[1][len(s.before_reads[0]):]
                self.assertRegex(feedback, r"無効|整数|半角|範囲|1.*100|入力が空|入力されて")
                self.assertRegex(feedback, RETRY)
                self.assert_won_in(s.text, 1)
                s.randint.assert_called_once_with(1, 100)

    def test_req02_invalid_answer_does_not_consume_last_attempt(self):
        s = self.play(["1"] * 9 + ["abc", "50", "n"])
        self.assert_won_in(s.text, 10)

    def test_req03_smaller_answer_gets_higher_hint_and_nine_remaining(self):
        s = self.play(["30", "q"])
        self.assertIn("もっと大きい数です", s.text)
        self.assertNotIn("もっと小さい数です", s.text)
        self.assertRegex(s.text, r"残り\s*9\s*回")

    def test_req03_larger_answer_gets_lower_hint_and_nine_remaining(self):
        s = self.play(["70", "q"])
        self.assertIn("もっと小さい数です", s.text)
        self.assertNotIn("もっと大きい数です", s.text)
        self.assertRegex(s.text, r"残り\s*9\s*回")

    def test_req03_repeated_answer_uses_another_attempt(self):
        s = self.play(["30", "30", "50", "n"])
        self.assertEqual(s.text.count("もっと大きい数です"), 2)
        self.assertRegex(s.text, r"残り\s*8\s*回")
        self.assert_won_in(s.text, 3)

    def test_req03_remaining_count_decreases_until_last_answer(self):
        s = self.play(["1"] * 9 + ["q"])
        numbers = re.findall(r"残り\s*(\d+)\s*回", s.text)
        # 開始時に残り10回を表示してもしなくてもよい。
        self.assertEqual([int(n) for n in numbers if int(n) != 10], list(range(9, 0, -1)))

    def test_req04_first_answer_can_win(self):
        s = self.play(["50", "n"])
        self.assert_won_in(s.text, 1)
        self.assertEqual(s.read_count, 2)
        self.assertRegex(s.text, REPLAY)

    def test_req04_tenth_correct_answer_wins_instead_of_losing(self):
        s = self.play(["1"] * 9 + ["50", "n"])
        self.assert_won_in(s.text, 10)
        self.assertEqual(s.read_count, 11)

    def test_req04_tenth_wrong_answer_loses_and_reveals_secret(self):
        s = self.play(["1"] * 10 + ["n"], secrets=(53,))
        self.assertRegex(s.text, LOSE)
        self.assertRegex(s.text, r"(?<!\d)53(?!\d)")
        self.assertNotRegex(s.text, WIN)
        self.assertRegex(s.text, REPLAY)
        self.assertEqual(s.read_count, 11)

    def test_req04_no_more_game_answers_after_win(self):
        # 勝利後の数字は再プレイ入力として無効。大小判定してはいけない。
        s = self.play(["50", "30", "n"])
        self.assert_won_in(s.text, 1)
        self.assertNotIn("もっと大きい数です", s.text)
        self.assertNotIn("もっと小さい数です", s.text)
        s.randint.assert_called_once_with(1, 100)

    def test_req04_no_more_game_answers_after_loss(self):
        s = self.play(["1"] * 10 + ["50", "n"])
        self.assertRegex(s.text, LOSE)
        self.assertNotRegex(s.text, WIN)
        self.assertEqual(s.read_count, 12)
        s.randint.assert_called_once_with(1, 100)

    def test_req05_yes_starts_new_game_with_new_secret_and_reset_count(self):
        for yes in ("y", "Y", " y ", "\tY\t"):
            with self.subTest(yes=yes):
                s = self.play(["30", "50", yes, "75", "n"], secrets=(50, 75))
                self.assert_won_in(s.before_reads[2], 2)
                second_game = s.text[len(s.before_reads[2]):]
                self.assert_won_in(second_game, 1)
                self.assertEqual(s.randint.call_args_list, [call(1, 100), call(1, 100)])

    def test_req05_can_replay_after_loss(self):
        s = self.play(["1"] * 10 + ["y", "75", "n"], secrets=(50, 75))
        self.assertRegex(s.before_reads[10], LOSE)
        self.assert_won_in(s.text[len(s.before_reads[10]):], 1)
        self.assertEqual(s.randint.call_count, 2)

    def test_req05_new_game_may_have_same_secret(self):
        s = self.play(["50", "y", "50", "n"], secrets=(50, 50))
        self.assert_won_in(s.before_reads[1], 1)
        self.assert_won_in(s.text[len(s.before_reads[1]):], 1)
        self.assertEqual(s.randint.call_count, 2)

    def test_req05_no_exits_without_starting_another_game(self):
        for no in ("n", "N", " n ", "\tN\t"):
            with self.subTest(no=no):
                s = self.play(["50", no])
                self.assertEqual(s.read_count, 2)
                s.randint.assert_called_once_with(1, 100)

    def test_req05_invalid_replay_input_prompts_again_without_new_game(self):
        for invalid in ("", "abc", "yes", "1", "ｙ"):
            with self.subTest(invalid=invalid):
                s = self.play(["50", invalid, "n"])
                feedback = s.before_reads[2][len(s.before_reads[1]):]
                self.assertRegex(feedback, RETRY)
                self.assertEqual(s.read_count, 3)
                s.randint.assert_called_once_with(1, 100)

    def test_req06_quit_during_answer_does_not_reveal_or_declare_outcome(self):
        for quit_input in ("q", "Q", " q ", "\tQ\t"):
            with self.subTest(quit_input=quit_input):
                s = self.play([quit_input], secrets=(53,))
                self.assertEqual(s.read_count, 1)
                self.assertNotRegex(s.text, WIN)
                self.assertNotRegex(s.text, LOSE)
                self.assertNotRegex(s.text, r"(?<!\d)53(?!\d)")

    def test_req06_quit_after_nine_wrong_answers_is_not_a_tenth_attempt(self):
        s = self.play(["1"] * 9 + ["q"], secrets=(53,))
        self.assertNotRegex(s.text, LOSE)
        self.assertNotRegex(s.text, WIN)
        self.assertNotRegex(s.text, r"(?<!\d)53(?!\d)")
        self.assertEqual(s.read_count, 10)

    def test_req06_quit_during_replay_exits(self):
        for quit_input in ("q", "Q", " q "):
            with self.subTest(quit_input=quit_input):
                s = self.play(["50", quit_input])
                self.assertEqual(s.read_count, 2)
                s.randint.assert_called_once_with(1, 100)

    def test_req06_eof_and_interrupt_during_answer_exit_normally(self):
        for interruption in (EOFError, KeyboardInterrupt):
            with self.subTest(interruption=interruption.__name__):
                s = self.play([interruption()], secrets=(53,))
                self.assertEqual(s.read_count, 1)
                self.assertNotRegex(s.text, WIN)
                self.assertNotRegex(s.text, LOSE)
                self.assertNotRegex(s.text, r"(?<!\d)53(?!\d)")
                self.assertNotIn("Traceback", s.text)

    def test_req06_eof_and_interrupt_during_replay_exit_normally(self):
        for interruption in (EOFError, KeyboardInterrupt):
            with self.subTest(interruption=interruption.__name__):
                s = self.play(["50", interruption()])
                self.assertEqual(s.read_count, 2)
                self.assertNotIn("Traceback", s.text)
                s.randint.assert_called_once_with(1, 100)


if __name__ == "__main__":
    unittest.main()

