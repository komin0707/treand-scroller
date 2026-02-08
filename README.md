# Trend Dashboard (GitHub Pages)

이 프로젝트는 아래 구조로 배포됩니다.

- `docs/index.html`: 정적 대시보드 UI
- `docs/data.json`: 최신 수집 결과
- `naver_realtime_scraper.py`: Selenium 수집기
- `.github/workflows/update-data.yml`: 30분마다 `data.json` 자동 갱신

## 1) GitHub에 업로드

이 폴더를 새 저장소에 push 하세요.

## 2) GitHub Pages 켜기

1. 저장소 `Settings` -> `Pages`
2. `Source`를 `Deploy from a branch`로 선택
3. Branch: `main`, Folder: `/docs`
4. 저장

배포 URL은 보통 아래 형태입니다.

- `https://<your-id>.github.io/<repo-name>/`

## 3) 자동 갱신 실행

- `Actions` 탭에서 `Update Trend Data` 워크플로를 `Run workflow`로 1회 수동 실행
- 이후 30분마다 자동 실행됩니다.

## 로컬 테스트

```bash
python3 -m pip install -r requirements.txt
python3 naver_realtime_scraper.py --out docs/data.json --json
```

`docs/index.html`을 브라우저로 열어 확인합니다.

## 참고

- Selenium 실행에는 Chrome/Chromium 환경이 필요합니다.
- 대상 사이트 구조 변경 시 수집 로직 업데이트가 필요할 수 있습니다.
