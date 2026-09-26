"""모든 decoy 쌍에 **실행 가능한 반증 시도**가 있는지 강제한다.

🔴 왜 중앙 테스트 파일이 아니라 쌍마다 proof.py 인가.

전에는 `test_safety_claims.py` 한 파일에 손으로 케이스를 적었다. 그 결과
19쌍 중 8쌍(42%)에 twin 반증이 없었고, **그중 하나가 D015** - 안전 근거가
실제로 거짓이었던 바로 그 쌍이다. 우연이 아니라 인과다: 중앙 파일에 적는
방식은 빠뜨려도 아무도 모른다.

쌍마다 proof.py 를 두고 이 테스트가 전수로 돌면, 빠뜨리는 것이 **불가능**해진다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codeproof_ai.corpus.proof import MAX_ATTEMPTS, ProofError, run_proof

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"
PAIRS = sorted(p for p in DECOYS.glob("D*") if p.is_dir())


def _ids(paths: list[Path]) -> list[str]:
    return [p.name.split("-")[0] for p in paths]


class TestEveryPairHasAnExecutableProof:
    def test_corpus_is_not_empty(self) -> None:
        assert PAIRS, "decoy 쌍이 하나도 없다 - 경로가 틀렸을 것이다"

    @pytest.mark.parametrize("pair", PAIRS, ids=_ids(PAIRS))
    def test_proof_file_exists(self, pair: Path) -> None:
        assert (pair / "proof.py").is_file(), (
            f"{pair.name}: proof.py 가 없다. 서면 근거만으로는 「증명된 음성」을 "
            "주장할 수 없다 - D015 가 11개 규칙을 통과하고도 틀렸다."
        )


class TestTheProofsHold:
    """🔴 이 프로젝트에서 가장 중요한 테스트.

    여기가 깨지면 코퍼스의 정답 라벨이 거짓이고, 그러면 헤드라인 숫자
    (채점 기준 편차)가 통째로 무의미해진다.
    """

    @pytest.mark.parametrize("pair", PAIRS, ids=_ids(PAIRS))
    def test_attack_fails_on_decoy_and_succeeds_on_twin(self, pair: Path) -> None:
        try:
            result = run_proof(pair)
        except ProofError as exc:
            pytest.fail(str(exc))
        assert result.ok, result.failure


class TestTheContractIsNotVacuous:
    """공격이 무능하면 통과하지 못하는지 확인한다."""

    def test_an_attack_that_never_succeeds_is_rejected(self, tmp_path: Path) -> None:
        """`return False` 만 적은 공격은 twin 조건에서 걸린다."""
        pair = _fake_pair(tmp_path, "def attack(mod: object) -> bool:\n    return False\n")
        assert run_proof(pair).failure is not None

    def test_an_attack_that_always_succeeds_is_rejected(self, tmp_path: Path) -> None:
        """`return True` 만 적은 공격은 decoy 조건에서 걸린다."""
        pair = _fake_pair(tmp_path, "def attack(mod: object) -> bool:\n    return True\n")
        f = run_proof(pair).failure
        assert f is not None
        assert "decoy 를 깼다" in f

    def test_unimportable_twin_is_an_error(self, tmp_path: Path) -> None:
        """🔴 파싱되는데 **import 가 안 되는** 짝을 잡는다.

        [실측] D048 의 twin 이 그랬다 - `dataclass` 가 가변 기본값을
        ValueError 로 거부해서 파일이 아예 로드되지 않았다. `decoy validate`
        의 V2 는 **파싱**만 보므로 통과시켰고, 이 층이 잡았다.

        import 조차 안 되는 twin 은 결함이 아니라 깨진 파일이고, 그런 짝은
        「가드만 다르다」는 전제가 성립하지 않는다.
        """
        pair = _fake_pair(tmp_path, "def attack(mod: object) -> bool:\n    return True\n")
        (pair / "twin.py").write_text(
            "raise ValueError('cannot import')\n", encoding="utf-8"
        )
        with pytest.raises(ProofError, match="import 하다 터졌다"):
            run_proof(pair)

    def test_missing_proof_is_an_error(self, tmp_path: Path) -> None:
        pair = _fake_pair(tmp_path, None)
        with pytest.raises(ProofError, match=r"proof\.py 이 없다"):
            run_proof(pair)


class TestRepeatedAttemptsStrengthenBothSides:
    """🔴 시도를 늘려도 **완화가 아니다**.

    경쟁 기반 반증은 비결정적이라 한 번에 재현되지 않을 수 있다.
    [실측] D042 가 단독 실행에서는 5/5 통과했는데 전체 테스트 부하에서
    twin 을 못 깨 flaky 했다. flaky 한 관문은 느린 관문보다 나쁘다 -
    사람이 재실행으로 넘기기 시작한다.

    그래서 `ATTEMPTS = N` 을 선언하면 **양쪽 모두** N회 시도한다.
    decoy 는 한 번이라도 깨지면 실패이므로 시도가 늘수록 **엄격해진다.**
    """

    def test_default_is_a_single_attempt(self, tmp_path: Path) -> None:
        pair = _fake_pair(
            tmp_path, "def attack(mod: object) -> bool:\n    return True\n"
        )
        assert run_proof(pair).attempts == 1

    def test_declared_attempts_are_honoured(self, tmp_path: Path) -> None:
        pair = _fake_pair(
            tmp_path,
            "ATTEMPTS = 4\n\ndef attack(mod: object) -> bool:\n    return True\n",
        )
        assert run_proof(pair).attempts == 4

    def test_a_flaky_attack_still_catches_a_broken_decoy(
        self, tmp_path: Path
    ) -> None:
        """🔴 decoy 를 가끔만 깨는 공격도 **잡아야 한다** - 시도가 늘면 더 잡는다."""
        pair = _fake_pair(
            tmp_path,
            "ATTEMPTS = 12\n"
            "_n = {'i': 0}\n\n"
            "def attack(mod: object) -> bool:\n"
            "    _n['i'] += 1\n"
            "    return _n['i'] % 5 == 0\n",
        )
        assert run_proof(pair).broke_decoy, (
            "가끔만 깨는 공격을 놓쳤다 - 라벨이 거짓인 decoy 가 통과한다"
        )

    def test_attempts_are_capped(self, tmp_path: Path) -> None:
        """무한정 시도하면 어떤 공격이든 언젠가 성공해 twin 조건이 무의미해진다."""
        pair = _fake_pair(
            tmp_path,
            "ATTEMPTS = 9999\n\ndef attack(mod: object) -> bool:\n    return True\n",
        )
        assert run_proof(pair).attempts == MAX_ATTEMPTS

    def test_bad_attempts_value_is_an_error(self, tmp_path: Path) -> None:
        pair = _fake_pair(
            tmp_path,
            "ATTEMPTS = 0\n\ndef attack(mod: object) -> bool:\n    return True\n",
        )
        with pytest.raises(ProofError, match="1 이상의 정수"):
            run_proof(pair)


class TestItCatchesTheBugThatSlippedThrough:
    """🔴 이 설계의 존재 이유 - 회귀 검사.

    D015 의 원래 가드는 `threading.Semaphore(4)` 였다. 세마포어 4는 스레드
    4개를 동시에 들여보내므로 경쟁이 실재했는데, 「증명된 음성」이라 라벨하고
    **11개 형식 검증 규칙을 전부 통과**시켰다. 형식 검증은 근거가 참인지
    볼 수 없다.

    그 버전을 복원해 공격이 실제로 잡는지 확인한다. 이게 깨지면 proof.py
    체계가 원래 목적을 잃은 것이다.
    """

    def test_semaphore_guard_is_caught(self, tmp_path: Path) -> None:
        src = DECOYS / "D015-caller-held-semaphore"
        pair = tmp_path / "D015-regression"
        pair.mkdir()
        for name in ("twin.py", "proof.py"):
            (pair / name).write_text(
                (src / name).read_text(encoding="utf-8"), encoding="utf-8"
            )
        # 틀린 가드를 되살린다 - 세마포어 4는 상호배제가 아니다
        (pair / "decoy.py").write_text(
            (src / "decoy.py")
            .read_text(encoding="utf-8")
            .replace("threading.Lock()", "threading.Semaphore(4)"),
            encoding="utf-8",
        )
        result = run_proof(pair)
        assert result.broke_decoy, (
            "세마포어 가드를 공격이 못 깼다 - 이 체계가 D015 를 다시 놓친다"
        )
        assert result.failure is not None
        assert "라벨이 거짓" in result.failure


def _fake_pair(tmp_path: Path, proof: str | None) -> Path:
    d = tmp_path / "D999-fake"
    d.mkdir()
    (d / "decoy.py").write_text("VALUE = 1\n", encoding="utf-8")
    (d / "twin.py").write_text("VALUE = 2\n", encoding="utf-8")
    if proof is not None:
        (d / "proof.py").write_text(proof, encoding="utf-8")
    return d
