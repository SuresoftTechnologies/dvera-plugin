# DVERA — CT C/C++ 검증을 위한 코딩 에이전트 Skill

> 이 문서는 [README.md](README.md)의 한국어 번역입니다. 두 문서의 내용이 다를 경우 영문판이 기준입니다.

DVERA(Dynamic Verification Agent)는 Claude Code, Codex CLI, Cursor, GitHub Copilot 등의 코딩 에이전트 안에서 CT C/C++ 검증 작업을 연결합니다. 소스 코드·요구사항·빌드 정보·변경 이력·기존 테스트 자산의 작업 맥락을 바탕으로 CT 검증 작업을 준비하고 요청합니다.

CT(Controller Tester)는 미션 크리티컬 C/C++ 소프트웨어를 위한 단위·통합·코드 기반 테스트 자동화 솔루션입니다. 테스트 환경 구성, 테스트 설계·생성, 실행, 코드 커버리지 분석, 보고, 추적성 관리를 하나의 작업 흐름으로 연결합니다.

기능안전 프로젝트의 단위·통합 검증, 코드 커버리지, 요구사항 추적성과 ISO 26262 적용 예시는 [CT 공식 제품 페이지](https://apps.suresofttech.com/ct/)에서 확인할 수 있습니다.

DVERA가 CT의 검증 결과를 대체하지는 않습니다. 코딩 에이전트는 검증 작업을 준비·조율하고, CT는 실제 분석·빌드·테스트 실행·결과 집계를 수행합니다. 생성한 테스트는 테스트 의도·데이터·기대 결과를 검토한 뒤 실제 실행 결과와 측정된 커버리지로 확인해야 합니다.

## CT와 DVERA 작업 흐름이 더하는 것

| 검증 과제 | CT와 DVERA 작업 흐름 |
|---|---|
| 복잡한 C/C++ 환경 | 분석 전에 컴파일러·매크로·include 경로·툴체인·빌드·타깃 조건을 수집 |
| 단위·통합 검증 | 함수·모듈·인터페이스 수준의 테스트를 설계·실행하고, 해당하는 경우 기존 GoogleTest 자산도 활용 |
| 검토 가능한 근거 | 테스트 의도, 실행 결과, 구문·분기·MC/DC 커버리지, 보고서, 요구사항 연결을 함께 검토 |
| 변경 후 반복 검증 | 코드 변경 뒤 영향 테스트를 다시 실행하고 새 실패·커버리지 변화를 회귀 관점에서 검토 |
| AI 기반 테스트 작업 | 코드·요구사항·변경 맥락으로 테스트 작업을 준비하고 CT 분석·측정 결과로 보완 |

## 작업 흐름 한눈에 보기

1. CT 프로젝트에 필요한 컴파일러·매크로·include 경로·툴체인·타깃 맥락을 준비합니다.
2. 프로젝트를 분석하고, 환경·구성 문제를 피드백 루프로 해결합니다.
3. 빌드·실행·커버리지 피드백을 사용해 단위·통합 테스트를 생성·실행·보완합니다.
4. 커버리지와 결과를 검토·보고하고, 소스 변경 뒤 영향 범위를 다시 검증합니다.

이 저장소의 Skill은 위 제품 연동 작업 흐름을 문서화합니다. CT 설치본을 대체하는 독립 도구는 아닙니다.

## Claude 디렉터리 배포본

이 Claude 디렉터리 배포본에는 DVERA Skills가 포함됩니다. CT 실행 환경과 선택 사항인 로컬 MCP
서버는 포함하지 않습니다. 제품 기반 동작에는 별도로 설치된 CT 환경과 유효한 CT 라이선스가 필요합니다.

[전체 소스 저장소](https://github.com/SuresoftTechnologies/dvera-plugin/tree/main)에서 선택 사항인
로컬 MCP 서버와 MCP 번들 배포본도 제공합니다.

## 설치

Skills 전용 패키지는 Claude 플러그인 디렉터리에서 DVERA를 설치해 사용합니다.
아래 수동 설치 명령은 선택 사항인 로컬 MCP 서버 소스도 포함한 `main`의 전체 저장소를 설치합니다.

전체 소스 저장소에서 수동으로 설치하려면 Claude Code에서 실행합니다:

```text
/plugin marketplace add SuresoftTechnologies/dvera-plugin
/plugin install dvera@suresofttech
```

터미널에서:

```text
claude plugin marketplace add SuresoftTechnologies/dvera-plugin
claude plugin install dvera@suresofttech
```

설치 후 Skill은 `/dvera:ct-init-project`, `/dvera:ct-test-loop` 형태로 호출됩니다. 플러그인은 세션마다 약 620토큰을 사용하며, 각 Skill 본문은 해당 Skill이 실행될 때만 읽힙니다.

제품 연동 동작에는 배포된 CT 환경이 필요합니다. 환경이 없으면 Skill은 설치 확인 단계에서 중단하고 제품 문의 경로를 안내합니다.

## 요청 예시

CT 사용자 가이드의 트리거 예시입니다. 동일한 요청이라도 사용하는 AI 모델과 대화 컨텍스트에 따라 응답이 달라질 수 있습니다. 결과가 예상과 다르면 요청을 더 구체적으로 다시 입력하고 재시도하세요.

| 요청 | Skill |
|---|---|
| `CT 프로젝트를 만들어서 검증을 시작해 주세요.` | `ct-init-project` |
| `CT에서 테스트를 진행해 주세요.` | `ct-init-project` |
| `calculate_checksum 함수에 테스트를 생성해 주세요.` | `ct-test-loop` |
| `테스트가 없는 함수를 찾아서 테스트를 생성해 주세요.` | `ct-test-loop` |
| `회귀 테스트를 진행해 주세요.` | `ct-regression` |
| `CT를 열어주세요.` | `ct-open` |

## 공개 Skill

모든 Skill은 제품 연동 작업을 수행하려면 배포된 CT 환경이 필요하며, 설치본을 찾지 못하면 설치 안내를 표시하고 중단합니다.

| Skill | CT 작업 단계 |
|---|---|
| `ct-init-project` | CT 검증 프로젝트 시작 또는 준비 |
| `ct-extract-macro` | 타깃 컴파일러 매크로와 빌드 환경 정보 수집 |
| `ct-make-conf` | 선택한 툴체인용 분석 구성 준비 |
| `ct-setup-project` | CT 프로젝트 생성과 빌드 입력 적용 |
| `ct-analysis-loop` | 분석과 구성·툴체인 문제 해결 |
| `ct-test-loop` | 테스트 생성·실행·보완 |
| `ct-kb-update` | 완료된 CT 작업의 검증 관찰 기록 수집 |
| `ct-regression` | 코드 변경 후 회귀 검증 |
| `ct-self-healing` | 회귀 실행 근거를 수집하고 CT Self-Healing 검토 대상을 식별 |
| `ct-run-gtest` | CT에 등록된 GoogleTest를 재실행하고 결과·커버리지 검토 |
| `ct-req-to-test` | 승인된 요구사항으로 CT AI 테스트를 생성·실행 |
| `ct-report` | 실행·커버리지 근거 내보내기 |
| `ct-open` | CT 프로젝트 화면 검토 |
| `ct-orchestrator` | 진행 중인 검증 작업의 다음 단계 선택 |

## 제품 연동 작업 흐름

DVERA는 CT와 DVERA가 구축된 환경에서 사용합니다. 이 Claude 디렉터리 배포본은 검증 작업 흐름을 문서화하고 Skills를 포함합니다. CT와 실행 환경은 별도로 설치해야 합니다.

구축 전에는 이 저장소의 작업 흐름을 검토할 수 있지만, CT 동작이 필요한 Skill은 설치 확인에서 중단합니다. CT 분석·실행·커버리지 측정·보고가 수행됐다고 주장하지 않습니다.

## 선택 사항인 로컬 MCP 연결

로컬 MCP 서버는 이 Claude 디렉터리 패키지와 별도로 배포합니다.
[전체 저장소의 MCP 설정 안내(영문)](https://github.com/SuresoftTechnologies/dvera-plugin/blob/main/README.md#mcp-tools)에
따라 연결할 수 있습니다. MCP 서버에도 로컬 CT 설치와 유효한 CT 라이선스가 필요합니다.

## 제품 기반 검증 요구사항

- CT 2026.06 이상
- 유효한 CT 라이선스
- 지원되는 C/C++ 빌드·타깃 환경
- 설치된 CT 환경에서 제공되는 DVERA 연동

제품 데모, 구매 또는 구축 상담은 [bizcenter@suresofttech.com](mailto:bizcenter@suresofttech.com)으로 문의해 주세요.

## 개인정보 처리방침

[전체 소스 저장소](https://github.com/SuresoftTechnologies/dvera-plugin/tree/main)의 선택 사항인 MCP 서버는 전적으로 사용자 PC에서 동작합니다. 이 Claude 디렉터리 패키지에는 포함하지 않습니다.

- Suresoft Technologies를 포함해 어디에도 데이터를 전송하지 않습니다. 자체 텔레메트리·분석·네트워크
  호출이 없습니다.
- 도구 인자는 같은 PC에 설치된 CT로 전달되고, CT의 응답이 MCP 클라이언트로 돌아갑니다. CT 자체
  워크스페이스 밖에는 아무것도 기록하지 않습니다.
- 자격증명을 저장하지 않으며, CT 설치 디렉터리와 도구 호출이 지정한 경로 외의 파일을 읽지 않습니다.
- CT가 자체적으로 남기는 것(워크스페이스, 분석 산출물, 보고서)은 이 저장소가 아니라 CT 제품의 데이터
  처리 방침을 따릅니다.

Skills는 별도 프로그램을 포함하지 않는 Markdown 지침입니다. 에이전트가 별도로 설치된 CT를
호출하도록 안내합니다. 에이전트가 CT 출력을 읽으면 소스 경로, 함수명, 소스 코드 일부, 테스트
결과와 커버리지 데이터를 사용 중인 AI 제공자에게 전달할 수 있습니다. 이 전송에는 해당 AI
제공자의 약관과 개인정보 처리방침이 적용됩니다. Skills 패키지는 이 데이터를 Suresoft Technologies로
전송하지 않습니다.

전문은 [PRIVACY.md](PRIVACY.md)에 있습니다. CT 제품 자체의 데이터 처리에 대한 문의는
[bizcenter@suresofttech.com](mailto:bizcenter@suresofttech.com)으로 주세요.

## 라이선스 및 상표

이 저장소는 [MIT 라이선스](LICENSE)를 따릅니다. 라이선스는 이 배포본의 문서와 Skill 파일에 적용됩니다. CT 자체에는 적용되지 않습니다. CT와 DVERA는 Suresoft Technologies의 제품이며, 이 저장소의 라이선스로 제품 기능이나 제품 라이선스가 제공되지는 않습니다.

GoogleTest는 Google LLC의 상표입니다. 이 저장소는 Google과 제휴 관계에 있지 않으며 Google의 후원이나 승인을 받지 않았습니다. 그 밖의 제품명은 각 소유자의 상표일 수 있습니다.
