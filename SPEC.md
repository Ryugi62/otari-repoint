---
id: 20261031T0400-spec-otari-repoint
title: "SPEC — Repoint (Otari 해커톤)"
type: reference
status: seedling
created: 2026-10-31
updated: 2026-10-31
links: ["[[projects/mozilla-otari-hackathon-2026-2026]]"]
private: false
---
# Repoint — SPEC (v0.1 2026-10-31)

kind: service

## 0. 목적
상용 모델용으로 만든 운영 에이전트의 과제를 모델 문자열만 바꿔 오픈웨이트 모델에 옮기고, 깨지는 곳을 과제x모델 표로 재며, 운영 규칙(금지 행동, 증거 필수)을 Otari 게이트웨이 정책(예산, 가드레일)으로 집행해 어느 규칙이 무엇을 막았는지 기록한다. 쓰는 사람: 상용 API 청구서를 오픈웨이트로 줄이려는 소규모 에이전트 팀. 본질: "모델이 똑똑한가"가 아니라 "모델 바깥 구조가 옮겨 가는가".

## 1. 성공 조건 (숫자) / 마감 / 비목표
루브릭 100점 = 오픈웨이트 30 + Otari 기능 60 + 프로젝트/데모 10 (출처 공고분석.md).
- 축 30 (오픈웨이트): 서로 다른 역할의 오픈웨이트 모델 >= 2종이 실제 응답 (S1)
- 축 60 (Otari 기능, 기능당 10, 상한 60): 앱 안에서 실제 호출된 기능 >= 6종, 각 호출의 흔적(요청 ID, 응답 헤더 또는 활동 기록) 1건 이상 (S2). 6종 = 라우팅/폴백, 웹 페치, 코드 실행, 예산 한도, 다중 모델 역할 분리, 가드레일.
- 축 10 (프로젝트/데모): 과제 N >= 10 x 모델 >= 3 결과표 1장이 재실행 한 명령으로 재생성 (S3), 영상 1개는 별도 단계
- 하한: 6종 중 5종 미만이면 LaneGovernor 후퇴안(부록 A) 발동
- 마감: 2026-11-11 낮(한국시간, 시간대 미표기라 보수적으로), 스모크 판정 2026-11-04
- 비목표: 모델 학습/파인튜닝, 로컬 오픈웨이트 추론, 사용자별 예산과 MCP(루브릭 8종 중 이번 6종 밖), 아동/개인 데이터, 공개 push는 승인 후, 호스티드 가입은 [ASK: 계정] 승인 전까지 안 함

## 2. 제약
- 호스티드 Otari.ai 사용이 필수 요건("You must use Otari.ai in your project"). 로컬 셀프호스트 스모크는 기능 동작의 대리 증거일 뿐 제출 증거가 아님.
- 비용 0원 원칙: 업스트림 호출은 가짜 서버로 시험, 실제 오픈웨이트 호출은 승인 뒤.

## 3. 유비쿼터스 언어
| 용어 | 뜻 | 코드 이름 |
|---|---|---|
| 과제 | 모델에 주는 결정적 검사가 가능한 한 건 | Task |
| 이식 | 모델 문자열만 바꿔 재실행 | Port / Repoint |
| 결과표 | 과제 x 모델 통과/실패 | ResultMatrix |
| 규칙 | 운영 규칙(금지 행동 등) | Rule |
| 집행 | 규칙을 게이트웨이 정책으로 막은 기록 | Enforcement |
| 기능 흔적 | Otari 기능 호출 증거 | FeatureTrace |

## 4. 도메인 모델
- Task, ModelRef(provider:model, role), Verdict(pass/fail/blocked), ResultMatrix, Rule, Enforcement, FeatureTrace, FeatureKind(6종)
- 포트: GatewayPort(complete), JudgePort, ClockPort

## 5. 유스케이스
| UC | 입력 | 출력 | 규칙 |
|---|---|---|---|
| UC-1 이식 실행 | Task[], ModelRef[] | ResultMatrix | 모델 문자열 외 입력 동일 |
| UC-2 흔적 집계 | 응답 헤더/활동 | FeatureTrace[] | 기능 6종 중 호출된 것만 인정 (enabled != used) |
| UC-3 규칙 집행 기록 | 403/402 응답 | Enforcement[] | 어느 Rule이 막았는지 필수 |

## 6. 수용 기준
- AC-1: Given 폴백 정책 a->b, a가 500 When 요청 Then 응답은 b가 냈고 Otari-Fallback=true인 FeatureTrace(라우팅/폴백) 1건
- AC-2: Given 6종 중 호출 흔적이 4종뿐 When 집계 Then 기능 점수 40, 6종이면 60 (루브릭 축 60, 기능당 10)
- AC-3: Given 예산 초과 키 When 요청 Then 차단 응답이 Enforcement(예산 한도)로 기록
- AC-4: Given 오픈웨이트 2종이 다른 역할 When 결과표 Then 역할별 모델이 표에 분리 표시 (축 30)
- AC-5: Given 인젝션 입력 + 가드레일 block When 요청 Then 403 + Enforcement(가드레일), 업스트림 호출 0

## 7. 아키텍처
domain/ <- application/ <- adapters/(otari_http) <- infrastructure/(config, composition root). 역방향 import 금지.

## 8. 비기능
호출당 비용 상한 로그, 모든 요청 ID 보존.

## 9. 물리 검증
스모크-2026-10-31.md (셀프호스트 실호출), 이후 호스티드 실호출은 계정 승인 뒤.

## 부록 A. LaneGovernor 후퇴안
스모크 6/6(게이트웨이 수준)이라 발동 조건은 아니지만 호스티드 실측에서 5종 미만이면 발동. 내용: 제품을 관제판으로 바꾼다. 에이전트마다 예산 한도 + 폴백 + 가드레일 3종을 핵심(30 + 30 + 오픈웨이트 30 = 90 상한 근접)으로 쓰고, 웹 페치/코드 실행 중 호스티드에서 막힌 것은 비목표로 내린다. 빠진 기능은 실측 시점에 이 절에 적는다(현재 빠진 기능 0).

## 10. 변경 이력
- v0.1 2026-10-31 최초
