# 테스트 안티패턴 (pytest 예시)

- 사용: tdd-red (작성), tdd-green (테스트 이상 보고 판단), tdd-refactor (리뷰 관점)
- 출처: Matt Pocock `tdd` (동어반복 · 구현 결합), Superpowers `test-driven-development` (change detector · mock 단언) 를 실습용으로 축약

## 1. 동어반복 (기대값을 코드처럼 계산)

```python
# ❌ 구현과 같은 식 → 식이 틀려도 통과
assert body["fail_rate"] == round(fail / (fail + success) * 100, 2)
# ✅ 문서의 숫자 그대로
assert body["fail_rate"] == 5.0
```

## 2. 구현 결합 (내부를 들여다보는 검증)

```python
# ❌ 내부 함수 mock, DB 직접 조회로 판정
monkeypatch.setattr(health, "should_halt", lambda r: True)
assert db.query_one("SELECT status FROM rollouts WHERE id=?", (rid,))["status"] == "HALTED"
# ✅ 공개 API 로 결과 확인
assert client.get(f"/rollouts/{rid}").json()["status"] == "HALTED"
```

- 예외: 문서에 seam 으로 적힌 서비스 함수 (`health.should_halt(rate)`) 는 직접 호출 가능

## 3. Change detector (값 · 문구만 고정)

```python
# ❌ 설정값을 그대로 다시 확인 → 규칙을 잡지 못함
assert config.HALT_THRESHOLD == 5
# ✅ 규칙이 드러나는 경계 동작 확인
@pytest.mark.parametrize("rate,halt", [(4.9, False), (5.0, True), (5.1, True)])
def test_halt_boundary(rate, halt):
    assert health.should_halt(rate) is halt
```

## 4. Mock 단언 (mock 이 불렸는지만 확인)

```python
# ❌ 호출 여부만 확인 → 결과가 틀려도 통과
assert fake_notify.called
# ✅ 결과 (기록 · 응답) 확인, mock 은 외부 단말 · 푸시만
assert client.get(f"/events?rollout_id={rid}").json()[0]["actor"] == "health-check"
```

## 5. RED 불인정 실패

| 실패 | 원인 | 처리 |
| --- | --- | --- |
| ImportError · NameError | 없는 이름 사용 | 문서 · 계획의 이름 확인, 없으면 사람에게 질문 |
| fixture 오류 | conftest 사용법 오류 | 기존 테스트 형식 따르기 |
| (참고) `backend/` 안 예외 | 제품 결함 (0 나누기 등) | RED 인정 ✅ |
| 처음부터 통과 | 이미 맞는 동작 · 약한 단언 | 회귀 보호 표시 또는 기대값 재확인 |
