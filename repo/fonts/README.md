# 나눔스퀘어 폰트 넣는 곳

이 폴더에 나눔스퀘어(NanumSquare) ttf 파일을 넣으면 프로그램이 자동으로 인식해서 사용합니다.
파일이 없으면 자동으로 "맑은 고딕"으로 대체되니, 안 넣어도 프로그램은 정상 작동합니다.

## 다운로드
- 눈누(무료 상업용 폰트 사이트): https://noonnu.cc/en/font_page/37
- 위 페이지에서 "다운로드" 버튼으로 zip을 받은 뒤, 압축을 풀면 아래와 같은 파일들이 나옵니다.
  - NanumSquareR.ttf (Regular)
  - NanumSquareB.ttf (Bold)
  - NanumSquareL.ttf (Light) — 있는 경우
  - NanumSquareEB.ttf (ExtraBold) — 있는 경우

## 넣는 법
1. 위에서 받은 .ttf 파일들을 이 `fonts` 폴더 안에 그대로 복사
2. GitHub 저장소의 `fonts` 폴더에 업로드 & Commit
3. Actions가 자동으로 다시 빌드됨 (fonts 폴더가 exe 안에 함께 포함됩니다)

컴퓨터에 폰트를 "설치"할 필요는 없습니다 — 프로그램이 실행될 때 이 폴더의 폰트를 자체적으로 불러와 사용합니다.
