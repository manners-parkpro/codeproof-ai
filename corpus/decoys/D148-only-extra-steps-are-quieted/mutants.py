"""D148 변이 - 쓰는 단계 18개 · 쓰는 단계 점검 33개 · 독립 검토 3개 · 교차 2개 (약화 47 · 안전 9 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_SAVE = "    save()\n"
_COUNT = "    return sum(_quietly(step) for step in steps)\n"
_CATCH = "    except Exception:\n        return False\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[저장] _quietly 로 부름 (twin)": [(_SAVE, "    _quietly(save)\n")],
    "[저장] 실패하면 0 을 돌려줌": [(_SAVE, "    if not _quietly(save):\n        return 0\n")],
    "[저장] 실패하면 한 번 더": [(_SAVE, "    try:\n        save()\n    except Exception:\n        save()\n")],
    "[예외 종류] ValueError 는 삼킴": [(_SAVE, "    try:\n        save()\n    except ValueError:\n        return 0\n")],
    "[예외 종류] 표준 라이브러리 밖의 예외는 삼킴": [
        (_SAVE, '    try:\n        save()\n    except Exception as exc:\n        if type(exc).__module__ == "builtins":\n            raise\n        return 0\n'),
    ],
    "[BaseException] save 의 KeyboardInterrupt 는 삼킴": [(_SAVE, "    try:\n        save()\n    except KeyboardInterrupt:\n        return 0\n")],
    "[그대로] RuntimeError 로 감싸 올림": [
        (_SAVE, '    try:\n        save()\n    except Exception as exc:\n        raise RuntimeError("저장 실패") from exc\n'),
    ],
    "[순서] extras 를 save 보다 먼저": [(_SAVE + _COUNT, "    done = sum(_quietly(step) for step in steps)\n    save()\n    return done\n")],
    "[차례] 거꾸로 부름": [(_COUNT, "    return sum(_quietly(step) for step in reversed(steps))\n")],
    "[한 번씩] 실패한 단계를 한 번 더": [(_COUNT, "    return sum(_quietly(step) or _quietly(step) for step in steps)\n")],
    "[셈] 실패한 단계도 셈": [(_COUNT, "    for step in steps:\n        _quietly(step)\n    return len(steps)\n")],
    "[셈] 첫 실패에서 멈춤": [
        (_COUNT, "    done = 0\n    for step in steps:\n        if not _quietly(step):\n            break\n        done += 1\n    return done\n"),
    ],
    "[Exception] 일부 하위 클래스만 삼킴": [(_CATCH, "    except (ArithmeticError, LookupError, OSError):\n        return False\n")],
    "[BaseException] 단계의 BaseException 도 삼킴": [(_CATCH, "    except BaseException:\n        return False\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[크기] 앞의 16개 단계만 부름': [('    return sum(_quietly(step) for step in steps)\n', '    return sum(_quietly(step) for step in steps[:16])\n')],
    '[같은 단계 여럿] 같은 단계는 한 번만 부름': [('    return sum(_quietly(step) for step in steps)\n', '    return sum(_quietly(step) for step in dict.fromkeys(steps))\n')],
    '[예외 종류] save 의 TimeoutError 는 삼킴': [('    save()\n', '    try:\n        save()\n    except TimeoutError:\n        return 0\n')],
    '[예외 값] errno 가 EAGAIN 인 save 실패는 삼킴': [('from collections.abc import Callable\n', 'import errno\nfrom collections.abc import Callable\n'), ('    save()\n', '    try:\n        save()\n    except OSError as exc:\n        if exc.errno != errno.EAGAIN:\n            raise\n        return 0\n')],
    '[예외 값] 메시지에 timeout 이 든 save 실패는 삼킴': [('    save()\n', '    try:\n        save()\n    except Exception as exc:\n        if "timeout" not in str(exc).lower():\n            raise\n        return 0\n')],
    '[extras 모양] extras 가 비면 save 의 Exception 을 삼킴': [('    save()\n', '    if not extras:\n        _quietly(save)\n        return 0\n    save()\n')],
    '[BaseException 둘] 남은 단계를 마저 부르고 처음 BaseException 을 올림': [('    return sum(_quietly(step) for step in steps)\n', '    done = 0\n    halt = None\n    for step in steps:\n        try:\n            done += _quietly(step)\n        except BaseException as exc:\n            if halt is None:\n                halt = exc\n    if halt is not None:\n        raise halt\n    return done\n')],
    '[BaseExceptionGroup] except* Exception 으로 실패를 적음': [('    try:\n        step()\n    except Exception:\n        return False\n    return True\n', '    ok = True\n    try:\n        step()\n    except* Exception:\n        ok = False\n    return ok\n')],
    '[크기] 앞의 64개 단계만 부름': [('    return sum(_quietly(step) for step in steps)\n', '    return sum(_quietly(step) for step in steps[:64])\n')],
    '[크기] 앞의 256개 단계만 부름': [('    return sum(_quietly(step) for step in steps)\n', '    return sum(_quietly(step) for step in steps[:256])\n')],
    '[BaseExceptionGroup] contextlib.suppress 로 삼킴 - 섞인 그룹을 나눠 새 그룹을 올림 (점검이 안전으로 적었던 약화)': [('from collections.abc import Callable\n', 'import contextlib\nfrom collections.abc import Callable\n'), ('    try:\n        step()\n    except Exception:\n        return False\n    return True\n', '    with contextlib.suppress(Exception):\n        step()\n        return True\n    return False\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[예외 종류] save 의 OSError 는 삼킴': [('    save()\n', '    try:\n        save()\n    except OSError:\n        return 0\n')],
    '[예외 종류] save 의 LookupError 는 삼킴': [('    save()\n', '    try:\n        save()\n    except LookupError:\n        return 0\n')],
    '[예외 종류] save 를 map 으로 불러 StopIteration 이 끝으로 읽힘': [('    save()\n', '    any(map(lambda run: run(), [save]))\n')],
    '[예외 종류] save 의 RuntimeError 는 삼킴': [('    save()\n', '    try:\n        save()\n    except RuntimeError:\n        return 0\n')],
    '[BaseException] save 의 SystemExit 는 삼킴': [('    save()\n', '    try:\n        save()\n    except SystemExit:\n        return 0\n')],
    '[BaseException] save 의 표준 라이브러리 밖 BaseException 은 삼킴': [('    save()\n', '    try:\n        save()\n    except Exception:\n        raise\n    except BaseException as exc:\n        if type(exc).__module__ != "builtins":\n            return 0\n        raise\n')],
    '[저장] 실패하면 한 번 더 부르고 또 실패하면 첫 예외': [('    save()\n', '    try:\n        save()\n    except Exception as first:\n        try:\n            save()\n        except Exception:\n            raise first from None\n')],
    '[저장 실패] extras 를 부른 뒤 다시 던짐': [('    save()\n', '    try:\n        save()\n    except BaseException:\n        for step in steps:\n            _quietly(step)\n        raise\n')],
    '[빈 값] extras 가 비면 save 도 부르지 않고 0': [('    save()\n', '    if not extras:\n        return 0\n    save()\n')],
    '[셈] 모두 성공하면 마지막 단계를 세지 않음': [('    return sum(_quietly(step) for step in steps)\n', '    done = [_quietly(step) for step in steps]\n    return sum(done) - (bool(done) and all(done))\n')],
    '[셈] 모든 단계가 실패하면 RuntimeError': [('    return sum(_quietly(step) for step in steps)\n', '    done = [_quietly(step) for step in steps]\n    if done and not any(done):\n        raise RuntimeError("모든 단계 실패")\n    return sum(done)\n')],
    '[BaseException] 단계의 KeyboardInterrupt 도 삼킴': [('    except Exception:\n        return False\n', '    except (Exception, KeyboardInterrupt):\n        return False\n')],
    '[BaseException] 단계의 SystemExit 도 삼킴': [('    except Exception:\n        return False\n', '    except (Exception, SystemExit):\n        return False\n')],
    '[BaseException] 단계의 GeneratorExit 도 삼킴': [('    except Exception:\n        return False\n', '    except (Exception, GeneratorExit):\n        return False\n')],
    '[BaseException] 단계의 표준 라이브러리 밖 BaseException 도 삼킴': [('    except Exception:\n        return False\n', '    except Exception:\n        return False\n    except BaseException as exc:\n        if type(exc).__module__ == "builtins":\n            raise\n        return False\n')],
    '[그대로] 단계의 BaseException 을 RuntimeError 로 감싸 올림': [('    except Exception:\n        return False\n', '    except Exception:\n        return False\n    except BaseException as exc:\n        raise RuntimeError("단계 중단") from exc\n')],
    '[한 번씩] BaseException 을 낸 단계를 한 번 더 부르고 올림': [('    except Exception:\n        return False\n', '    except Exception:\n        return False\n    except BaseException:\n        step()\n        raise\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[save] 원소가 하나인 ExceptionGroup 을 풀어 원소를 올림': [('    save()\n', '    try:\n        save()\n    except ExceptionGroup as eg:\n        if len(eg.exceptions) == 1:\n            raise eg.exceptions[0] from None\n        raise\n')],
    '[save] except* 로 받아 첫 원소를 올림': [('    save()\n', '    try:\n        save()\n    except* Exception as eg:\n        raise eg.exceptions[0]\n')],
    '[save] 같은 객체를 from None 으로 다시 올림 - 원인 사슬이 지워짐': [('    save()\n', '    try:\n        save()\n    except Exception as exc:\n        raise exc from None\n')],
    # 교차 렌즈 - 원래 증명이 놓치던 약화
    '[자리] 살아 있는 목록을 돎 - 단계가 목록을 비우면 뒤 자리를 부르지 않음 (고치기 전 판)': [('    steps = tuple(extras)\n    save()\n    return sum(_quietly(step) for step in steps)\n', '    save()\n    return sum(_quietly(step) for step in extras)\n')],
    '[자리] save 뒤에 떠 둠 - save 가 더한 단계까지 부름': [('    steps = tuple(extras)\n    save()\n', '    save()\n    steps = tuple(extras)\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "save 를 try 로 감싸 다시 던짐 (안전)": [(_SAVE, "    try:\n        save()\n    except BaseException:\n        raise\n")],
    "단계 결과를 목록으로 모아 셈 (안전)": [(_COUNT, "    done = [_quietly(step) for step in steps]\n    return done.count(True)\n")],
    "for 문으로 셈 (안전)": [(_COUNT, "    done = 0\n    for step in steps:\n        done += _quietly(step)\n    return done\n")],
    "else 절에서 True (안전)": [(_CATCH + "    return True\n", _CATCH + "    else:\n        return True\n")],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '[다른 구현] 성공한 단계만 모아 len (안전)': [('    return sum(_quietly(step) for step in steps)\n', '    return len([step for step in steps if _quietly(step)])\n')],
    '[다른 구현] save 예외를 이름으로 받아 다시 던짐 (안전)': [('    save()\n', '    try:\n        save()\n    except BaseException as exc:\n        raise exc\n')],
    '[다른 구현] 플래그로 성공을 적음 (안전)': [('    try:\n        step()\n    except Exception:\n        return False\n    return True\n', '    ok = False\n    try:\n        step()\n        ok = True\n    except Exception:\n        pass\n    return ok\n')],
    '[컨테이너] 떠 둔 단계를 list 로 바꿔 돎 (안전)': [('    return sum(_quietly(step) for step in steps)\n', '    return sum(_quietly(step) for step in list(steps))\n')],
    '[다른 구현] 인덱스로 돎 (안전)': [('    return sum(_quietly(step) for step in steps)\n', '    return sum(_quietly(steps[i]) for i in range(len(steps)))\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
