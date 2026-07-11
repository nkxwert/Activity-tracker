# Activity Tracker

Windows용 활동 기록기. 활성 창(프로그램)을 자동으로 감지해 사용 시간을 기록합니다.
customtkinter 기반 모던 UI. 결과 화면에서 "클래식" / "카드형" 디자인을 즉석에서 전환해볼 수 있음.
창 크기 자유 조절 가능. 나눔스퀘어 폰트 자동 적용(없으면 맑은 고딕 대체).

## exe 받는 법 (파이썬 설치 불필요)
1. 이 저장소를 GitHub에 올리고 `main` 브랜치에 push
2. GitHub 저장소 상단 **Actions** 탭 클릭
3. 방금 실행된 워크플로우(빌드) 클릭 → 초록 체크 표시(완료)까지 대기 (약 1~2분)
4. 페이지 하단 **Artifacts** 항목에서 `ActivityTracker-Windows` 다운로드 (zip)
5. 압축 풀면 `ActivityTracker.exe` — 더블클릭으로 바로 실행

## 폰트 (선택사항)
`fonts` 폴더 안의 README 참고 — 나눔스퀘어 ttf 파일을 넣으면 자동 적용됩니다. 안 넣어도 맑은 고딕으로 정상 작동합니다.

## 참고
- 처음 실행 시 Windows Defender SmartScreen이 "알 수 없는 게시자" 경고를 띄울 수 있습니다.
  → "추가 정보" 클릭 → "실행" 클릭하면 정상 실행됩니다.
